"""
Backtest engine for running trading strategies on historical data.

This engine:
1. Loads historical data from the broker API
2. Instantiates the strategy with a simulated context
3. Iterates through historical data chronologically
4. Calls strategy.on_market_data() for each candle
5. Simulates order execution
6. Tracks positions, capital, and P&L
7. Calculates performance metrics
"""

from typing import List, Optional, Callable, Dict, Any
from decimal import Decimal
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
import importlib
import asyncio

from strategies.base import BaseStrategy, MarketData, StrategyContext, Order, Signal, Position
from backtest.metrics import MetricsCalculator, TradeResult, PerformanceMetrics
from backtest.simulator import OrderSimulator, SimulatedContext, SimulatedPosition


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""
    strategy_module_path: str
    strategy_class_name: str
    symbol: str
    exchange: str
    interval: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    strategy_config: Dict[str, Any] = field(default_factory=dict)
    slippage_percent: float = 0.05
    commission: Decimal = Decimal("0")


@dataclass
class BacktestResult:
    """Complete result of a backtest run."""
    config: BacktestConfig
    metrics: PerformanceMetrics
    trades: List[TradeResult]
    equity_curve: List[tuple[datetime, Decimal]]  # (timestamp, equity)
    candles: List[Dict[str, Any]]  # OHLC data for charting
    error: Optional[str] = None


ProgressCallback = Callable[[int, str], None]


class BacktestEngine:
    """
    Main backtest execution engine.

    Runs a trading strategy on historical data and calculates
    performance metrics.
    """

    def __init__(
        self,
        slippage_percent: float = 0.05,
        commission: Decimal = Decimal("0"),
    ):
        """
        Initialize the backtest engine.

        Args:
            slippage_percent: Slippage to apply to fills
            commission: Commission per trade
        """
        self.slippage_percent = slippage_percent
        self.commission = commission
        self.simulator = OrderSimulator(
            slippage_percent=slippage_percent,
            commission_per_trade=commission,
        )

    async def run(
        self,
        config: BacktestConfig,
        historical_data: List[Dict[str, Any]],
        on_progress: Optional[ProgressCallback] = None,
    ) -> BacktestResult:
        """
        Run backtest with provided historical data.

        Args:
            config: Backtest configuration
            historical_data: List of OHLC candles from broker API
            on_progress: Optional callback for progress updates

        Returns:
            BacktestResult with metrics, trades, and equity curve
        """
        try:
            # Load strategy class
            strategy_class = self._load_strategy_class(
                config.strategy_module_path, config.strategy_class_name
            )

            # Create simulated context
            sim_context = SimulatedContext(
                initial_capital=config.initial_capital,
                capital=config.initial_capital,
            )

            # Create strategy context
            strategy_context = self._create_strategy_context(config, sim_context)

            # Instantiate strategy
            strategy = strategy_class(strategy_context)
            # Apply user configuration if provided
            if config.strategy_config:
                strategy.apply_config(config.strategy_config)
            strategy.on_start()

            # Track trades and equity curve
            completed_trades: List[TradeResult] = []
            equity_curve: List[tuple[datetime, Decimal]] = []
            open_trades: Dict[str, Dict[str, Any]] = {}  # symbol -> trade info

            total_candles = len(historical_data)

            # Process each candle
            for i, candle in enumerate(historical_data):
                # Report progress
                if on_progress:
                    progress = int((i + 1) / total_candles * 100)
                    await self._report_progress(
                        on_progress,
                        progress,
                        f"Processing {candle.get('timestamp', '')}",
                    )

                # Create MarketData from candle (include exchange in symbol for strategy matching)
                full_symbol = f"{config.exchange}:{config.symbol}" if config.exchange else config.symbol
                market_data = self._candle_to_market_data(candle, full_symbol)

                # Update unrealized P&L
                sim_context.update_unrealized_pnl({config.symbol: market_data.close})

                # Record equity point
                equity_curve.append((market_data.timestamp, sim_context.total_equity))

                # Update strategy context with current state
                self._sync_context(strategy_context, sim_context, market_data)

                # Get order from strategy
                order = strategy.on_market_data(market_data)

                # Execute order if any
                if order:
                    fill = self.simulator.execute_order(
                        order=order,
                        candle_open=market_data.open,
                        candle_high=market_data.high,
                        candle_low=market_data.low,
                        candle_close=market_data.close,
                        timestamp=market_data.timestamp,
                        context=sim_context,
                    )

                    if fill:
                        # Process the fill
                        position, realized_pnl = self.simulator.process_fill(
                            fill, sim_context
                        )

                        # Notify strategy
                        strategy.on_order_filled(
                            fill.order, fill.fill_price, fill.fill_quantity
                        )

                        # Track trades
                        if order.signal == Signal.BUY:
                            # Opening trade
                            open_trades[order.symbol] = {
                                "entry_price": fill.fill_price,
                                "quantity": fill.fill_quantity,
                                "entry_time": fill.fill_time,
                                "reason": order.reason,
                            }
                        elif order.signal in [Signal.SELL, Signal.EXIT_LONG] and realized_pnl is not None:
                            # Closing trade
                            if order.symbol in open_trades:
                                trade_info = open_trades.pop(order.symbol)
                                pnl_percent = (
                                    (fill.fill_price - trade_info["entry_price"])
                                    / trade_info["entry_price"]
                                    * 100
                                )
                                completed_trades.append(
                                    TradeResult(
                                        entry_price=trade_info["entry_price"],
                                        exit_price=fill.fill_price,
                                        quantity=trade_info["quantity"],
                                        entry_time=trade_info["entry_time"],
                                        exit_time=fill.fill_time,
                                        pnl=realized_pnl,
                                        pnl_percent=Decimal(str(round(pnl_percent, 4))),
                                        is_winner=realized_pnl > 0,
                                    )
                                )

                # Allow async tasks to run
                await asyncio.sleep(0)

            # Close any remaining positions at end
            final_candle = historical_data[-1] if historical_data else None
            if final_candle:
                final_price = Decimal(str(final_candle.get("close", 0)))
                final_time = self._parse_timestamp(final_candle.get("timestamp"))

                for symbol, trade_info in list(open_trades.items()):
                    if symbol in sim_context.positions:
                        position = sim_context.positions[symbol]
                        pnl = self.simulator.close_position(
                            position, final_price, final_time, sim_context
                        )

                        pnl_percent = (
                            (final_price - trade_info["entry_price"])
                            / trade_info["entry_price"]
                            * 100
                        )
                        completed_trades.append(
                            TradeResult(
                                entry_price=trade_info["entry_price"],
                                exit_price=final_price,
                                quantity=trade_info["quantity"],
                                entry_time=trade_info["entry_time"],
                                exit_time=final_time,
                                pnl=pnl,
                                pnl_percent=Decimal(str(round(pnl_percent, 4))),
                                is_winner=pnl > 0,
                            )
                        )

            # Stop strategy
            strategy.on_stop()

            # Calculate metrics
            metrics_calculator = MetricsCalculator(config.initial_capital)
            metrics = metrics_calculator.calculate_all(
                trades=completed_trades,
                equity_curve=[eq for _, eq in equity_curve],
                start_date=datetime.combine(config.start_date, datetime.min.time()),
                end_date=datetime.combine(config.end_date, datetime.min.time()),
            )

            if on_progress:
                await self._report_progress(on_progress, 100, "Backtest completed")

            return BacktestResult(
                config=config,
                metrics=metrics,
                trades=completed_trades,
                equity_curve=equity_curve,
                candles=historical_data,
            )

        except Exception as e:
            return BacktestResult(
                config=config,
                metrics=None,
                trades=[],
                equity_curve=[],
                candles=historical_data,
                error=str(e),
            )

    def _load_strategy_class(self, module_path: str, class_name: str) -> type:
        """Dynamically load a strategy class."""
        module = importlib.import_module(module_path)
        strategy_class = getattr(module, class_name)

        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"{class_name} is not a valid strategy class")

        return strategy_class

    def _create_strategy_context(
        self, config: BacktestConfig, sim_context: SimulatedContext
    ) -> StrategyContext:
        """Create a StrategyContext for the strategy."""
        return StrategyContext(
            strategy_id="backtest",
            user_id="backtest",
            subscription_id="backtest",
            capital=config.initial_capital,
            max_positions=10,  # Default max positions
            max_drawdown_percent=Decimal("20"),  # Default max drawdown
            daily_loss_limit=config.initial_capital * Decimal("0.05"),  # 5% daily limit
            per_trade_sl_percent=Decimal("2"),  # Default 2% stop loss
            is_paper_trading=True,
            positions=[],
        )

    def _sync_context(
        self,
        strategy_context: StrategyContext,
        sim_context: SimulatedContext,
        market_data: MarketData,
    ) -> None:
        """Sync strategy context with simulation state."""
        # Update positions
        strategy_context.positions = [
            Position(
                symbol=pos.symbol,
                exchange=pos.exchange,
                quantity=pos.quantity,
                avg_price=pos.avg_price,
                current_price=market_data.close,
                pnl=pos.update_price(market_data.close),
            )
            for pos in sim_context.positions.values()
        ]

        # Update P&L
        strategy_context.realized_pnl = sim_context.realized_pnl
        strategy_context.unrealized_pnl = sim_context.unrealized_pnl
        strategy_context.total_pnl = (
            sim_context.realized_pnl + sim_context.unrealized_pnl
        )

    def _candle_to_market_data(self, candle: Dict[str, Any], symbol: str) -> MarketData:
        """Convert OHLC candle dict to MarketData object."""
        timestamp = self._parse_timestamp(candle.get("timestamp"))

        return MarketData(
            symbol=symbol,
            ltp=Decimal(str(candle.get("close", 0))),
            open=Decimal(str(candle.get("open", 0))),
            high=Decimal(str(candle.get("high", 0))),
            low=Decimal(str(candle.get("low", 0))),
            close=Decimal(str(candle.get("close", 0))),
            volume=int(candle.get("volume", 0)),
            timestamp=timestamp,
            bid=Decimal(str(candle.get("close", 0))),  # Use close as bid for backtest
            ask=Decimal(str(candle.get("close", 0))),  # Use close as ask for backtest
        )

    def _parse_timestamp(self, ts: Any) -> datetime:
        """Parse timestamp from various formats."""
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            # Try common formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(ts, fmt)
                except ValueError:
                    continue
        return datetime.now()

    async def _report_progress(
        self, callback: ProgressCallback, progress: int, message: str
    ) -> None:
        """Report progress via callback."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(progress, message)
            else:
                callback(progress, message)
        except Exception:
            pass  # Ignore progress reporting errors
