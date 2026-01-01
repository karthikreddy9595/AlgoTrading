from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, StrategySubscription, Position, Order, Trade
from app.schemas import (
    PositionResponse,
    OrderResponse,
    OrderListResponse,
    TradeResponse,
    TradeListResponse,
    PortfolioSummary,
)

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio summary for current user.
    """
    # Get all subscriptions
    result = await db.execute(
        select(StrategySubscription).where(StrategySubscription.user_id == current_user.id)
    )
    subscriptions = result.scalars().all()

    total_capital = sum(s.capital_allocated for s in subscriptions)
    total_pnl = sum(s.current_pnl for s in subscriptions)
    today_pnl = sum(s.today_pnl for s in subscriptions)
    active_strategies = len([s for s in subscriptions if s.status == "active"])

    # Get open positions count
    subscription_ids = [s.id for s in subscriptions]
    if subscription_ids:
        result = await db.execute(
            select(func.count(Position.id)).where(Position.subscription_id.in_(subscription_ids))
        )
        open_positions = result.scalar() or 0

        # Get total trades count
        result = await db.execute(
            select(func.count(Trade.id)).where(Trade.subscription_id.in_(subscription_ids))
        )
        total_trades = result.scalar() or 0
    else:
        open_positions = 0
        total_trades = 0

    return PortfolioSummary(
        total_capital=total_capital,
        allocated_capital=total_capital,
        available_capital=Decimal("0"),  # TODO: Calculate based on positions
        total_pnl=total_pnl,
        today_pnl=today_pnl,
        active_strategies=active_strategies,
        open_positions=open_positions,
        total_trades=total_trades,
    )


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    subscription_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all open positions.
    """
    # Get user's subscription IDs
    result = await db.execute(
        select(StrategySubscription.id).where(StrategySubscription.user_id == current_user.id)
    )
    subscription_ids = [row[0] for row in result.fetchall()]

    if not subscription_ids:
        return []

    query = select(Position).where(Position.subscription_id.in_(subscription_ids))

    if subscription_id:
        if subscription_id not in subscription_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this subscription",
            )
        query = query.where(Position.subscription_id == subscription_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/orders", response_model=OrderListResponse)
async def get_orders(
    subscription_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get order history.
    """
    # Get user's subscription IDs
    result = await db.execute(
        select(StrategySubscription.id).where(StrategySubscription.user_id == current_user.id)
    )
    subscription_ids = [row[0] for row in result.fetchall()]

    if not subscription_ids:
        return OrderListResponse(orders=[], total=0, page=page, page_size=page_size)

    query = select(Order).where(Order.subscription_id.in_(subscription_ids))

    if subscription_id:
        if subscription_id not in subscription_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this subscription",
            )
        query = query.where(Order.subscription_id == subscription_id)

    if status_filter:
        query = query.where(Order.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Paginate
    query = query.order_by(Order.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        orders=orders,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/trades", response_model=TradeListResponse)
async def get_trades(
    subscription_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get trade history.
    """
    # Get user's subscription IDs
    result = await db.execute(
        select(StrategySubscription.id).where(StrategySubscription.user_id == current_user.id)
    )
    subscription_ids = [row[0] for row in result.fetchall()]

    if not subscription_ids:
        return TradeListResponse(trades=[], total=0, page=page, page_size=page_size)

    query = select(Trade).where(Trade.subscription_id.in_(subscription_ids))

    if subscription_id:
        if subscription_id not in subscription_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this subscription",
            )
        query = query.where(Trade.subscription_id == subscription_id)

    if status_filter:
        query = query.where(Trade.status == status_filter)

    if start_date:
        query = query.where(Trade.entry_time >= start_date)

    if end_date:
        query = query.where(Trade.entry_time <= end_date)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Paginate
    query = query.order_by(Trade.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    trades = result.scalars().all()

    return TradeListResponse(
        trades=trades,
        total=total,
        page=page,
        page_size=page_size,
    )
