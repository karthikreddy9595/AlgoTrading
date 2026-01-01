"""
Admin API for monitoring and kill switch control.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_admin_user
from app.models import User, StrategySubscription, Order, Trade

router = APIRouter(prefix="/monitoring", tags=["Admin - Monitoring"])


class KillSwitchRequest(BaseModel):
    reason: str
    scope: str = "global"  # global, user, strategy
    target_id: Optional[str] = None


@router.get("/dashboard")
async def get_monitoring_dashboard(
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get monitoring dashboard data.
    """
    # Active strategies count
    result = await db.execute(
        select(func.count(StrategySubscription.id)).where(
            StrategySubscription.status == "active"
        )
    )
    active_strategies = result.scalar()

    # Today's orders
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= today_start)
    )
    today_orders = result.scalar()

    # Today's trades
    result = await db.execute(
        select(func.count(Trade.id)).where(Trade.created_at >= today_start)
    )
    today_trades = result.scalar()

    # Total PnL today
    result = await db.execute(
        select(func.sum(StrategySubscription.today_pnl))
    )
    today_pnl = result.scalar() or 0

    # Total capital deployed
    result = await db.execute(
        select(func.sum(StrategySubscription.capital_allocated)).where(
            StrategySubscription.status == "active"
        )
    )
    total_capital = result.scalar() or 0

    return {
        "active_strategies": active_strategies,
        "today_orders": today_orders,
        "today_trades": today_trades,
        "today_pnl": float(today_pnl),
        "total_capital": float(total_capital),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/active-strategies")
async def get_active_strategies(
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all active strategy subscriptions with details.
    """
    result = await db.execute(
        select(StrategySubscription).where(
            StrategySubscription.status == "active"
        )
    )
    subscriptions = result.scalars().all()

    return [
        {
            "id": str(sub.id),
            "user_id": str(sub.user_id),
            "strategy_id": str(sub.strategy_id),
            "status": sub.status,
            "capital_allocated": float(sub.capital_allocated),
            "is_paper_trading": sub.is_paper_trading,
            "current_pnl": float(sub.current_pnl),
            "today_pnl": float(sub.today_pnl),
            "max_drawdown_percent": float(sub.max_drawdown_percent),
            "last_started_at": sub.last_started_at.isoformat() if sub.last_started_at else None,
        }
        for sub in subscriptions
    ]


@router.get("/kill-switch/status")
async def get_kill_switch_status(
    request: Request,
    admin: User = Depends(get_current_admin_user),
):
    """
    Get current kill switch status.
    """
    import redis.asyncio as redis_client
    from execution_engine.kill_switch import KillSwitch

    redis = request.app.state.redis
    kill_switch = KillSwitch(redis)

    global_state = await kill_switch.get_global_state()

    return {
        "global_active": global_state.is_active if global_state else False,
        "global_reason": global_state.reason if global_state else None,
        "global_activated_by": global_state.activated_by if global_state else None,
        "global_activated_at": global_state.activated_at.isoformat() if global_state else None,
    }


@router.post("/kill-switch/activate")
async def activate_kill_switch(
    request: Request,
    kill_request: KillSwitchRequest,
    admin: User = Depends(get_current_admin_user),
):
    """
    Activate kill switch.
    """
    from execution_engine.kill_switch import KillSwitch

    redis = request.app.state.redis
    kill_switch = KillSwitch(redis)

    if kill_request.scope == "global":
        await kill_switch.activate_global(
            reason=kill_request.reason,
            activated_by=str(admin.id),
        )
        return {"message": "Global kill switch activated"}

    elif kill_request.scope == "user":
        if not kill_request.target_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_id required for user scope",
            )
        await kill_switch.activate_for_user(
            user_id=kill_request.target_id,
            reason=kill_request.reason,
            activated_by=str(admin.id),
        )
        return {"message": f"Kill switch activated for user {kill_request.target_id}"}

    elif kill_request.scope == "strategy":
        if not kill_request.target_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_id required for strategy scope",
            )
        await kill_switch.activate_for_strategy(
            subscription_id=kill_request.target_id,
            reason=kill_request.reason,
            activated_by=str(admin.id),
        )
        return {"message": f"Kill switch activated for strategy {kill_request.target_id}"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid scope",
    )


@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch(
    request: Request,
    scope: str = "global",
    target_id: Optional[str] = None,
    admin: User = Depends(get_current_admin_user),
):
    """
    Deactivate kill switch.
    """
    from execution_engine.kill_switch import KillSwitch

    redis = request.app.state.redis
    kill_switch = KillSwitch(redis)

    if scope == "global":
        await kill_switch.deactivate_global(deactivated_by=str(admin.id))
        return {"message": "Global kill switch deactivated"}

    elif scope == "user" and target_id:
        await kill_switch.deactivate_for_user(target_id)
        return {"message": f"Kill switch deactivated for user {target_id}"}

    elif scope == "strategy" and target_id:
        await kill_switch.deactivate_for_strategy(target_id)
        return {"message": f"Kill switch deactivated for strategy {target_id}"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid scope or missing target_id",
    )


@router.get("/recent-orders")
async def get_recent_orders(
    limit: int = 50,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent orders across all users.
    """
    result = await db.execute(
        select(Order)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    orders = result.scalars().all()

    return [
        {
            "id": str(order.id),
            "subscription_id": str(order.subscription_id),
            "symbol": order.symbol,
            "exchange": order.exchange,
            "order_type": order.order_type,
            "transaction_type": order.transaction_type,
            "quantity": order.quantity,
            "price": float(order.price) if order.price else None,
            "status": order.status,
            "reason": order.reason,
            "created_at": order.created_at.isoformat(),
        }
        for order in orders
    ]


@router.get("/recent-trades")
async def get_recent_trades(
    limit: int = 50,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent trades across all users.
    """
    result = await db.execute(
        select(Trade)
        .order_by(Trade.created_at.desc())
        .limit(limit)
    )
    trades = result.scalars().all()

    return [
        {
            "id": str(trade.id),
            "subscription_id": str(trade.subscription_id),
            "symbol": trade.symbol,
            "exchange": trade.exchange,
            "side": trade.side,
            "quantity": trade.quantity,
            "entry_price": float(trade.entry_price),
            "exit_price": float(trade.exit_price) if trade.exit_price else None,
            "pnl": float(trade.pnl) if trade.pnl else None,
            "status": trade.status,
            "entry_time": trade.entry_time.isoformat(),
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
        }
        for trade in trades
    ]
