import asyncio
import random
from typing import List, Optional, Callable, Dict
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from brokers.base import (
    BaseBroker,
    BrokerCredentials,
    BrokerOrder,
    BrokerPosition,
    MarketQuote,
    OrderStatus,
)


class PaperTradingBroker(BaseBroker):
    """
    Paper trading broker for simulated trading.

    This broker simulates order execution without placing real orders.
    Useful for testing strategies and paper trading mode.
    """

    name = "Paper Trading"

    def __init__(self):
        super().__init__()
        self._orders: Dict[str, BrokerOrder] = {}
        self._positions: Dict[str, BrokerPosition] = {}
        self._market_data_callback: Optional[Callable] = None
        self._subscribed_symbols: List[str] = []
        self._market_data_task: Optional[asyncio.Task] = None
        self._running = False

        # Simulated market prices
        self._prices: Dict[str, Decimal] = {
            "NSE:NIFTY50-INDEX": Decimal("22500"),
            "NSE:NIFTYBANK-INDEX": Decimal("48000"),
            "NSE:RELIANCE": Decimal("2800"),
            "NSE:TCS": Decimal("3900"),
            "NSE:INFY": Decimal("1450"),
            "NSE:HDFCBANK": Decimal("1600"),
        }

        # Simulated margin
        self._available_margin = Decimal("1000000")  # 10 Lakhs
        self._used_margin = Decimal("0")

    async def connect(self, credentials: BrokerCredentials) -> bool:
        """Connect to paper trading (always succeeds)."""
        self.credentials = credentials
        self.is_connected = True
        self._running = True
        return True

    async def disconnect(self) -> None:
        """Disconnect from paper trading."""
        self._running = False
        if self._market_data_task:
            self._market_data_task.cancel()
            try:
                await self._market_data_task
            except asyncio.CancelledError:
                pass
        self.is_connected = False

    async def get_profile(self) -> dict:
        """Get simulated user profile."""
        return {
            "name": "Paper Trading User",
            "email": "paper@trading.local",
            "broker": "Paper Trading",
            "client_id": "PAPER001",
        }

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
        """Place a simulated order."""
        order_id = str(uuid4())
        full_symbol = f"{exchange}:{symbol}"

        # Get current price
        current_price = self._prices.get(full_symbol, Decimal("1000"))

        # Simulate fill price with small slippage
        slippage = Decimal(str(random.uniform(-0.001, 0.001)))
        fill_price = current_price * (1 + slippage)
        fill_price = fill_price.quantize(Decimal("0.05"))

        # Determine fill price based on order type
        if order_type == "MARKET":
            final_price = fill_price
            status = OrderStatus.FILLED
            filled_qty = quantity
        elif order_type == "LIMIT":
            if price:
                if (transaction_type == "BUY" and price >= current_price) or \
                   (transaction_type == "SELL" and price <= current_price):
                    final_price = price
                    status = OrderStatus.FILLED
                    filled_qty = quantity
                else:
                    final_price = None
                    status = OrderStatus.OPEN
                    filled_qty = 0
            else:
                final_price = None
                status = OrderStatus.REJECTED
                filled_qty = 0
        else:
            final_price = fill_price
            status = OrderStatus.FILLED
            filled_qty = quantity

        order = BrokerOrder(
            order_id=order_id,
            broker_order_id=f"PAPER_{order_id[:8]}",
            symbol=symbol,
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            price=price,
            trigger_price=trigger_price,
            status=status,
            filled_quantity=filled_qty,
            filled_price=final_price,
            message="Order placed successfully" if status != OrderStatus.REJECTED else "Order rejected",
            placed_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self._orders[order_id] = order

        # Update positions if filled
        if status == OrderStatus.FILLED and final_price:
            await self._update_position(full_symbol, exchange, transaction_type, filled_qty, final_price)

        return order

    async def _update_position(
        self,
        symbol: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        price: Decimal,
    ):
        """Update position after order fill."""
        if symbol in self._positions:
            position = self._positions[symbol]

            if transaction_type == "BUY":
                # Add to long position
                new_qty = position.quantity + quantity
                if new_qty == 0:
                    del self._positions[symbol]
                else:
                    total_value = (position.avg_price * position.quantity) + (price * quantity)
                    position.avg_price = total_value / abs(new_qty) if new_qty != 0 else Decimal("0")
                    position.quantity = new_qty
                    position.ltp = price
                    position.pnl = (price - position.avg_price) * new_qty
            else:
                # Reduce position
                new_qty = position.quantity - quantity
                if new_qty == 0:
                    del self._positions[symbol]
                else:
                    position.quantity = new_qty
                    position.ltp = price
                    position.pnl = (price - position.avg_price) * new_qty
        else:
            # New position
            qty = quantity if transaction_type == "BUY" else -quantity
            self._positions[symbol] = BrokerPosition(
                symbol=symbol.split(":")[-1],
                exchange=exchange,
                quantity=qty,
                avg_price=price,
                ltp=price,
                pnl=Decimal("0"),
                product_type="INTRADAY",
            )

    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[Decimal] = None,
        trigger_price: Optional[Decimal] = None,
    ) -> BrokerOrder:
        """Modify an existing order."""
        if order_id not in self._orders:
            raise ValueError(f"Order {order_id} not found")

        order = self._orders[order_id]

        if order.status != OrderStatus.OPEN:
            raise ValueError(f"Cannot modify order in status {order.status}")

        if quantity:
            order.quantity = quantity
        if price:
            order.price = price
        if trigger_price:
            order.trigger_price = trigger_price

        order.updated_at = datetime.utcnow()
        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if order_id not in self._orders:
            return False

        order = self._orders[order_id]
        if order.status != OrderStatus.OPEN:
            return False

        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        return True

    async def get_order_status(self, order_id: str) -> BrokerOrder:
        """Get order status."""
        if order_id not in self._orders:
            raise ValueError(f"Order {order_id} not found")
        return self._orders[order_id]

    async def get_orders(self) -> List[BrokerOrder]:
        """Get all orders."""
        return list(self._orders.values())

    async def get_positions(self) -> List[BrokerPosition]:
        """Get current positions."""
        return list(self._positions.values())

    async def get_quote(self, symbol: str, exchange: str) -> MarketQuote:
        """Get current market quote."""
        full_symbol = f"{exchange}:{symbol}"
        base_price = self._prices.get(full_symbol, Decimal("1000"))

        # Simulate price movement
        change = Decimal(str(random.uniform(-0.005, 0.005)))
        current_price = base_price * (1 + change)
        current_price = current_price.quantize(Decimal("0.05"))

        # Update stored price
        self._prices[full_symbol] = current_price

        spread = current_price * Decimal("0.0005")

        return MarketQuote(
            symbol=symbol,
            exchange=exchange,
            ltp=current_price,
            open=base_price,
            high=current_price * Decimal("1.01"),
            low=current_price * Decimal("0.99"),
            close=base_price,
            volume=random.randint(100000, 1000000),
            bid=current_price - spread,
            ask=current_price + spread,
            bid_qty=random.randint(100, 1000),
            ask_qty=random.randint(100, 1000),
            timestamp=datetime.utcnow(),
        )

    async def subscribe_market_data(
        self,
        symbols: List[str],
        callback: Callable[[MarketQuote], None],
    ) -> None:
        """Subscribe to simulated market data."""
        self._subscribed_symbols.extend(symbols)
        self._market_data_callback = callback

        # Start market data simulation if not running
        if not self._market_data_task or self._market_data_task.done():
            self._market_data_task = asyncio.create_task(self._simulate_market_data())

    async def _simulate_market_data(self):
        """Simulate real-time market data."""
        while self._running and self._subscribed_symbols:
            for full_symbol in self._subscribed_symbols:
                if ":" in full_symbol:
                    exchange, symbol = full_symbol.split(":", 1)
                else:
                    exchange = "NSE"
                    symbol = full_symbol

                try:
                    quote = await self.get_quote(symbol, exchange)
                    if self._market_data_callback:
                        self._market_data_callback(quote)
                except Exception as e:
                    print(f"Error simulating market data for {full_symbol}: {e}")

            await asyncio.sleep(1)  # 1 second tick interval

    async def unsubscribe_market_data(self, symbols: List[str]) -> None:
        """Unsubscribe from market data."""
        for symbol in symbols:
            if symbol in self._subscribed_symbols:
                self._subscribed_symbols.remove(symbol)

    async def get_margin(self) -> dict:
        """Get simulated margin."""
        return {
            "available": float(self._available_margin - self._used_margin),
            "used": float(self._used_margin),
            "total": float(self._available_margin),
        }

    def reset(self):
        """Reset paper trading state."""
        self._orders.clear()
        self._positions.clear()
        self._available_margin = Decimal("1000000")
        self._used_margin = Decimal("0")
