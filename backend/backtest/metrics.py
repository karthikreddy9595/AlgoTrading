"""
Performance metrics calculator for backtesting.

Implements standard quantitative finance metrics for evaluating
trading strategy performance.
"""

from typing import List, Optional
from decimal import Decimal
from dataclasses import dataclass
import math
from datetime import datetime, timedelta


@dataclass
class TradeResult:
    """Result of a completed trade."""
    entry_price: Decimal
    exit_price: Decimal
    quantity: int
    entry_time: datetime
    exit_time: datetime
    pnl: Decimal
    pnl_percent: Decimal
    is_winner: bool


@dataclass
class PerformanceMetrics:
    """Complete performance metrics for a backtest."""
    # Return metrics
    total_return: Decimal
    total_return_percent: Decimal
    cagr: Decimal

    # Risk-adjusted metrics
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal

    # Drawdown metrics
    max_drawdown: Decimal
    avg_drawdown: Decimal

    # Trade statistics
    win_rate: Decimal
    profit_factor: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_duration: int  # in seconds

    # Capital metrics
    final_capital: Decimal
    max_capital: Decimal


class MetricsCalculator:
    """Calculator for backtesting performance metrics."""

    def __init__(
        self,
        initial_capital: Decimal,
        risk_free_rate: float = 0.05,  # 5% annual risk-free rate
        trading_days_per_year: int = 252,
    ):
        """
        Initialize the metrics calculator.

        Args:
            initial_capital: Starting capital
            risk_free_rate: Annual risk-free rate (default 5%)
            trading_days_per_year: Number of trading days per year
        """
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = trading_days_per_year

    def calculate_all(
        self,
        trades: List[TradeResult],
        equity_curve: List[Decimal],
        start_date: datetime,
        end_date: datetime,
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics.

        Args:
            trades: List of completed trades
            equity_curve: List of equity values over time
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            Complete performance metrics
        """
        final_capital = equity_curve[-1] if equity_curve else self.initial_capital
        max_capital = max(equity_curve) if equity_curve else self.initial_capital

        # Calculate returns
        total_return = final_capital - self.initial_capital
        total_return_percent = self._calculate_return_percent(
            self.initial_capital, final_capital
        )

        # Calculate time-based metrics
        years = self._calculate_years(start_date, end_date)
        cagr = self._calculate_cagr(self.initial_capital, final_capital, years)

        # Calculate daily returns for Sharpe/Sortino
        daily_returns = self._calculate_daily_returns(equity_curve)

        # Risk-adjusted metrics
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
        sortino_ratio = self._calculate_sortino_ratio(daily_returns)

        # Drawdown metrics
        max_drawdown, avg_drawdown = self._calculate_drawdowns(equity_curve)
        calmar_ratio = self._calculate_calmar_ratio(cagr, max_drawdown)

        # Trade statistics
        winning_trades = [t for t in trades if t.is_winner]
        losing_trades = [t for t in trades if not t.is_winner]

        win_rate = self._calculate_win_rate(trades)
        profit_factor = self._calculate_profit_factor(winning_trades, losing_trades)
        avg_trade_duration = self._calculate_avg_trade_duration(trades)

        return PerformanceMetrics(
            total_return=total_return,
            total_return_percent=total_return_percent,
            cagr=cagr,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            avg_drawdown=avg_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_trade_duration=avg_trade_duration,
            final_capital=final_capital,
            max_capital=max_capital,
        )

    def _calculate_return_percent(
        self, start_value: Decimal, end_value: Decimal
    ) -> Decimal:
        """Calculate percentage return."""
        if start_value == 0:
            return Decimal("0")
        return ((end_value - start_value) / start_value) * 100

    def _calculate_years(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate number of years between dates."""
        days = (end_date - start_date).days
        return max(days / 365.25, 0.01)  # Minimum 0.01 to avoid division by zero

    def _calculate_cagr(
        self, start_value: Decimal, end_value: Decimal, years: float
    ) -> Decimal:
        """
        Calculate Compound Annual Growth Rate.

        CAGR = (End Value / Start Value)^(1/years) - 1
        """
        if start_value <= 0 or years <= 0:
            return Decimal("0")

        ratio = float(end_value / start_value)
        if ratio <= 0:
            return Decimal("-100")

        cagr = (math.pow(ratio, 1 / years) - 1) * 100
        return Decimal(str(round(cagr, 4)))

    def _calculate_daily_returns(self, equity_curve: List[Decimal]) -> List[float]:
        """Calculate daily returns from equity curve."""
        if len(equity_curve) < 2:
            return []

        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] != 0:
                daily_return = float(
                    (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                )
                returns.append(daily_return)
        return returns

    def _calculate_sharpe_ratio(self, daily_returns: List[float]) -> Decimal:
        """
        Calculate Sharpe Ratio.

        Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
        Annualized by multiplying by sqrt(252)
        """
        if len(daily_returns) < 2:
            return Decimal("0")

        mean_return = sum(daily_returns) / len(daily_returns)
        daily_rf = self.risk_free_rate / self.trading_days_per_year

        # Calculate standard deviation
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / (
            len(daily_returns) - 1
        )
        std_dev = math.sqrt(variance) if variance > 0 else 0

        if std_dev == 0:
            return Decimal("0")

        sharpe = ((mean_return - daily_rf) / std_dev) * math.sqrt(
            self.trading_days_per_year
        )
        return Decimal(str(round(sharpe, 4)))

    def _calculate_sortino_ratio(self, daily_returns: List[float]) -> Decimal:
        """
        Calculate Sortino Ratio.

        Similar to Sharpe but only considers downside deviation.
        Sortino = (Mean Return - Risk Free Rate) / Downside Deviation
        """
        if len(daily_returns) < 2:
            return Decimal("0")

        mean_return = sum(daily_returns) / len(daily_returns)
        daily_rf = self.risk_free_rate / self.trading_days_per_year

        # Calculate downside deviation (only negative returns)
        negative_returns = [r for r in daily_returns if r < 0]
        if not negative_returns:
            return Decimal("0") if mean_return <= daily_rf else Decimal("999")

        downside_variance = sum(r**2 for r in negative_returns) / len(
            negative_returns
        )
        downside_dev = math.sqrt(downside_variance)

        if downside_dev == 0:
            return Decimal("0")

        sortino = ((mean_return - daily_rf) / downside_dev) * math.sqrt(
            self.trading_days_per_year
        )
        return Decimal(str(round(sortino, 4)))

    def _calculate_drawdowns(
        self, equity_curve: List[Decimal]
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate maximum and average drawdown.

        Drawdown = (Peak - Current) / Peak * 100
        """
        if not equity_curve:
            return Decimal("0"), Decimal("0")

        peak = equity_curve[0]
        drawdowns = []

        for equity in equity_curve:
            if equity > peak:
                peak = equity
            if peak > 0:
                drawdown = float((peak - equity) / peak * 100)
                drawdowns.append(drawdown)

        max_dd = max(drawdowns) if drawdowns else 0
        avg_dd = sum(drawdowns) / len(drawdowns) if drawdowns else 0

        return Decimal(str(round(max_dd, 4))), Decimal(str(round(avg_dd, 4)))

    def _calculate_calmar_ratio(
        self, cagr: Decimal, max_drawdown: Decimal
    ) -> Decimal:
        """
        Calculate Calmar Ratio.

        Calmar = CAGR / Max Drawdown
        """
        if max_drawdown == 0:
            return Decimal("0")
        return Decimal(str(round(float(cagr / max_drawdown), 4)))

    def _calculate_win_rate(self, trades: List[TradeResult]) -> Decimal:
        """Calculate win rate (percentage of winning trades)."""
        if not trades:
            return Decimal("0")

        winners = sum(1 for t in trades if t.is_winner)
        return Decimal(str(round(winners / len(trades) * 100, 4)))

    def _calculate_profit_factor(
        self,
        winning_trades: List[TradeResult],
        losing_trades: List[TradeResult],
    ) -> Decimal:
        """
        Calculate Profit Factor.

        Profit Factor = Gross Profit / Gross Loss
        """
        gross_profit = sum(float(t.pnl) for t in winning_trades)
        gross_loss = abs(sum(float(t.pnl) for t in losing_trades))

        if gross_loss == 0:
            return Decimal("999") if gross_profit > 0 else Decimal("0")

        return Decimal(str(round(gross_profit / gross_loss, 4)))

    def _calculate_avg_trade_duration(self, trades: List[TradeResult]) -> int:
        """Calculate average trade duration in seconds."""
        if not trades:
            return 0

        total_duration = sum(
            (t.exit_time - t.entry_time).total_seconds() for t in trades
        )
        return int(total_duration / len(trades))

    def calculate_equity_drawdown(
        self, equity: Decimal, peak: Decimal
    ) -> Decimal:
        """Calculate current drawdown from peak."""
        if peak <= 0:
            return Decimal("0")
        return ((peak - equity) / peak) * 100
