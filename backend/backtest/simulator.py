"""
Order execution simulator for backtesting.

Simulates order execution on historical data with realistic
assumptions about fill prices and slippage.
"""

from typing import Optional, Dict, List
from decimal import Decimal
from dataclasses import dataclass, field
from datetime import datetime

from strategies.base import Order, Signal, OrderType, Position


@dataclass
class Fill:
    """Represents a filled order."""
    order: Order
    fill_price: Decimal
    fill_quantity: int
    fill_time: datetime
    commission: Decimal = Decimal("0")


@dataclass
class SimulatedPosition:
    """Position tracked during simulation."""
    symbol: str
    exchange: str
    quantity: int
    avg_price: Decimal
    entry_time: datetime
    entry_order: Order

    def update_price(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized P&L at current price."""
        if self.quantity == 0:
            return Decimal("0")
        return (current_price - self.avg_price) * self.quantity

    @property
    def market_value(self) -> Decimal:
        """Calculate current market value."""
        return abs(self.quantity) * self.avg_price


@dataclass
class SimulatedContext:
    """Tracks simulation state during backtest."""
    initial_capital: Decimal
    capital: Decimal
    positions: Dict[str, SimulatedPosition] = field(default_factory=dict)
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    peak_capital: Decimal = Decimal("0")
    trades_count: int = 0

    def __post_init__(self):
        self.peak_capital = self.capital

    @property
    def total_equity(self) -> Decimal:
        """Total equity including unrealized P&L."""
        return self.capital + self.unrealized_pnl

    @property
    def available_capital(self) -> Decimal:
        """Capital available for new trades."""
        used = sum(p.market_value for p in self.positions.values())
        return self.capital - used

    def update_unrealized_pnl(self, current_prices: Dict[str, Decimal]) -> None:
        """Update unrealized P&L based on current prices."""
        total_unrealized = Decimal("0")
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                pnl = position.update_price(current_prices[symbol])
                total_unrealized += pnl
        self.unrealized_pnl = total_unrealized

        # Update peak capital
        if self.total_equity > self.peak_capital:
            self.peak_capital = self.total_equity


class OrderSimulator:
    """
    Simulates order execution on historical data.

    Supports market and limit orders with configurable slippage.
    """

    def __init__(
        self,
        slippage_percent: float = 0.05,  # 0.05% slippage
        commission_per_trade: Decimal = Decimal("0"),  # No commission by default
        allow_fractional: bool = False,
    ):
        """
        Initialize the order simulator.

        Args:
            slippage_percent: Percentage slippage to apply (0.05 = 0.05%)
            commission_per_trade: Commission per trade
            allow_fractional: Whether to allow fractional quantities
        """
        self.slippage_percent = slippage_percent
        self.commission_per_trade = commission_per_trade
        self.allow_fractional = allow_fractional

    def execute_order(
        self,
        order: Order,
        candle_open: Decimal,
        candle_high: Decimal,
        candle_low: Decimal,
        candle_close: Decimal,
        timestamp: datetime,
        context: SimulatedContext,
    ) -> Optional[Fill]:
        """
        Attempt to execute an order on the given candle.

        For backtesting, we assume:
        - Market orders fill at open price with slippage
        - Limit orders fill if price reaches the limit level
        - Stop orders fill if price reaches the stop level

        Args:
            order: The order to execute
            candle_open/high/low/close: OHLC prices
            timestamp: Candle timestamp
            context: Current simulation context

        Returns:
            Fill if order executed, None if not
        """
        fill_price = self._determine_fill_price(
            order, candle_open, candle_high, candle_low, candle_close
        )

        if fill_price is None:
            return None

        # Apply slippage
        fill_price = self._apply_slippage(fill_price, order.signal)

        # Validate order quantity
        if order.quantity <= 0:
            return None

        # Check if we have enough capital for buy orders
        if order.signal in [Signal.BUY]:
            required_capital = fill_price * order.quantity
            if required_capital > context.available_capital:
                # Reduce quantity to what we can afford
                affordable_qty = int(context.available_capital / fill_price)
                if affordable_qty <= 0:
                    return None
                order.quantity = affordable_qty

        return Fill(
            order=order,
            fill_price=fill_price,
            fill_quantity=order.quantity,
            fill_time=timestamp,
            commission=self.commission_per_trade,
        )

    def _determine_fill_price(
        self,
        order: Order,
        candle_open: Decimal,
        candle_high: Decimal,
        candle_low: Decimal,
        candle_close: Decimal,
    ) -> Optional[Decimal]:
        """Determine the fill price based on order type."""
        if order.order_type == OrderType.MARKET:
            # Market orders fill at open price
            return candle_open

        elif order.order_type == OrderType.LIMIT:
            if order.price is None:
                return None

            # Buy limit fills if price drops to limit
            if order.signal == Signal.BUY:
                if candle_low <= order.price:
                    return order.price
            # Sell limit fills if price rises to limit
            elif order.signal == Signal.SELL:
                if candle_high >= order.price:
                    return order.price

        elif order.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LOSS_MARKET]:
            if order.price is None:
                return candle_open  # Market stop loss

            # Stop loss for long position (sell if price drops)
            if order.signal in [Signal.SELL, Signal.EXIT_LONG]:
                if candle_low <= order.price:
                    return order.price
            # Stop loss for short position (buy if price rises)
            elif order.signal in [Signal.BUY, Signal.EXIT_SHORT]:
                if candle_high >= order.price:
                    return order.price

        return None

    def _apply_slippage(self, price: Decimal, signal: Signal) -> Decimal:
        """Apply slippage to fill price."""
        slippage_multiplier = Decimal(str(1 + self.slippage_percent / 100))

        if signal in [Signal.BUY, Signal.EXIT_SHORT]:
            # Buying - price moves up (adverse)
            return price * slippage_multiplier
        else:
            # Selling - price moves down (adverse)
            return price / slippage_multiplier

    def process_fill(
        self,
        fill: Fill,
        context: SimulatedContext,
    ) -> tuple[Optional[SimulatedPosition], Optional[Decimal]]:
        """
        Process a filled order and update context.

        Returns:
            Tuple of (new/updated position, realized P&L if closed)
        """
        order = fill.order
        symbol = order.symbol
        realized_pnl = None

        # Handle position opening/closing
        if order.signal == Signal.BUY:
            # Opening or adding to long position
            if symbol in context.positions:
                # Add to existing position
                pos = context.positions[symbol]
                total_cost = (pos.avg_price * pos.quantity) + (
                    fill.fill_price * fill.fill_quantity
                )
                new_qty = pos.quantity + fill.fill_quantity
                pos.avg_price = total_cost / new_qty if new_qty > 0 else Decimal("0")
                pos.quantity = new_qty
            else:
                # Open new position
                context.positions[symbol] = SimulatedPosition(
                    symbol=symbol,
                    exchange=order.exchange,
                    quantity=fill.fill_quantity,
                    avg_price=fill.fill_price,
                    entry_time=fill.fill_time,
                    entry_order=order,
                )
                context.trades_count += 1

            # Deduct capital
            context.capital -= fill.fill_price * fill.fill_quantity + fill.commission

        elif order.signal in [Signal.SELL, Signal.EXIT_LONG]:
            # Closing long position
            if symbol in context.positions:
                pos = context.positions[symbol]
                # Calculate P&L
                pnl = (fill.fill_price - pos.avg_price) * min(
                    fill.fill_quantity, pos.quantity
                )
                realized_pnl = pnl - fill.commission

                # Update position
                pos.quantity -= fill.fill_quantity
                if pos.quantity <= 0:
                    del context.positions[symbol]

                # Add capital back
                context.capital += (
                    fill.fill_price * fill.fill_quantity - fill.commission
                )
                context.realized_pnl += realized_pnl

        elif order.signal == Signal.EXIT_SHORT:
            # Would handle short covering here (not implemented in detail)
            pass

        return context.positions.get(symbol), realized_pnl

    def close_position(
        self,
        position: SimulatedPosition,
        close_price: Decimal,
        timestamp: datetime,
        context: SimulatedContext,
    ) -> Decimal:
        """
        Force close a position at the given price.

        Returns:
            Realized P&L from closing
        """
        pnl = (close_price - position.avg_price) * position.quantity

        # Update context
        context.capital += close_price * position.quantity
        context.realized_pnl += pnl

        if position.symbol in context.positions:
            del context.positions[position.symbol]

        return pnl

    def close_all_positions(
        self,
        close_prices: Dict[str, Decimal],
        timestamp: datetime,
        context: SimulatedContext,
    ) -> Decimal:
        """
        Close all open positions at given prices.

        Returns:
            Total realized P&L from closing all positions
        """
        total_pnl = Decimal("0")
        symbols_to_close = list(context.positions.keys())

        for symbol in symbols_to_close:
            if symbol in close_prices:
                position = context.positions[symbol]
                pnl = self.close_position(
                    position, close_prices[symbol], timestamp, context
                )
                total_pnl += pnl

        return total_pnl
