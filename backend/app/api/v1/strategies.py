from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
import importlib

from app.core.database import get_db
from app.core.execution import get_execution_engine, is_engine_initialized
from app.api.deps import get_current_user
from app.models import User, Strategy, StrategySubscription, BrokerConnection
from brokers.factory import BrokerFactory
from app.core.config import settings
from app.schemas import (
    StrategyListResponse,
    StrategyResponse,
    StrategyDetailResponse,
    ConfigurableParam,
    StrategySubscriptionCreate,
    StrategySubscriptionUpdate,
    StrategySubscriptionResponse,
    StrategyAction,
)

router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.get("", response_model=List[StrategyListResponse])
async def list_strategies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_featured: Optional[bool] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all available strategies.
    """
    query = select(Strategy).where(Strategy.is_active == True)

    if is_featured is not None:
        query = query.where(Strategy.is_featured == is_featured)

    if tag:
        query = query.where(Strategy.tags.contains([tag]))

    if search:
        query = query.where(
            Strategy.name.ilike(f"%{search}%") |
            Strategy.description.ilike(f"%{search}%")
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    return result.scalars().all()


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific strategy by ID.
    """
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.is_active == True)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    return strategy


@router.get("/slug/{slug}", response_model=StrategyResponse)
async def get_strategy_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific strategy by slug.
    """
    result = await db.execute(
        select(Strategy).where(Strategy.slug == slug, Strategy.is_active == True)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    return strategy


@router.get("/{strategy_id}/config", response_model=StrategyDetailResponse)
async def get_strategy_with_config(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get strategy details including configurable parameters.
    """
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.is_active == True)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Load strategy class to get configurable params
    try:
        module = importlib.import_module(strategy.module_path)
        strategy_class = getattr(module, strategy.class_name)
        raw_params = strategy_class.get_configurable_params()

        configurable_params = [
            ConfigurableParam(
                name=p.name,
                display_name=p.display_name,
                type=p.param_type,
                default_value=p.default_value,
                min_value=p.min_value,
                max_value=p.max_value,
                description=p.description,
            )
            for p in raw_params
        ]
    except (ImportError, AttributeError) as e:
        # If strategy class can't be loaded, return empty params
        configurable_params = []

    return StrategyDetailResponse(
        id=strategy.id,
        name=strategy.name,
        slug=strategy.slug,
        description=strategy.description,
        long_description=strategy.long_description,
        version=strategy.version,
        author=strategy.author,
        min_capital=strategy.min_capital,
        expected_return_percent=strategy.expected_return_percent,
        max_drawdown_percent=strategy.max_drawdown_percent,
        timeframe=strategy.timeframe,
        supported_symbols=strategy.supported_symbols,
        tags=strategy.tags,
        is_active=strategy.is_active,
        is_featured=strategy.is_featured,
        module_path=strategy.module_path,
        class_name=strategy.class_name,
        created_at=strategy.created_at,
        updated_at=strategy.updated_at,
        configurable_params=configurable_params,
    )


# --- Strategy Subscriptions ---

@router.get("/subscriptions/my", response_model=List[StrategySubscriptionResponse])
async def get_my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all strategy subscriptions for current user.
    """
    result = await db.execute(
        select(StrategySubscription).where(StrategySubscription.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/subscribe", response_model=StrategySubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def subscribe_to_strategy(
    subscription_data: StrategySubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Subscribe to a strategy.
    """
    # Check if strategy exists
    result = await db.execute(
        select(Strategy).where(Strategy.id == subscription_data.strategy_id, Strategy.is_active == True)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Check minimum capital
    if subscription_data.capital_allocated < strategy.min_capital:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum capital required is {strategy.min_capital}",
        )

    # Check if already subscribed with the same symbols
    # Note: Users can subscribe to the same strategy multiple times with different symbols
    result = await db.execute(
        select(StrategySubscription).where(
            StrategySubscription.user_id == current_user.id,
            StrategySubscription.strategy_id == subscription_data.strategy_id,
        )
    )
    existing_subscriptions = result.scalars().all()

    # Check if any existing subscription has the exact same set of symbols
    selected_symbols_set = set(subscription_data.selected_symbols)
    for existing in existing_subscriptions:
        if existing.selected_symbols and set(existing.selected_symbols) == selected_symbols_set:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Already subscribed to this strategy with the same symbols: {', '.join(sorted(selected_symbols_set))}",
            )

    # Verify broker connection if provided
    if subscription_data.broker_connection_id:
        result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.id == subscription_data.broker_connection_id,
                BrokerConnection.user_id == current_user.id,
            )
        )
        broker_connection = result.scalar_one_or_none()

        if not broker_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Broker connection not found",
            )

    # Check subscription limit (free tier = 1 strategy)
    result = await db.execute(
        select(func.count(StrategySubscription.id)).where(
            StrategySubscription.user_id == current_user.id
        )
    )
    subscription_count = result.scalar()

    # TODO: Check user's subscription plan for limits
    # For now, allow up to 1 strategy for free tier
    if subscription_count >= 1:
        # Check if user has a paid plan
        # For now, just raise an error
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Free tier allows only 1 strategy. Please upgrade to subscribe to more.",
        )

    # Validate config_params against strategy's configurable params
    validated_config_params = {}
    if subscription_data.config_params:
        try:
            module = importlib.import_module(strategy.module_path)
            strategy_class = getattr(module, strategy.class_name)
            valid_params = {p.name: p for p in strategy_class.get_configurable_params()}

            for key, value in subscription_data.config_params.items():
                if key not in valid_params:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid config parameter: {key}",
                    )
                param = valid_params[key]
                # Validate value within range
                if param.min_value is not None and value < param.min_value:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Parameter {key} must be >= {param.min_value}",
                    )
                if param.max_value is not None and value > param.max_value:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Parameter {key} must be <= {param.max_value}",
                    )
                validated_config_params[key] = value
        except (ImportError, AttributeError):
            # If strategy class can't be loaded, accept params as-is
            validated_config_params = subscription_data.config_params

    subscription = StrategySubscription(
        user_id=current_user.id,
        strategy_id=subscription_data.strategy_id,
        broker_connection_id=subscription_data.broker_connection_id,
        capital_allocated=subscription_data.capital_allocated,
        is_paper_trading=subscription_data.is_paper_trading,
        max_drawdown_percent=subscription_data.max_drawdown_percent,
        daily_loss_limit=subscription_data.daily_loss_limit,
        per_trade_stop_loss_percent=subscription_data.per_trade_stop_loss_percent,
        max_positions=subscription_data.max_positions,
        config_params=validated_config_params,
        selected_symbols=subscription_data.selected_symbols,
        scheduled_start=subscription_data.scheduled_start,
        scheduled_stop=subscription_data.scheduled_stop,
        active_days=subscription_data.active_days,
    )

    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    return subscription


@router.get("/subscriptions/{subscription_id}", response_model=StrategySubscriptionResponse)
async def get_subscription(
    subscription_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific subscription.
    """
    result = await db.execute(
        select(StrategySubscription).where(
            StrategySubscription.id == subscription_id,
            StrategySubscription.user_id == current_user.id,
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    return subscription


@router.patch("/subscriptions/{subscription_id}", response_model=StrategySubscriptionResponse)
async def update_subscription(
    subscription_id: UUID,
    update_data: StrategySubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a subscription's settings.
    """
    result = await db.execute(
        select(StrategySubscription).where(
            StrategySubscription.id == subscription_id,
            StrategySubscription.user_id == current_user.id,
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    # Don't allow updates while strategy is running
    if subscription.status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update subscription while strategy is running. Please stop it first.",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(subscription, field, value)

    await db.commit()
    await db.refresh(subscription)

    return subscription


@router.post("/subscriptions/{subscription_id}/action", response_model=StrategySubscriptionResponse)
async def subscription_action(
    subscription_id: UUID,
    action: StrategyAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Perform an action on a subscription (start, stop, pause, resume).
    """
    result = await db.execute(
        select(StrategySubscription).where(
            StrategySubscription.id == subscription_id,
            StrategySubscription.user_id == current_user.id,
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    # Get the associated strategy
    result = await db.execute(
        select(Strategy).where(Strategy.id == subscription.strategy_id)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    current_status = subscription.status
    new_status = None

    # Check if execution engine is available
    engine_available = is_engine_initialized()

    if action.action == "start":
        if current_status not in ["inactive", "stopped"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start strategy from status: {current_status}",
            )

        if engine_available:
            try:
                engine = get_execution_engine()

                # Connect broker to execution engine for market data
                broker_result = await db.execute(
                    select(BrokerConnection).where(
                        BrokerConnection.user_id == current_user.id,
                        BrokerConnection.is_active == True,
                    )
                )
                broker_connection = broker_result.scalar_one_or_none()

                if broker_connection and not engine.broker:
                    try:
                        # Get broker config
                        broker_config = {
                            "fyers": {
                                "app_id": settings.FYERS_APP_ID,
                                "secret_key": settings.FYERS_SECRET_KEY,
                            },
                        }.get(broker_connection.broker, {})

                        # Create and connect broker
                        broker = await BrokerFactory.create_and_connect(
                            broker_connection.broker,
                            {
                                "api_key": broker_connection.api_key,
                                "api_secret": broker_connection.api_secret,
                                "access_token": broker_connection.access_token,
                                "client_id": broker_config.get("app_id") or broker_connection.api_key,
                            },
                        )
                        engine.broker = broker
                    except Exception as e:
                        print(f"Failed to connect broker for market data: {e}")
                        # Continue without market data - strategy can still run

                # Build config for execution engine
                config = {
                    "context": {
                        "strategy_id": str(subscription.strategy_id),
                        "user_id": str(current_user.id),
                        "subscription_id": str(subscription_id),
                        "capital": float(subscription.capital_allocated),
                        "max_positions": subscription.max_positions,
                        "max_drawdown_percent": float(subscription.max_drawdown_percent),
                        "daily_loss_limit": float(subscription.daily_loss_limit or 0),
                        "per_trade_sl_percent": float(subscription.per_trade_stop_loss_percent),
                        "is_paper_trading": subscription.is_paper_trading,
                        "dry_run": subscription.dry_run,
                    },
                    "risk_limits": {
                        "max_drawdown_percent": float(subscription.max_drawdown_percent),
                        "daily_loss_limit": float(subscription.daily_loss_limit or 0),
                        "per_trade_sl_percent": float(subscription.per_trade_stop_loss_percent),
                        "max_positions": subscription.max_positions,
                    },
                    "config_params": subscription.config_params or {},
                    "symbols": subscription.selected_symbols or [],
                    "dry_run": subscription.dry_run,
                }

                success = await engine.start_strategy(
                    subscription_id=str(subscription_id),
                    user_id=str(current_user.id),
                    strategy_module=strategy.module_path,
                    strategy_class=strategy.class_name,
                    config=config,
                )

                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to start strategy execution",
                    )
            except RuntimeError as e:
                # Execution engine not initialized - continue with status update only
                pass

        new_status = "active"
        from datetime import datetime
        subscription.last_started_at = datetime.utcnow()

    elif action.action == "stop":
        if current_status not in ["active", "paused"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot stop strategy from status: {current_status}",
            )

        if engine_available:
            try:
                engine = get_execution_engine()
                await engine.stop_strategy(str(subscription_id))
            except RuntimeError:
                pass

        new_status = "stopped"
        from datetime import datetime
        subscription.last_stopped_at = datetime.utcnow()

    elif action.action == "pause":
        if current_status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause strategy from status: {current_status}",
            )

        if engine_available:
            try:
                engine = get_execution_engine()
                await engine.pause_strategy(str(subscription_id))
            except RuntimeError:
                pass

        new_status = "paused"

    elif action.action == "resume":
        if current_status != "paused":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume strategy from status: {current_status}",
            )

        if engine_available:
            try:
                engine = get_execution_engine()
                await engine.resume_strategy(str(subscription_id))
            except RuntimeError:
                pass

        new_status = "active"

    subscription.status = new_status
    await db.commit()
    await db.refresh(subscription)

    return subscription


@router.delete("/subscriptions/{subscription_id}")
async def unsubscribe_from_strategy(
    subscription_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Unsubscribe from a strategy.
    """
    result = await db.execute(
        select(StrategySubscription).where(
            StrategySubscription.id == subscription_id,
            StrategySubscription.user_id == current_user.id,
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    if subscription.status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unsubscribe while strategy is running. Please stop it first.",
        )

    await db.delete(subscription)
    await db.commit()

    return {"message": "Unsubscribed successfully"}
