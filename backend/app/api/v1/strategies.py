from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Strategy, StrategySubscription, BrokerConnection
from app.schemas import (
    StrategyListResponse,
    StrategyResponse,
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

    # Check if already subscribed
    result = await db.execute(
        select(StrategySubscription).where(
            StrategySubscription.user_id == current_user.id,
            StrategySubscription.strategy_id == subscription_data.strategy_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already subscribed to this strategy",
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

    current_status = subscription.status
    new_status = None

    if action.action == "start":
        if current_status not in ["inactive", "stopped"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start strategy from status: {current_status}",
            )
        new_status = "active"
        # TODO: Actually start the strategy execution

    elif action.action == "stop":
        if current_status not in ["active", "paused"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot stop strategy from status: {current_status}",
            )
        new_status = "stopped"
        # TODO: Actually stop the strategy execution

    elif action.action == "pause":
        if current_status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause strategy from status: {current_status}",
            )
        new_status = "paused"
        # TODO: Actually pause the strategy execution

    elif action.action == "resume":
        if current_status != "paused":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume strategy from status: {current_status}",
            )
        new_status = "active"
        # TODO: Actually resume the strategy execution

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
