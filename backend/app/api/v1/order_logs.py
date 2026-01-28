"""
Order logs API endpoints for testing and monitoring order execution.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, OrderLog, StrategySubscription, BrokerConnection
from app.schemas import (
    OrderLogResponse,
    OrderLogListResponse,
    BrokerTestOrderRequest,
    BrokerTestOrderResponse,
)
from brokers.factory import BrokerFactory
from app.core.config import settings


router = APIRouter(prefix="/order-logs", tags=["Order Logs"])


@router.get("", response_model=OrderLogListResponse)
async def get_order_logs(
    subscription_id: Optional[UUID] = Query(None, description="Filter by subscription ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    is_dry_run: Optional[bool] = Query(None, description="Filter by dry-run status"),
    is_test_order: Optional[bool] = Query(None, description="Filter by test order status"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    from_date: Optional[datetime] = Query(None, description="Filter from date"),
    to_date: Optional[datetime] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get order logs with filtering and pagination.

    This endpoint helps you verify if orders are being sent to the broker
    and track all order execution events.
    """
    # Build query
    query = select(OrderLog).join(
        StrategySubscription,
        OrderLog.subscription_id == StrategySubscription.id
    ).where(
        StrategySubscription.user_id == current_user.id
    )

    # Apply filters
    if subscription_id:
        query = query.where(OrderLog.subscription_id == subscription_id)

    if event_type:
        query = query.where(OrderLog.event_type == event_type)

    if is_dry_run is not None:
        query = query.where(OrderLog.is_dry_run == is_dry_run)

    if is_test_order is not None:
        query = query.where(OrderLog.is_test_order == is_test_order)

    if success is not None:
        query = query.where(OrderLog.success == success)

    if from_date:
        query = query.where(OrderLog.created_at >= from_date)

    if to_date:
        query = query.where(OrderLog.created_at <= to_date)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(OrderLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()

    return OrderLogListResponse(
        logs=logs,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{log_id}", response_model=OrderLogResponse)
async def get_order_log(
    log_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific order log by ID."""
    result = await db.execute(
        select(OrderLog).join(
            StrategySubscription,
            OrderLog.subscription_id == StrategySubscription.id
        ).where(
            OrderLog.id == log_id,
            StrategySubscription.user_id == current_user.id,
        )
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order log not found",
        )

    return log


@router.post("/test-broker-order", response_model=BrokerTestOrderResponse)
async def test_broker_order(
    request: BrokerTestOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Place a test order with the broker to verify connectivity.

    This is a real order with minimal quantity (1-10 shares) to test
    if your broker integration is working correctly.

    **WARNING**: This will place a real order if broker is connected!
    Only use this for testing purposes.
    """
    # Get broker connection
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.id == request.broker_connection_id,
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.is_active == True,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broker connection not found or inactive",
        )

    # Check token expiry
    if connection.token_expiry and connection.token_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Broker session expired. Please reconnect your broker.",
        )

    try:
        # Get broker config
        config = _get_broker_config(connection.broker)

        # Log the attempt
        print(f"[TEST ORDER] Broker: {connection.broker}, User: {current_user.email}")
        print(f"[TEST ORDER] Token expiry: {connection.token_expiry}")
        print(f"[TEST ORDER] Token valid: {connection.token_expiry > datetime.utcnow() if connection.token_expiry else 'Unknown'}")

        # Create broker instance
        broker = await BrokerFactory.create_and_connect(
            connection.broker,
            {
                "api_key": connection.api_key,
                "api_secret": connection.api_secret,
                "access_token": connection.access_token,
                "client_id": config.get("app_id") or connection.api_key,
            },
        )

        # If LIMIT order, get current price if not provided
        price = request.price
        if request.order_type == "LIMIT" and not price:
            quote = await broker.get_quote(request.symbol, request.exchange)
            price = float(quote.ltp) if quote.ltp else None

        # Prepare order request
        order_request = {
            "symbol": request.symbol.upper(),
            "exchange": request.exchange.upper(),
            "transaction_type": request.transaction_type,
            "quantity": request.quantity,
            "order_type": request.order_type,
            "price": price,
        }

        print(f"[TEST ORDER] Placing order: {order_request}")

        # Place test order
        result = await broker.place_order(**order_request)

        print(f"[TEST ORDER] Order placed successfully: {result}")

        await broker.disconnect()

        # Log the test order
        from app.models.order import OrderLog
        from decimal import Decimal

        log_entry = OrderLog(
            subscription_id=None,  # No subscription for test orders
            order_id=None,
            symbol=request.symbol.upper(),
            exchange=request.exchange.upper(),
            order_type=request.order_type,
            transaction_type=request.transaction_type,
            quantity=request.quantity,
            price=Decimal(str(price)) if price else None,
            trigger_price=None,
            event_type="placed",
            is_dry_run=False,
            is_test_order=True,
            success=True,
            broker_order_id=result.broker_order_id if hasattr(result, 'broker_order_id') else None,
            broker_name=connection.broker,
            broker_request=order_request,
            broker_response=vars(result) if hasattr(result, '__dict__') else {"result": str(result)},
            error_message=None,
            strategy_name="Test Order",
            reason="Manual broker connectivity test",
        )

        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)

        return BrokerTestOrderResponse(
            success=True,
            message=f"Test order placed successfully! Order ID: {result.broker_order_id if hasattr(result, 'broker_order_id') else 'N/A'}",
            order_log_id=log_entry.id,
            broker_order_id=result.broker_order_id if hasattr(result, 'broker_order_id') else None,
            broker_response=vars(result) if hasattr(result, '__dict__') else {"result": str(result)},
        )

    except Exception as e:
        # Log the failed test
        from app.models.order import OrderLog
        from decimal import Decimal

        log_entry = OrderLog(
            subscription_id=None,
            order_id=None,
            symbol=request.symbol.upper(),
            exchange=request.exchange.upper(),
            order_type=request.order_type,
            transaction_type=request.transaction_type,
            quantity=request.quantity,
            price=Decimal(str(request.price)) if request.price else None,
            trigger_price=None,
            event_type="failed",
            is_dry_run=False,
            is_test_order=True,
            success=False,
            broker_order_id=None,
            broker_name=connection.broker,
            broker_request=None,
            broker_response=None,
            error_message=str(e),
            strategy_name="Test Order",
            reason="Manual broker connectivity test",
        )

        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)

        return BrokerTestOrderResponse(
            success=False,
            message="Test order failed",
            order_log_id=log_entry.id,
            error=str(e),
        )


def _get_broker_config(broker_name: str) -> dict:
    """Get broker configuration from settings based on broker name."""
    config_mapping = {
        "fyers": {
            "app_id": settings.FYERS_APP_ID,
            "secret_key": settings.FYERS_SECRET_KEY,
            "redirect_uri": settings.FYERS_REDIRECT_URI,
        },
    }
    return config_mapping.get(broker_name, {})
