"""
WebSocket endpoint for real-time portfolio updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import asyncio
import json

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, StrategySubscription, Position, Order
from app.api.websocket.manager import manager

router = APIRouter()


async def get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    """Validate token and get user."""
    try:
        payload = decode_access_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception:
        return None


@router.websocket("/portfolio")
async def portfolio_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time portfolio updates.

    Connect with: ws://host/ws/portfolio?token=<jwt_token>

    Receives:
    - Portfolio summary updates
    - Position changes
    - Order status updates
    - PnL updates
    """
    # Get database session
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # Validate token and get user
        user = await get_user_from_token(token, db)
        if not user:
            await websocket.close(code=4001, reason="Invalid or expired token")
            return

        user_id = str(user.id)

    # Accept connection
    await manager.connect(websocket, user_id)

    try:
        # Send initial portfolio state
        await send_portfolio_snapshot(websocket, user_id)

        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_json()
                await handle_client_message(websocket, user_id, data)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })

    finally:
        await manager.disconnect(websocket)


async def send_portfolio_snapshot(websocket: WebSocket, user_id: str):
    """Send current portfolio state to client."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # Get active subscriptions
        result = await db.execute(
            select(StrategySubscription).where(
                StrategySubscription.user_id == user_id,
                StrategySubscription.status.in_(["active", "paused"])
            )
        )
        subscriptions = result.scalars().all()

        # Get open positions
        subscription_ids = [str(sub.id) for sub in subscriptions]
        positions = []

        if subscription_ids:
            result = await db.execute(
                select(Position).where(
                    Position.subscription_id.in_(subscription_ids)
                )
            )
            positions = result.scalars().all()

        # Calculate totals
        total_pnl = sum(float(sub.current_pnl) for sub in subscriptions)
        today_pnl = sum(float(sub.today_pnl) for sub in subscriptions)
        total_capital = sum(float(sub.capital_allocated) for sub in subscriptions)

        # Send snapshot
        await websocket.send_json({
            "type": "portfolio_snapshot",
            "data": {
                "summary": {
                    "total_capital": total_capital,
                    "total_pnl": total_pnl,
                    "today_pnl": today_pnl,
                    "active_strategies": len([s for s in subscriptions if s.status == "active"]),
                    "open_positions": len(positions),
                },
                "subscriptions": [
                    {
                        "id": str(sub.id),
                        "strategy_id": str(sub.strategy_id),
                        "status": sub.status,
                        "capital_allocated": float(sub.capital_allocated),
                        "current_pnl": float(sub.current_pnl),
                        "today_pnl": float(sub.today_pnl),
                        "is_paper_trading": sub.is_paper_trading,
                    }
                    for sub in subscriptions
                ],
                "positions": [
                    {
                        "id": str(pos.id),
                        "subscription_id": str(pos.subscription_id),
                        "symbol": pos.symbol,
                        "exchange": pos.exchange,
                        "quantity": pos.quantity,
                        "avg_price": float(pos.avg_price),
                        "current_price": float(pos.current_price) if pos.current_price else None,
                        "unrealized_pnl": float(pos.unrealized_pnl) if pos.unrealized_pnl else None,
                    }
                    for pos in positions
                ],
            }
        })


async def handle_client_message(websocket: WebSocket, user_id: str, data: dict):
    """Handle messages from the client."""
    msg_type = data.get("type")

    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})

    elif msg_type == "subscribe_symbols":
        # Subscribe to market data for symbols
        symbols = data.get("symbols", [])
        for symbol in symbols:
            await manager.subscribe_to_topic(websocket, f"market:{symbol}")
        await websocket.send_json({
            "type": "subscribed",
            "symbols": symbols
        })

    elif msg_type == "unsubscribe_symbols":
        symbols = data.get("symbols", [])
        for symbol in symbols:
            await manager.unsubscribe_from_topic(websocket, f"market:{symbol}")
        await websocket.send_json({
            "type": "unsubscribed",
            "symbols": symbols
        })

    elif msg_type == "refresh":
        # Refresh portfolio snapshot
        await send_portfolio_snapshot(websocket, user_id)

    else:
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown message type: {msg_type}"
        })


# Helper functions to send updates from other parts of the application

async def notify_position_update(user_id: str, position_data: dict):
    """Notify user of position update."""
    await manager.send_to_user(user_id, {
        "type": "position_update",
        "data": position_data
    })


async def notify_order_update(user_id: str, order_data: dict):
    """Notify user of order status update."""
    await manager.send_to_user(user_id, {
        "type": "order_update",
        "data": order_data
    })


async def notify_pnl_update(user_id: str, pnl_data: dict):
    """Notify user of PnL update."""
    await manager.send_to_user(user_id, {
        "type": "pnl_update",
        "data": pnl_data
    })


async def notify_strategy_status(user_id: str, subscription_id: str, status: str):
    """Notify user of strategy status change."""
    await manager.send_to_user(user_id, {
        "type": "strategy_status",
        "data": {
            "subscription_id": subscription_id,
            "status": status
        }
    })
