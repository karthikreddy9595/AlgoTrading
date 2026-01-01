"""
Fyers Broker Integration

This module provides integration with Fyers trading API for:
- OAuth authentication
- Order placement and management
- Real-time market data via WebSocket
- Position and order tracking
"""

import asyncio
import hashlib
import json
from typing import List, Optional, Callable, Dict, Any
from decimal import Decimal
from datetime import datetime
from urllib.parse import urlencode
import aiohttp

from brokers.base import (
    BaseBroker,
    BrokerCredentials,
    BrokerOrder,
    BrokerPosition,
    MarketQuote,
    OrderStatus,
)
from app.core.config import settings


class FyersBroker(BaseBroker):
    """
    Fyers broker integration for live trading.

    Implements the BaseBroker interface for Fyers API v3.
    """

    name = "Fyers"

    # API endpoints
    BASE_URL = "https://api-t1.fyers.in/api/v3"
    DATA_URL = "https://api-t1.fyers.in/data"
    AUTH_URL = "https://api-t1.fyers.in/api/v3/generate-authcode"
    TOKEN_URL = "https://api-t1.fyers.in/api/v3/validate-authcode"

    def __init__(self):
        super().__init__()
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._subscribed_symbols: List[str] = []
        self._market_data_callback: Optional[Callable] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            "Authorization": f"{self.credentials.client_id}:{self.credentials.access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def generate_auth_url(client_id: str, redirect_uri: str, state: str = "") -> str:
        """
        Generate OAuth authorization URL.

        Args:
            client_id: Fyers app ID
            redirect_uri: OAuth callback URL
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{FyersBroker.AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_auth_code(
        client_id: str,
        secret_key: str,
        auth_code: str,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            client_id: Fyers app ID
            secret_key: Fyers secret key
            auth_code: Authorization code from OAuth callback

        Returns:
            Token response with access_token
        """
        # Generate app ID hash
        app_id_hash = hashlib.sha256(
            f"{client_id}:{secret_key}".encode()
        ).hexdigest()

        payload = {
            "grant_type": "authorization_code",
            "appIdHash": app_id_hash,
            "code": auth_code,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                FyersBroker.TOKEN_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                data = await response.json()

                if data.get("s") != "ok":
                    raise Exception(f"Token exchange failed: {data.get('message')}")

                return data

    async def connect(self, credentials: BrokerCredentials) -> bool:
        """Connect to Fyers API."""
        self.credentials = credentials

        try:
            # Verify connection by fetching profile
            profile = await self.get_profile()
            if profile:
                self.is_connected = True
                return True
            return False
        except Exception as e:
            print(f"Fyers connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Fyers API."""
        self.is_connected = False

        # Close WebSocket
        if self._ws and not self._ws.closed:
            await self._ws.close()

        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

        # Close HTTP session
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_profile(self) -> dict:
        """Get user profile information."""
        session = await self._get_session()

        async with session.get(
            f"{self.BASE_URL}/profile",
            headers=self._get_headers(),
        ) as response:
            data = await response.json()

            if data.get("s") != "ok":
                raise Exception(f"Failed to get profile: {data.get('message')}")

            return data.get("data", {})

    async def get_funds(self) -> dict:
        """Get available funds/margin."""
        session = await self._get_session()

        async with session.get(
            f"{self.BASE_URL}/funds",
            headers=self._get_headers(),
        ) as response:
            data = await response.json()

            if data.get("s") != "ok":
                raise Exception(f"Failed to get funds: {data.get('message')}")

            return data.get("fund_limit", [])

    async def place_order(
        self,
        symbol: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        price: Optional[Decimal] = None,
        trigger_price: Optional[Decimal] = None,
        product_type: str = "INTRADAY",
    ) -> BrokerOrder:
        """Place an order with Fyers."""
        session = await self._get_session()

        # Map order type to Fyers format
        order_type_map = {
            "MARKET": 2,
            "LIMIT": 1,
            "SL": 3,
            "SL-M": 4,
        }

        # Map product type
        product_type_map = {
            "INTRADAY": "INTRADAY",
            "CNC": "CNC",
            "MARGIN": "MARGIN",
            "CO": "CO",
            "BO": "BO",
        }

        # Construct Fyers symbol format
        fyers_symbol = f"{exchange}:{symbol}"

        payload = {
            "symbol": fyers_symbol,
            "qty": quantity,
            "type": order_type_map.get(order_type, 2),
            "side": 1 if transaction_type == "BUY" else -1,
            "productType": product_type_map.get(product_type, "INTRADAY"),
            "limitPrice": float(price) if price else 0,
            "stopPrice": float(trigger_price) if trigger_price else 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
        }

        async with session.post(
            f"{self.BASE_URL}/orders",
            json=payload,
            headers=self._get_headers(),
        ) as response:
            data = await response.json()

            status = OrderStatus.PLACED if data.get("s") == "ok" else OrderStatus.REJECTED

            return BrokerOrder(
                order_id=data.get("id", ""),
                broker_order_id=data.get("id", ""),
                symbol=symbol,
                exchange=exchange,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=order_type,
                price=price,
                trigger_price=trigger_price,
                status=status,
                filled_quantity=0,
                filled_price=None,
                message=data.get("message", ""),
                placed_at=datetime.utcnow(),
            )

    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[Decimal] = None,
        trigger_price: Optional[Decimal] = None,
    ) -> BrokerOrder:
        """Modify an existing order."""
        session = await self._get_session()

        payload = {"id": order_id}
        if quantity:
            payload["qty"] = quantity
        if price:
            payload["limitPrice"] = float(price)
        if trigger_price:
            payload["stopPrice"] = float(trigger_price)

        async with session.put(
            f"{self.BASE_URL}/orders",
            json=payload,
            headers=self._get_headers(),
        ) as response:
            data = await response.json()

            if data.get("s") != "ok":
                raise Exception(f"Failed to modify order: {data.get('message')}")

            # Fetch updated order
            return await self.get_order_status(order_id)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        session = await self._get_session()

        async with session.delete(
            f"{self.BASE_URL}/orders",
            json={"id": order_id},
            headers=self._get_headers(),
        ) as response:
            data = await response.json()
            return data.get("s") == "ok"

    async def get_order_status(self, order_id: str) -> BrokerOrder:
        """Get status of a specific order."""
        orders = await self.get_orders()

        for order in orders:
            if order.order_id == order_id or order.broker_order_id == order_id:
                return order

        raise Exception(f"Order {order_id} not found")

    async def get_orders(self) -> List[BrokerOrder]:
        """Get all orders for today."""
        session = await self._get_session()

        async with session.get(
            f"{self.BASE_URL}/orders",
            headers=self._get_headers(),
        ) as response:
            data = await response.json()

            if data.get("s") != "ok":
                return []

            orders = []
            for o in data.get("orderBook", []):
                # Map Fyers status to our status
                status_map = {
                    1: OrderStatus.PENDING,
                    2: OrderStatus.FILLED,
                    3: OrderStatus.OPEN,
                    4: OrderStatus.PENDING,
                    5: OrderStatus.REJECTED,
                    6: OrderStatus.CANCELLED,
                }

                orders.append(BrokerOrder(
                    order_id=str(o.get("id", "")),
                    broker_order_id=str(o.get("id", "")),
                    symbol=o.get("symbol", "").split(":")[-1],
                    exchange=o.get("symbol", "").split(":")[0] if ":" in o.get("symbol", "") else "NSE",
                    transaction_type="BUY" if o.get("side") == 1 else "SELL",
                    quantity=o.get("qty", 0),
                    order_type=["LIMIT", "MARKET", "SL", "SL-M"][o.get("type", 2) - 1],
                    price=Decimal(str(o.get("limitPrice", 0))) if o.get("limitPrice") else None,
                    trigger_price=Decimal(str(o.get("stopPrice", 0))) if o.get("stopPrice") else None,
                    status=status_map.get(o.get("status"), OrderStatus.PENDING),
                    filled_quantity=o.get("filledQty", 0),
                    filled_price=Decimal(str(o.get("tradedPrice", 0))) if o.get("tradedPrice") else None,
                    message=o.get("message", ""),
                ))

            return orders

    async def get_positions(self) -> List[BrokerPosition]:
        """Get current positions."""
        session = await self._get_session()

        async with session.get(
            f"{self.BASE_URL}/positions",
            headers=self._get_headers(),
        ) as response:
            data = await response.json()

            if data.get("s") != "ok":
                return []

            positions = []
            for p in data.get("netPositions", []):
                symbol_parts = p.get("symbol", "").split(":")
                positions.append(BrokerPosition(
                    symbol=symbol_parts[-1] if symbol_parts else "",
                    exchange=symbol_parts[0] if len(symbol_parts) > 1 else "NSE",
                    quantity=p.get("netQty", 0),
                    avg_price=Decimal(str(p.get("avgPrice", 0))),
                    ltp=Decimal(str(p.get("ltp", 0))),
                    pnl=Decimal(str(p.get("pl", 0))),
                    product_type=p.get("productType", "INTRADAY"),
                ))

            return positions

    async def get_quote(self, symbol: str, exchange: str) -> MarketQuote:
        """Get current market quote."""
        session = await self._get_session()

        fyers_symbol = f"{exchange}:{symbol}"

        async with session.get(
            f"{self.DATA_URL}/quotes",
            params={"symbols": fyers_symbol},
            headers=self._get_headers(),
        ) as response:
            data = await response.json()

            if data.get("s") != "ok" or not data.get("d"):
                raise Exception(f"Failed to get quote for {fyers_symbol}")

            q = data["d"][0]["v"]

            return MarketQuote(
                symbol=symbol,
                exchange=exchange,
                ltp=Decimal(str(q.get("lp", 0))),
                open=Decimal(str(q.get("open_price", 0))),
                high=Decimal(str(q.get("high_price", 0))),
                low=Decimal(str(q.get("low_price", 0))),
                close=Decimal(str(q.get("prev_close_price", 0))),
                volume=q.get("volume", 0),
                bid=Decimal(str(q.get("bid", 0))),
                ask=Decimal(str(q.get("ask", 0))),
                bid_qty=q.get("bidSize", 0),
                ask_qty=q.get("askSize", 0),
                timestamp=datetime.utcnow(),
            )

    async def subscribe_market_data(
        self,
        symbols: List[str],
        callback: Callable[[MarketQuote], None],
    ) -> None:
        """Subscribe to real-time market data via WebSocket."""
        self._subscribed_symbols.extend(symbols)
        self._market_data_callback = callback

        # Start WebSocket connection if not running
        if not self._ws_task or self._ws_task.done():
            self._ws_task = asyncio.create_task(self._run_websocket())

    async def _run_websocket(self):
        """Run WebSocket connection for market data."""
        ws_url = f"wss://api-t1.fyers.in/socket/v2/dataSock?access_token={self.credentials.client_id}:{self.credentials.access_token}"

        try:
            session = await self._get_session()
            async with session.ws_connect(ws_url) as ws:
                self._ws = ws

                # Subscribe to symbols
                subscribe_msg = {
                    "T": "SUB_DATA",
                    "SLIST": self._subscribed_symbols,
                    "SUB_T": 1,  # Full market data
                }
                await ws.send_json(subscribe_msg)

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        await self._handle_ws_message(data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"WebSocket error: {ws.exception()}")
                        break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"WebSocket error: {e}")

    async def _handle_ws_message(self, data: dict):
        """Handle incoming WebSocket message."""
        if data.get("T") == "if" and self._market_data_callback:
            # Parse market data
            symbol_parts = data.get("s", "").split(":")
            symbol = symbol_parts[-1] if symbol_parts else ""
            exchange = symbol_parts[0] if len(symbol_parts) > 1 else "NSE"

            quote = MarketQuote(
                symbol=symbol,
                exchange=exchange,
                ltp=Decimal(str(data.get("lp", 0))),
                open=Decimal(str(data.get("o", 0))),
                high=Decimal(str(data.get("h", 0))),
                low=Decimal(str(data.get("l", 0))),
                close=Decimal(str(data.get("c", 0))),
                volume=data.get("v", 0),
                bid=Decimal(str(data.get("bp", 0))),
                ask=Decimal(str(data.get("sp", 0))),
                bid_qty=data.get("bq", 0),
                ask_qty=data.get("sq", 0),
                timestamp=datetime.utcnow(),
            )

            self._market_data_callback(quote)

    async def unsubscribe_market_data(self, symbols: List[str]) -> None:
        """Unsubscribe from market data."""
        for symbol in symbols:
            if symbol in self._subscribed_symbols:
                self._subscribed_symbols.remove(symbol)

        if self._ws and not self._ws.closed:
            unsubscribe_msg = {
                "T": "UNSUB_DATA",
                "SLIST": symbols,
            }
            await self._ws.send_json(unsubscribe_msg)

    async def get_margin(self) -> dict:
        """Get available margin/funds."""
        funds = await self.get_funds()

        # Parse fund limits
        available = 0
        used = 0
        total = 0

        for fund in funds:
            if fund.get("title") == "Total Balance":
                total = fund.get("equityAmount", 0)
            elif fund.get("title") == "Available Balance":
                available = fund.get("equityAmount", 0)
            elif fund.get("title") == "Utilized Amount":
                used = fund.get("equityAmount", 0)

        return {
            "available": available,
            "used": used,
            "total": total,
        }

    async def get_historical_data(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
    ) -> List[dict]:
        """Get historical OHLC data."""
        session = await self._get_session()

        # Map interval to Fyers format
        interval_map = {
            "1min": "1",
            "5min": "5",
            "15min": "15",
            "30min": "30",
            "1hour": "60",
            "1day": "D",
        }

        fyers_symbol = f"{exchange}:{symbol}"
        fyers_interval = interval_map.get(interval, "D")

        params = {
            "symbol": fyers_symbol,
            "resolution": fyers_interval,
            "date_format": "1",
            "range_from": int(from_date.timestamp()),
            "range_to": int(to_date.timestamp()),
            "cont_flag": "1",
        }

        async with session.get(
            f"{self.DATA_URL}/history",
            params=params,
            headers=self._get_headers(),
        ) as response:
            data = await response.json()

            if data.get("s") != "ok":
                return []

            candles = []
            for c in data.get("candles", []):
                candles.append({
                    "timestamp": datetime.fromtimestamp(c[0]),
                    "open": c[1],
                    "high": c[2],
                    "low": c[3],
                    "close": c[4],
                    "volume": c[5],
                })

            return candles
