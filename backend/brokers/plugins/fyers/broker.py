"""
Fyers Broker Plugin Implementation

Provides integration with Fyers trading API v3 for:
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
from datetime import datetime, timedelta
from urllib.parse import urlencode
import aiohttp

from brokers.base import (
    BaseBroker,
    BrokerCredentials,
    BrokerOrder,
    BrokerPosition,
    MarketQuote,
    OrderStatus,
    BrokerMetadata,
    BrokerCapabilities,
    BrokerAuthConfig,
)


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

    # ==================== Plugin System Methods ====================

    @classmethod
    def get_metadata(cls) -> BrokerMetadata:
        """Return broker plugin metadata."""
        return BrokerMetadata(
            name="fyers",
            display_name="Fyers",
            version="1.0.0",
            description="Fyers trading broker integration with OAuth authentication",
            capabilities=BrokerCapabilities(
                trading=True,
                market_data=True,
                historical_data=True,
                streaming=True,
                options=True,
                futures=True,
                equity=True,
                commodities=False,
                currency=True,
            ),
            auth_config=BrokerAuthConfig(
                auth_type="oauth",
                requires_api_key=True,
                requires_api_secret=True,
                requires_totp=False,
                token_expiry_hours=12,
                oauth_auth_url=cls.AUTH_URL,
                oauth_token_url=cls.TOKEN_URL,
            ),
            exchanges=["NSE", "BSE", "NFO", "MCX", "CDS"],
            symbol_format="{exchange}:{symbol}",
            logo_url="/assets/brokers/fyers.png",
            config_schema={
                "app_id": {
                    "type": "string",
                    "required": True,
                    "env_var": "FYERS_APP_ID",
                },
                "secret_key": {
                    "type": "string",
                    "required": True,
                    "env_var": "FYERS_SECRET_KEY",
                    "sensitive": True,
                },
                "redirect_uri": {
                    "type": "string",
                    "required": True,
                    "env_var": "FYERS_REDIRECT_URI",
                },
            },
        )

    @classmethod
    def generate_auth_url(cls, config: Dict[str, Any], state: str) -> Optional[str]:
        """
        Generate OAuth authorization URL.

        Args:
            config: Broker configuration with app_id, redirect_uri
            state: State parameter for OAuth (usually user_id)

        Returns:
            Authorization URL to redirect user to
        """
        client_id = config.get("app_id")
        redirect_uri = config.get("redirect_uri")

        if not client_id or not redirect_uri:
            return None

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{cls.AUTH_URL}?{urlencode(params)}"

    @classmethod
    async def exchange_auth_code(
        cls, config: Dict[str, Any], auth_code: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            config: Broker configuration with app_id, secret_key
            auth_code: Authorization code from OAuth callback

        Returns:
            Token response with access_token
        """
        client_id = config.get("app_id")
        secret_key = config.get("secret_key")

        if not client_id or not secret_key:
            raise ValueError("app_id and secret_key are required")

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
                cls.TOKEN_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                data = await response.json()

                if data.get("s") != "ok":
                    raise Exception(f"Token exchange failed: {data.get('message')}")

                return data

    # ==================== Internal Helpers ====================

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

    def _format_symbol(self, symbol: str, exchange: str) -> str:
        """
        Format symbol according to Fyers symbology.

        Segments and formats:
        - Equity: {Ex}:{Symbol}-{Series} (e.g., NSE:SBIN-EQ, BSE:ACC-A)
        - Index: {Ex}:{Symbol}-INDEX (e.g., NSE:NIFTY50-INDEX)
        - Futures: {Ex}:{Symbol}{YY}{MMM}FUT (e.g., NSE:NIFTY20OCTFUT)
        - Options: {Ex}:{Symbol}{YY}{MMM}{Strike}{CE/PE} (e.g., NSE:NIFTY20OCT11000CE)
        - Currency: {Ex}:{Pair}{YY}{MMM}FUT (e.g., NSE:USDINR20OCTFUT)
        - Commodity: {Ex}:{Commodity}{YY}{MMM}FUT (e.g., MCX:CRUDEOIL20OCTFUT)
        """
        symbol_upper = symbol.upper()

        # Check if symbol is an index (ends with -INDEX)
        if symbol_upper.endswith('-INDEX'):
            return f"{exchange}:{symbol}"

        # Check if symbol already has equity series suffix (e.g., -EQ, -BE, -A, -T)
        if '-' in symbol and any(symbol_upper.endswith(f'-{s}') for s in ['EQ', 'BE', 'A', 'T', 'B', 'N']):
            return f"{exchange}:{symbol}"

        # Check if symbol is a derivative (ends with FUT, CE, or PE with digits before)
        # Futures end with FUT (e.g., NIFTY20OCTFUT)
        if symbol_upper.endswith('FUT'):
            return f"{exchange}:{symbol}"

        # Options end with CE or PE preceded by strike price digits (e.g., NIFTY20OCT11000CE)
        if (symbol_upper.endswith('CE') or symbol_upper.endswith('PE')) and len(symbol) > 2:
            # Check if there's a digit before CE/PE (indicating it's an option, not a stock like RELIANCE)
            if symbol[-3].isdigit():
                return f"{exchange}:{symbol}"

        # For NSE/BSE equity, append -EQ suffix
        if exchange.upper() in ["NSE", "BSE"]:
            return f"{exchange}:{symbol}-EQ"

        # For other exchanges (MCX, CDS, etc.), use symbol as-is
        return f"{exchange}:{symbol}"

    # ==================== BaseBroker Implementation ====================

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
        # type 1 = Limit, type 2 = Market, type 3 = Stop (SL-M), type 4 = Stop Limit (SL-L)
        order_type_map = {
            "LIMIT": 1,
            "MARKET": 2,
            "SL": 3,
            "SL-M": 3,
            "SL-L": 4,
        }

        # Map product type
        product_type_map = {
            "INTRADAY": "INTRADAY",
            "CNC": "CNC",
            "MARGIN": "MARGIN",
            "CO": "CO",
            "BO": "BO",
        }

        # Construct Fyers symbol format based on segment
        # Uses denormalize_symbol to handle equity suffix (-EQ) and other formats
        fyers_symbol = self._format_symbol(symbol, exchange)

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
            "stopLoss": 0,
            "takeProfit": 0,
            "isSliceOrder": False,
        }

        async with session.post(
            f"{self.BASE_URL}/orders/sync",
            json=payload,
            headers=self._get_headers(),
        ) as response:
            # Check response content type
            content_type = response.headers.get('Content-Type', '')

            if 'text/plain' in content_type or 'text/html' in content_type:
                # API returned plain text, likely an error
                text_response = await response.text()
                raise Exception(
                    f"Fyers API returned text response (status {response.status}): {text_response}. "
                    f"This usually indicates authentication or permission issues. "
                    f"Please verify your Fyers access token is valid and has trading permissions."
                )

            try:
                data = await response.json()
            except Exception as e:
                text_response = await response.text()
                raise Exception(
                    f"Failed to parse Fyers API response as JSON: {str(e)}. "
                    f"Response (status {response.status}): {text_response}"
                )

            # Check if order was successful
            if data.get("s") != "ok":
                error_msg = data.get("message", "Unknown error")
                raise Exception(f"Fyers order failed: {error_msg}")

            status = OrderStatus.PLACED

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

        fyers_symbol = self._format_symbol(symbol, exchange)

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

            # Handle both sync and async callbacks
            if asyncio.iscoroutinefunction(self._market_data_callback):
                await self._market_data_callback(quote)
            else:
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
        """
        Get historical OHLC data.

        Fyers API has limits on data range per request:
        - Intraday (1min to 240min): max 100 days per request
        - Daily: max 366 days per request

        This method automatically chunks requests to handle longer date ranges.
        """
        # Map interval to Fyers format
        interval_map = {
            "1min": "1",
            "5min": "5",
            "15min": "15",
            "30min": "30",
            "1hour": "60",
            "1day": "D",
        }

        # Max days per request based on interval (Fyers API limits)
        max_days_map = {
            "1min": 100,
            "5min": 100,
            "15min": 100,
            "30min": 100,
            "1hour": 100,
            "1day": 365,
        }

        # Use denormalize_symbol to get proper Fyers format (adds -EQ for equities)
        fyers_symbol = self.denormalize_symbol(symbol, exchange)
        fyers_interval = interval_map.get(interval, "D")
        max_days = max_days_map.get(interval, 100)

        # Calculate total days requested
        total_days = (to_date - from_date).days

        # If within limit, make single request
        if total_days <= max_days:
            return await self._fetch_historical_chunk(
                fyers_symbol, fyers_interval, from_date, to_date
            )

        # Otherwise, chunk the requests
        all_candles = []
        chunk_start = from_date

        while chunk_start < to_date:
            chunk_end = min(chunk_start + timedelta(days=max_days), to_date)

            try:
                chunk_data = await self._fetch_historical_chunk(
                    fyers_symbol, fyers_interval, chunk_start, chunk_end
                )
                all_candles.extend(chunk_data)
            except Exception as e:
                # Log but continue if a chunk fails (might be no data for that period)
                print(f"Warning: Failed to fetch chunk {chunk_start} to {chunk_end}: {e}")

            # Move to next chunk
            chunk_start = chunk_end

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)

        if not all_candles:
            raise Exception(
                f"No historical data available for {fyers_symbol} "
                f"from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}. "
                f"Please check if the symbol exists and the date range is valid."
            )

        # Sort by timestamp and remove duplicates
        all_candles.sort(key=lambda x: x["timestamp"])
        seen_timestamps = set()
        unique_candles = []
        for candle in all_candles:
            ts = candle["timestamp"]
            if ts not in seen_timestamps:
                seen_timestamps.add(ts)
                unique_candles.append(candle)

        return unique_candles

    async def _fetch_historical_chunk(
        self,
        fyers_symbol: str,
        fyers_interval: str,
        from_date: datetime,
        to_date: datetime,
    ) -> List[dict]:
        """Fetch a single chunk of historical data from Fyers API."""
        session = await self._get_session()

        params = {
            "symbol": fyers_symbol,
            "resolution": fyers_interval,
            "date_format": "0",  # 0 = Unix timestamp format
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
                error_msg = data.get("message", "Unknown error")
                error_code = data.get("code", "")
                raise Exception(
                    f"Fyers API error: {error_msg} (code: {error_code}). "
                    f"Symbol: {fyers_symbol}, Interval: {fyers_interval}, "
                    f"Range: {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
                )

            candles = data.get("candles", [])
            if not candles:
                return []  # Return empty list for chunks with no data

            result = []
            for c in candles:
                result.append({
                    "timestamp": datetime.fromtimestamp(c[0]),
                    "open": c[1],
                    "high": c[2],
                    "low": c[3],
                    "close": c[4],
                    "volume": c[5],
                })

            return result

    # ==================== Symbol Mapping ====================

    def normalize_symbol(self, broker_symbol: str) -> str:
        """Convert Fyers symbol to normalized format."""
        # Fyers format: "NSE:RELIANCE-EQ" -> "RELIANCE"
        if ":" in broker_symbol:
            broker_symbol = broker_symbol.split(":")[-1]
        if "-" in broker_symbol:
            broker_symbol = broker_symbol.split("-")[0]
        return broker_symbol

    def denormalize_symbol(self, symbol: str, exchange: str) -> str:
        """Convert normalized symbol to Fyers format."""
        # For equity, append -EQ suffix
        if exchange in ["NSE", "BSE"]:
            return f"{exchange}:{symbol}-EQ"
        return f"{exchange}:{symbol}"

    async def search_symbols(
        self,
        query: str,
        exchange: Optional[str] = None,
    ) -> List[dict]:
        """
        Search for tradeable symbols.

        Note: Fyers API doesn't have a direct symbol search endpoint.
        This implementation searches against a static list of popular symbols.
        In production, you could cache and search the symbol master file.

        Args:
            query: Search query (symbol name or partial match)
            exchange: Optional exchange filter (NSE, BSE, etc.)

        Returns:
            List of matching symbols with metadata
        """
        # Popular NSE symbols with company names
        symbols_data = [
            {"symbol": "RELIANCE", "exchange": "NSE", "name": "Reliance Industries Ltd", "segment": "EQ"},
            {"symbol": "TCS", "exchange": "NSE", "name": "Tata Consultancy Services Ltd", "segment": "EQ"},
            {"symbol": "HDFCBANK", "exchange": "NSE", "name": "HDFC Bank Ltd", "segment": "EQ"},
            {"symbol": "INFY", "exchange": "NSE", "name": "Infosys Ltd", "segment": "EQ"},
            {"symbol": "ICICIBANK", "exchange": "NSE", "name": "ICICI Bank Ltd", "segment": "EQ"},
            {"symbol": "HINDUNILVR", "exchange": "NSE", "name": "Hindustan Unilever Ltd", "segment": "EQ"},
            {"symbol": "SBIN", "exchange": "NSE", "name": "State Bank of India", "segment": "EQ"},
            {"symbol": "BHARTIARTL", "exchange": "NSE", "name": "Bharti Airtel Ltd", "segment": "EQ"},
            {"symbol": "ITC", "exchange": "NSE", "name": "ITC Ltd", "segment": "EQ"},
            {"symbol": "KOTAKBANK", "exchange": "NSE", "name": "Kotak Mahindra Bank Ltd", "segment": "EQ"},
            {"symbol": "LT", "exchange": "NSE", "name": "Larsen & Toubro Ltd", "segment": "EQ"},
            {"symbol": "AXISBANK", "exchange": "NSE", "name": "Axis Bank Ltd", "segment": "EQ"},
            {"symbol": "ASIANPAINT", "exchange": "NSE", "name": "Asian Paints Ltd", "segment": "EQ"},
            {"symbol": "MARUTI", "exchange": "NSE", "name": "Maruti Suzuki India Ltd", "segment": "EQ"},
            {"symbol": "SUNPHARMA", "exchange": "NSE", "name": "Sun Pharmaceutical Industries Ltd", "segment": "EQ"},
            {"symbol": "TITAN", "exchange": "NSE", "name": "Titan Company Ltd", "segment": "EQ"},
            {"symbol": "BAJFINANCE", "exchange": "NSE", "name": "Bajaj Finance Ltd", "segment": "EQ"},
            {"symbol": "WIPRO", "exchange": "NSE", "name": "Wipro Ltd", "segment": "EQ"},
            {"symbol": "ULTRACEMCO", "exchange": "NSE", "name": "UltraTech Cement Ltd", "segment": "EQ"},
            {"symbol": "NESTLEIND", "exchange": "NSE", "name": "Nestle India Ltd", "segment": "EQ"},
            {"symbol": "TATAMOTORS", "exchange": "NSE", "name": "Tata Motors Ltd", "segment": "EQ"},
            {"symbol": "TATASTEEL", "exchange": "NSE", "name": "Tata Steel Ltd", "segment": "EQ"},
            {"symbol": "POWERGRID", "exchange": "NSE", "name": "Power Grid Corporation of India Ltd", "segment": "EQ"},
            {"symbol": "NTPC", "exchange": "NSE", "name": "NTPC Ltd", "segment": "EQ"},
            {"symbol": "ONGC", "exchange": "NSE", "name": "Oil and Natural Gas Corporation Ltd", "segment": "EQ"},
            {"symbol": "HCLTECH", "exchange": "NSE", "name": "HCL Technologies Ltd", "segment": "EQ"},
            {"symbol": "TECHM", "exchange": "NSE", "name": "Tech Mahindra Ltd", "segment": "EQ"},
            {"symbol": "ADANIENT", "exchange": "NSE", "name": "Adani Enterprises Ltd", "segment": "EQ"},
            {"symbol": "ADANIPORTS", "exchange": "NSE", "name": "Adani Ports and SEZ Ltd", "segment": "EQ"},
            {"symbol": "COALINDIA", "exchange": "NSE", "name": "Coal India Ltd", "segment": "EQ"},
            {"symbol": "M&M", "exchange": "NSE", "name": "Mahindra & Mahindra Ltd", "segment": "EQ"},
            {"symbol": "BAJAJFINSV", "exchange": "NSE", "name": "Bajaj Finserv Ltd", "segment": "EQ"},
            {"symbol": "DRREDDY", "exchange": "NSE", "name": "Dr. Reddy's Laboratories Ltd", "segment": "EQ"},
            {"symbol": "CIPLA", "exchange": "NSE", "name": "Cipla Ltd", "segment": "EQ"},
            {"symbol": "EICHERMOT", "exchange": "NSE", "name": "Eicher Motors Ltd", "segment": "EQ"},
            {"symbol": "DIVISLAB", "exchange": "NSE", "name": "Divi's Laboratories Ltd", "segment": "EQ"},
            {"symbol": "JSWSTEEL", "exchange": "NSE", "name": "JSW Steel Ltd", "segment": "EQ"},
            {"symbol": "APOLLOHOSP", "exchange": "NSE", "name": "Apollo Hospitals Enterprise Ltd", "segment": "EQ"},
            {"symbol": "BRITANNIA", "exchange": "NSE", "name": "Britannia Industries Ltd", "segment": "EQ"},
            {"symbol": "TATACONSUM", "exchange": "NSE", "name": "Tata Consumer Products Ltd", "segment": "EQ"},
        ]

        query_lower = query.lower()
        results = []

        for sym in symbols_data:
            if query_lower in sym["symbol"].lower() or query_lower in sym["name"].lower():
                if exchange is None or sym["exchange"] == exchange:
                    results.append(sym)

        return results[:20]
