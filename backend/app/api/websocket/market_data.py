"""
WebSocket endpoint for real-time market data.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Set, Dict, List, Tuple
import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User
from app.api.websocket.manager import manager

router = APIRouter()

# Index symbols for auto-subscription
INDEX_SYMBOLS = {
    "NIFTY50": {"symbol": "NSE:NIFTY50-INDEX", "display_name": "NIFTY 50"},
    "BANKNIFTY": {"symbol": "NSE:NIFTYBANK-INDEX", "display_name": "BANK NIFTY"},
    "SENSEX": {"symbol": "BSE:SENSEX-INDEX", "display_name": "SENSEX"},
    "BANKEX": {"symbol": "BSE:BANKEX-INDEX", "display_name": "BANKEX"},
}

# Special topic for index updates
INDICES_TOPIC = "market:indices"


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

        # Index values cache: key -> {ltp, change, change_percent, ...}
        self.index_values: Dict[str, dict] = {}

    def update_index(self, index_key: str, data: dict):
        """Update cached index value."""
        self.index_values[index_key] = data

    def get_index_values(self) -> Dict[str, dict]:
        """Get all cached index values."""
        return self.index_values.copy()

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


class CandleAggregator:
    """
    Aggregates quote updates into candles for real-time chart updates.

    Maintains current candles for each symbol-interval pair and broadcasts
    completed candles when intervals close.
    """

    # Interval to minutes mapping
    INTERVAL_MINUTES = {
        "1min": 1,
        "5min": 5,
        "15min": 15,
        "30min": 30,
        "1hour": 60,
        "1day": 1440,
    }

    def __init__(self):
        # Current candles: (symbol, interval) -> candle_data
        self.current_candles: Dict[Tuple[str, str], dict] = {}

        # Last broadcast time for partial updates: (symbol, interval) -> timestamp
        self.last_broadcast: Dict[Tuple[str, str], datetime] = {}

        # Broadcast partial updates every N seconds
        self.partial_update_interval = 5

    def _get_candle_start_time(self, timestamp: datetime, interval: str) -> datetime:
        """Calculate the start time of the candle for a given timestamp."""
        minutes = self.INTERVAL_MINUTES.get(interval, 5)

        if interval == "1day":
            # Round to start of day
            return datetime(timestamp.year, timestamp.month, timestamp.day)
        else:
            # Round down to nearest interval
            total_minutes = timestamp.hour * 60 + timestamp.minute
            candle_minutes = (total_minutes // minutes) * minutes
            hours = candle_minutes // 60
            mins = candle_minutes % 60
            return datetime(
                timestamp.year, timestamp.month, timestamp.day,
                hours, mins, 0, 0
            )

    async def process_quote(self, symbol: str, interval: str, quote_data: dict):
        """
        Process a quote update and update the current candle.

        Args:
            symbol: Trading symbol
            interval: Candle interval
            quote_data: Quote data with ltp, timestamp, etc.

        Returns:
            Tuple of (completed_candle, should_broadcast_partial)
        """
        key = (symbol, interval)

        # Extract price and timestamp
        ltp = quote_data.get("ltp")
        if not ltp:
            return None, False

        # Parse timestamp
        timestamp_str = quote_data.get("timestamp")
        if timestamp_str:
            try:
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = timestamp_str
            except:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()

        # Get candle start time
        candle_start = self._get_candle_start_time(timestamp, interval)

        # Check if we have a current candle
        current = self.current_candles.get(key)

        # Determine if we need to complete the previous candle
        completed_candle = None
        if current and current["timestamp"] != candle_start:
            # Previous candle is complete
            completed_candle = current.copy()
            current = None

        # Create new candle or update existing
        if not current:
            # Start new candle
            volume = int(quote_data.get("volume", 0))
            self.current_candles[key] = {
                "timestamp": candle_start,
                "open": float(ltp),
                "high": float(ltp),
                "low": float(ltp),
                "close": float(ltp),
                "volume": volume,
                "last_update": timestamp,
            }
        else:
            # Update existing candle
            current["high"] = max(current["high"], float(ltp))
            current["low"] = min(current["low"], float(ltp))
            current["close"] = float(ltp)
            current["volume"] = int(quote_data.get("volume", current["volume"]))
            current["last_update"] = timestamp

        # Check if we should broadcast a partial update
        should_broadcast = False
        last_broadcast_time = self.last_broadcast.get(key)
        if not last_broadcast_time or \
           (timestamp - last_broadcast_time).total_seconds() >= self.partial_update_interval:
            should_broadcast = True
            self.last_broadcast[key] = timestamp

        return completed_candle, should_broadcast

    def get_current_candle(self, symbol: str, interval: str) -> Optional[dict]:
        """Get the current candle for a symbol-interval pair."""
        return self.current_candles.get((symbol, interval))

    def clear_symbol(self, symbol: str):
        """Clear all candles for a symbol."""
        keys_to_remove = [k for k in self.current_candles.keys() if k[0] == symbol]
        for key in keys_to_remove:
            self.current_candles.pop(key, None)
            self.last_broadcast.pop(key, None)


# Global market data hub
market_hub = MarketDataHub()

# Global candle aggregator
candle_aggregator = CandleAggregator()


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

    # Auto-subscribe to indices topic
    await manager.subscribe_to_topic(websocket, INDICES_TOPIC)

    # Send current index values if available
    index_values = market_hub.get_index_values()
    if index_values:
        await websocket.send_json({
            "type": "indices",
            "data": index_values
        })

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

    elif msg_type == "subscribe_candles":
        # Subscribe to candle updates for symbols with specific intervals
        symbols = data.get("symbols", [])
        interval = data.get("interval", "5min")
        await subscribe_candles(websocket, symbols, interval)

    elif msg_type == "unsubscribe_candles":
        # Unsubscribe from candle updates
        symbols = data.get("symbols", [])
        interval = data.get("interval", "5min")
        await unsubscribe_candles(websocket, symbols, interval)

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

    elif msg_type == "get_current_candle":
        # Get current candle for a symbol-interval pair
        symbol = data.get("symbol")
        interval = data.get("interval", "5min")
        if symbol:
            candle = candle_aggregator.get_current_candle(symbol, interval)
            if candle:
                await websocket.send_json({
                    "type": "candle",
                    "symbol": symbol,
                    "interval": interval,
                    "data": candle
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"No candle data available for {symbol} @ {interval}"
                })

    elif msg_type == "get_indices":
        # Return current index values
        index_values = market_hub.get_index_values()
        await websocket.send_json({
            "type": "indices",
            "data": index_values
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


async def subscribe_candles(websocket: WebSocket, symbols: list, interval: str):
    """
    Subscribe to candle updates for symbols.

    This subscribes to both quote updates (for candle aggregation) and
    a dedicated candles topic for receiving candle completion notifications.
    """
    subscribed = []

    for symbol in symbols:
        # Subscribe to quote topic (for candle building)
        quote_topic = f"market:{symbol}"
        await manager.subscribe_to_topic(websocket, quote_topic)
        market_hub.add_symbol(symbol)

        # Subscribe to candles topic for this symbol-interval pair
        candle_topic = f"candles:{symbol}:{interval}"
        await manager.subscribe_to_topic(websocket, candle_topic)

        subscribed.append(symbol)

        # Send current candle if available
        current_candle = candle_aggregator.get_current_candle(symbol, interval)
        if current_candle:
            await websocket.send_json({
                "type": "candle",
                "symbol": symbol,
                "interval": interval,
                "data": current_candle,
                "is_partial": True
            })

    await websocket.send_json({
        "type": "candles_subscribed",
        "symbols": subscribed,
        "interval": interval
    })


async def unsubscribe_candles(websocket: WebSocket, symbols: list, interval: str):
    """Unsubscribe from candle updates for symbols."""
    unsubscribed = []

    for symbol in symbols:
        # Unsubscribe from candles topic
        candle_topic = f"candles:{symbol}:{interval}"
        await manager.unsubscribe_from_topic(websocket, candle_topic)
        unsubscribed.append(symbol)

        # Also unsubscribe from quotes if no other candle subscriptions exist
        # (This is simplified - in production, you'd track active subscriptions)

    await websocket.send_json({
        "type": "candles_unsubscribed",
        "symbols": unsubscribed,
        "interval": interval
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


async def broadcast_index_update(index_key: str, index_data: dict):
    """
    Broadcast a single index update to all connected clients.

    Args:
        index_key: Index identifier (e.g., "NIFTY50", "BANKNIFTY")
        index_data: Index data including ltp, change, change_percent, etc.
    """
    # Update cache
    market_hub.update_index(index_key, index_data)

    # Broadcast to all clients subscribed to indices topic
    await manager.broadcast_to_topic(INDICES_TOPIC, {
        "type": "index_update",
        "index": index_key,
        "data": index_data
    })


async def broadcast_all_indices(indices_data: Dict[str, dict]):
    """
    Broadcast all index values to all connected clients.

    Args:
        indices_data: Dictionary of index_key -> index_data
    """
    # Update cache for all indices
    for key, data in indices_data.items():
        market_hub.update_index(key, data)

    # Broadcast to all clients subscribed to indices topic
    await manager.broadcast_to_topic(INDICES_TOPIC, {
        "type": "indices",
        "data": indices_data
    })


async def broadcast_quote_with_candles(symbol: str, quote_data: dict, intervals: List[str] = None):
    """
    Broadcast a market quote and update candles for all intervals.

    This is an enhanced version of broadcast_quote that also handles candle
    aggregation for real-time chart updates.

    Args:
        symbol: Trading symbol
        quote_data: Quote data with ltp, timestamp, etc.
        intervals: List of intervals to aggregate (default: all supported)
    """
    # First, do the normal quote broadcast
    await broadcast_quote(symbol, quote_data)

    # Then, aggregate into candles for each interval
    if intervals is None:
        intervals = ["1min", "5min", "15min", "30min", "1hour"]

    for interval in intervals:
        # Process quote and check for candle completion
        completed_candle, should_broadcast = await candle_aggregator.process_quote(
            symbol, interval, quote_data
        )

        # If candle completed, broadcast it
        if completed_candle:
            await broadcast_candle(symbol, interval, completed_candle, is_partial=False)

        # If partial update needed, broadcast current candle
        elif should_broadcast:
            current_candle = candle_aggregator.get_current_candle(symbol, interval)
            if current_candle:
                await broadcast_candle(symbol, interval, current_candle, is_partial=True)


async def broadcast_candle(symbol: str, interval: str, candle_data: dict, is_partial: bool = False):
    """
    Broadcast a candle update to all subscribers.

    Args:
        symbol: Trading symbol
        interval: Candle interval
        candle_data: Candle OHLCV data
        is_partial: Whether this is a partial update (current candle) or completed
    """
    topic = f"candles:{symbol}:{interval}"
    await manager.broadcast_to_topic(topic, {
        "type": "candle",
        "symbol": symbol,
        "interval": interval,
        "data": candle_data,
        "is_partial": is_partial
    })
