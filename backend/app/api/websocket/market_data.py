"""
WebSocket endpoint for real-time market data.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Set
import asyncio
import json

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User
from app.api.websocket.manager import manager

router = APIRouter()


class MarketDataHub:
    """
    Manages market data subscriptions and broadcasting.

    Aggregates symbol subscriptions across all users and
    distributes market data efficiently.
    """

    def __init__(self):
        # All subscribed symbols across all users
        self.subscribed_symbols: Set[str] = set()

        # Symbol -> last price (for new subscribers)
        self.last_prices: dict = {}

    def add_symbol(self, symbol: str):
        """Add a symbol to global subscription."""
        self.subscribed_symbols.add(symbol)

    def remove_symbol(self, symbol: str):
        """Remove a symbol if no one is subscribed."""
        # Check if anyone is still subscribed
        topic = f"market:{symbol}"
        if manager.get_topic_subscriber_count(topic) == 0:
            self.subscribed_symbols.discard(symbol)

    def update_price(self, symbol: str, data: dict):
        """Update cached price for a symbol."""
        self.last_prices[symbol] = data

    def get_last_price(self, symbol: str) -> Optional[dict]:
        """Get last known price for a symbol."""
        return self.last_prices.get(symbol)

    def get_subscribed_symbols(self) -> Set[str]:
        """Get all subscribed symbols."""
        return self.subscribed_symbols.copy()


# Global market data hub
market_hub = MarketDataHub()


async def get_user_from_token(token: str) -> Optional[str]:
    """Validate token and get user ID."""
    try:
        payload = decode_access_token(token)
        if not payload:
            return None
        return payload.get("sub")
    except Exception:
        return None


@router.websocket("/market")
async def market_data_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time market data.

    Connect with: ws://host/ws/market?token=<jwt_token>

    Send messages:
    - {"type": "subscribe", "symbols": ["NSE:RELIANCE", "NSE:TCS"]}
    - {"type": "unsubscribe", "symbols": ["NSE:RELIANCE"]}

    Receives:
    - {"type": "quote", "symbol": "NSE:RELIANCE", "data": {...}}
    """
    # Validate token
    user_id = await get_user_from_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Accept connection
    await manager.connect(websocket, user_id)

    try:
        # Handle messages
        while True:
            try:
                data = await websocket.receive_json()
                await handle_market_message(websocket, data)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })

    finally:
        # Clean up subscriptions
        await cleanup_subscriptions(websocket)
        await manager.disconnect(websocket)


async def handle_market_message(websocket: WebSocket, data: dict):
    """Handle market data subscription messages."""
    msg_type = data.get("type")

    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})

    elif msg_type == "subscribe":
        symbols = data.get("symbols", [])
        await subscribe_symbols(websocket, symbols)

    elif msg_type == "unsubscribe":
        symbols = data.get("symbols", [])
        await unsubscribe_symbols(websocket, symbols)

    elif msg_type == "get_quote":
        symbol = data.get("symbol")
        if symbol:
            last_price = market_hub.get_last_price(symbol)
            if last_price:
                await websocket.send_json({
                    "type": "quote",
                    "symbol": symbol,
                    "data": last_price
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"No data available for {symbol}"
                })

    else:
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown message type: {msg_type}"
        })


async def subscribe_symbols(websocket: WebSocket, symbols: list):
    """Subscribe to market data for symbols."""
    subscribed = []

    for symbol in symbols:
        topic = f"market:{symbol}"
        await manager.subscribe_to_topic(websocket, topic)
        market_hub.add_symbol(symbol)
        subscribed.append(symbol)

        # Send last known price if available
        last_price = market_hub.get_last_price(symbol)
        if last_price:
            await websocket.send_json({
                "type": "quote",
                "symbol": symbol,
                "data": last_price
            })

    await websocket.send_json({
        "type": "subscribed",
        "symbols": subscribed
    })


async def unsubscribe_symbols(websocket: WebSocket, symbols: list):
    """Unsubscribe from market data for symbols."""
    unsubscribed = []

    for symbol in symbols:
        topic = f"market:{symbol}"
        await manager.unsubscribe_from_topic(websocket, topic)
        market_hub.remove_symbol(symbol)
        unsubscribed.append(symbol)

    await websocket.send_json({
        "type": "unsubscribed",
        "symbols": unsubscribed
    })


async def cleanup_subscriptions(websocket: WebSocket):
    """Clean up all subscriptions for a websocket."""
    # Find all market topics this websocket is subscribed to
    topics_to_clean = []
    for topic in manager.topic_subscriptions:
        if topic.startswith("market:") and websocket in manager.topic_subscriptions[topic]:
            topics_to_clean.append(topic)

    for topic in topics_to_clean:
        symbol = topic.replace("market:", "")
        await manager.unsubscribe_from_topic(websocket, topic)
        market_hub.remove_symbol(symbol)


# Functions to broadcast market data from broker feeds

async def broadcast_quote(symbol: str, quote_data: dict):
    """
    Broadcast a market quote to all subscribers.

    Called by market data handlers when new data arrives.
    """
    # Update cache
    market_hub.update_price(symbol, quote_data)

    # Broadcast to subscribers
    topic = f"market:{symbol}"
    await manager.broadcast_to_topic(topic, {
        "type": "quote",
        "symbol": symbol,
        "data": quote_data
    })


async def broadcast_trade(symbol: str, trade_data: dict):
    """Broadcast a trade to all subscribers."""
    topic = f"market:{symbol}"
    await manager.broadcast_to_topic(topic, {
        "type": "trade",
        "symbol": symbol,
        "data": trade_data
    })


async def broadcast_depth(symbol: str, depth_data: dict):
    """Broadcast market depth to all subscribers."""
    topic = f"market:{symbol}"
    await manager.broadcast_to_topic(topic, {
        "type": "depth",
        "symbol": symbol,
        "data": depth_data
    })
