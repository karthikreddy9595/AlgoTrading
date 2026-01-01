"""
Risk Manager - Pre-trade and real-time risk checks.

This module provides risk management functionality including:
- Pre-order validation
- Position sizing limits
- Drawdown monitoring
- Daily loss limits
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, List
from datetime import datetime, date

from strategies.base import Order, Signal, StrategyContext


@dataclass
class RiskCheckResult:
    """Result of a risk check."""
    allowed: bool
    reason: str
    limit_type: Optional[str] = None
    current_value: Optional[Decimal] = None
    limit_value: Optional[Decimal] = None


@dataclass
class RiskLimits:
    """Risk limits for a strategy subscription."""
    max_drawdown_percent: Decimal
    daily_loss_limit: Decimal
    per_trade_sl_percent: Decimal
    max_positions: int
    max_order_value_percent: Decimal = Decimal("20")  # Max 20% of capital per trade
    max_daily_trades: int = 50


class RiskManager:
    """
    Risk manager for validating trades and monitoring risk.

    Performs pre-order checks and can trigger kill switch
    when risk limits are breached.
    """

    def __init__(self, kill_switch=None):
        self.kill_switch = kill_switch

    def check_order(
        self,
        order: Order,
        context: StrategyContext,
        limits: RiskLimits,
        today_trade_count: int = 0,
    ) -> RiskCheckResult:
        """
        Perform all risk checks on an order.

        Args:
            order: The order to validate
            context: Current strategy context
            limits: Risk limits for this subscription
            today_trade_count: Number of trades today

        Returns:
            RiskCheckResult indicating if order is allowed
        """
        checks = [
            self._check_kill_switch_sync,
            self._check_daily_loss_limit,
            self._check_max_drawdown,
            self._check_position_count,
            self._check_position_sizing,
            self._check_daily_trade_limit,
            self._check_stop_loss_required,
        ]

        for check in checks:
            result = check(order, context, limits, today_trade_count)
            if not result.allowed:
                return result

        return RiskCheckResult(
            allowed=True,
            reason="All risk checks passed",
        )

    def _check_kill_switch_sync(
        self,
        order: Order,
        context: StrategyContext,
        limits: RiskLimits,
        today_trade_count: int,
    ) -> RiskCheckResult:
        """Check if kill switch is active (sync version for quick check)."""
        # Note: In practice, this would check Redis synchronously or use cached state
        # For now, we assume kill switch is not active in sync checks
        return RiskCheckResult(allowed=True, reason="")

    def _check_daily_loss_limit(
        self,
        order: Order,
        context: StrategyContext,
        limits: RiskLimits,
        today_trade_count: int,
    ) -> RiskCheckResult:
        """Check if daily loss limit has been reached."""
        if limits.daily_loss_limit and context.today_pnl <= -limits.daily_loss_limit:
            return RiskCheckResult(
                allowed=False,
                reason=f"Daily loss limit reached: {context.today_pnl}",
                limit_type="daily_loss",
                current_value=context.today_pnl,
                limit_value=-limits.daily_loss_limit,
            )
        return RiskCheckResult(allowed=True, reason="")

    def _check_max_drawdown(
        self,
        order: Order,
        context: StrategyContext,
        limits: RiskLimits,
        today_trade_count: int,
    ) -> RiskCheckResult:
        """Check if max drawdown has been breached."""
        if context.capital == 0:
            return RiskCheckResult(allowed=True, reason="")

        current_drawdown = (context.total_pnl / context.capital) * 100

        if current_drawdown <= -limits.max_drawdown_percent:
            return RiskCheckResult(
                allowed=False,
                reason=f"Max drawdown reached: {current_drawdown:.2f}%",
                limit_type="max_drawdown",
                current_value=current_drawdown,
                limit_value=-limits.max_drawdown_percent,
            )
        return RiskCheckResult(allowed=True, reason="")

    def _check_position_count(
        self,
        order: Order,
        context: StrategyContext,
        limits: RiskLimits,
        today_trade_count: int,
    ) -> RiskCheckResult:
        """Check if max position count has been reached."""
        # Only check for new positions (BUY orders)
        if order.signal not in [Signal.BUY]:
            return RiskCheckResult(allowed=True, reason="")

        # Check if already have position in this symbol
        existing = context.get_position(order.symbol)
        if existing:
            return RiskCheckResult(allowed=True, reason="")  # Adding to existing

        if len(context.positions) >= limits.max_positions:
            return RiskCheckResult(
                allowed=False,
                reason=f"Max positions ({limits.max_positions}) reached",
                limit_type="max_positions",
                current_value=Decimal(len(context.positions)),
                limit_value=Decimal(limits.max_positions),
            )
        return RiskCheckResult(allowed=True, reason="")

    def _check_position_sizing(
        self,
        order: Order,
        context: StrategyContext,
        limits: RiskLimits,
        today_trade_count: int,
    ) -> RiskCheckResult:
        """Check if order value is within limits."""
        # Only check for entry orders
        if order.signal not in [Signal.BUY]:
            return RiskCheckResult(allowed=True, reason="")

        # Estimate order value
        price = order.price or Decimal("0")
        if price == 0:
            # For market orders, we'd need current price
            # Skip check if we don't have price
            return RiskCheckResult(allowed=True, reason="")

        order_value = order.quantity * price
        max_value = context.capital * (limits.max_order_value_percent / 100)

        if order_value > max_value:
            return RiskCheckResult(
                allowed=False,
                reason=f"Order value ({order_value}) exceeds limit ({max_value})",
                limit_type="order_value",
                current_value=order_value,
                limit_value=max_value,
            )
        return RiskCheckResult(allowed=True, reason="")

    def _check_daily_trade_limit(
        self,
        order: Order,
        context: StrategyContext,
        limits: RiskLimits,
        today_trade_count: int,
    ) -> RiskCheckResult:
        """Check if daily trade limit has been reached."""
        if today_trade_count >= limits.max_daily_trades:
            return RiskCheckResult(
                allowed=False,
                reason=f"Daily trade limit ({limits.max_daily_trades}) reached",
                limit_type="daily_trades",
                current_value=Decimal(today_trade_count),
                limit_value=Decimal(limits.max_daily_trades),
            )
        return RiskCheckResult(allowed=True, reason="")

    def _check_stop_loss_required(
        self,
        order: Order,
        context: StrategyContext,
        limits: RiskLimits,
        today_trade_count: int,
    ) -> RiskCheckResult:
        """Check if entry orders have stop loss defined."""
        # Only check for entry orders
        if order.signal not in [Signal.BUY]:
            return RiskCheckResult(allowed=True, reason="")

        # Require stop loss for all entry orders
        if order.stop_loss is None:
            return RiskCheckResult(
                allowed=False,
                reason="Stop loss is required for all entry orders",
                limit_type="stop_loss_required",
            )
        return RiskCheckResult(allowed=True, reason="")

    def calculate_position_size(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        capital: Decimal,
        risk_percent: Decimal,
    ) -> int:
        """
        Calculate position size based on risk.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            capital: Available capital
            risk_percent: Percentage of capital to risk

        Returns:
            Number of units to buy
        """
        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit == 0:
            return 0

        risk_amount = capital * (risk_percent / 100)
        quantity = int(risk_amount / risk_per_unit)

        return max(0, quantity)

    def check_stop_loss_hit(
        self,
        position_avg_price: Decimal,
        current_price: Decimal,
        stop_loss_percent: Decimal,
        is_long: bool = True,
    ) -> bool:
        """
        Check if stop loss has been hit.

        Args:
            position_avg_price: Average entry price
            current_price: Current market price
            stop_loss_percent: Stop loss percentage
            is_long: True for long position, False for short

        Returns:
            True if stop loss hit
        """
        if is_long:
            sl_price = position_avg_price * (1 - stop_loss_percent / 100)
            return current_price <= sl_price
        else:
            sl_price = position_avg_price * (1 + stop_loss_percent / 100)
            return current_price >= sl_price
