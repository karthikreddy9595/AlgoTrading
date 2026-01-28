"""
SMA + RSI Crossover Strategy.

Combines Simple Moving Average crossover signals with RSI confirmation
for higher-quality entry/exit signals.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from collections import deque

from strategies.base import (
    BaseStrategy,
    MarketData,
    Order,
    Signal,
    OrderType,
    StrategyContext,
    ConfigurableParam,
)


class SMARSICrossover(BaseStrategy):
    """
    SMA + RSI Crossover Strategy.

    This strategy combines two popular indicators:
    1. Simple Moving Average (SMA) crossover for trend detection
    2. Relative Strength Index (RSI) for momentum confirmation

    Entry (BUY):
    - Fast MA crosses above Slow MA (bullish crossover)
    - RSI is below overbought level (< 70)

    Exit (EXIT_LONG):
    - Fast MA crosses below Slow MA (bearish crossover), OR
    - RSI exceeds overbought level (> 70)

    Parameters:
        fast_ma_period: Period for fast moving average (default: 9)
        slow_ma_period: Period for slow moving average (default: 21)
        rsi_period: Period for RSI calculation (default: 14)
        rsi_overbought: RSI level considered overbought (default: 70)
        rsi_oversold: RSI level considered oversold (default: 30)
        risk_per_trade: Percentage of capital to risk per trade (default: 2%)
    """

    name = "SMA RSI Crossover"
    description = "Combines SMA crossover with RSI confirmation for filtered entries"
    version = "1.0.0"
    author = "Platform"
    min_capital = Decimal("10000")
    # Support both formats: with and without exchange prefix
    supported_symbols = [
        "NIFTY50-INDEX", "NSE:NIFTY50-INDEX",
        "NIFTYBANK-INDEX", "NSE:NIFTYBANK-INDEX",
        "RELIANCE", "NSE:RELIANCE",
        "TCS", "NSE:TCS",
        "INFY", "NSE:INFY",
        "HDFCBANK", "NSE:HDFCBANK",
        "SBIN", "NSE:SBIN",
        "ICICIBANK", "NSE:ICICIBANK",
    ]
    timeframe = "15min"

    @classmethod
    def get_configurable_params(cls) -> List[ConfigurableParam]:
        """Return configurable parameters for this strategy."""
        return [
            ConfigurableParam(
                name="fast_ma_period",
                display_name="Fast MA Period",
                param_type="int",
                default_value=9,
                min_value=2,
                max_value=50,
                description="Period for fast moving average"
            ),
            ConfigurableParam(
                name="slow_ma_period",
                display_name="Slow MA Period",
                param_type="int",
                default_value=21,
                min_value=5,
                max_value=200,
                description="Period for slow moving average"
            ),
            ConfigurableParam(
                name="rsi_period",
                display_name="RSI Period",
                param_type="int",
                default_value=14,
                min_value=5,
                max_value=50,
                description="Period for RSI calculation"
            ),
            ConfigurableParam(
                name="rsi_overbought",
                display_name="RSI Overbought",
                param_type="int",
                default_value=70,
                min_value=50,
                max_value=90,
                description="RSI level considered overbought"
            ),
            ConfigurableParam(
                name="rsi_oversold",
                display_name="RSI Oversold",
                param_type="int",
                default_value=30,
                min_value=10,
                max_value=50,
                description="RSI level considered oversold"
            ),
            ConfigurableParam(
                name="stop_loss_percent",
                display_name="Stop Loss %",
                param_type="float",
                default_value=2.0,
                min_value=0.5,
                max_value=10.0,
                description="Stop loss percentage per trade"
            ),
            ConfigurableParam(
                name="target_percent",
                display_name="Target %",
                param_type="float",
                default_value=4.0,
                min_value=1.0,
                max_value=20.0,
                description="Target profit percentage per trade"
            ),
        ]

    def apply_config(self, config: Dict[str, Any]) -> None:
        """Apply user configuration to strategy parameters."""
        if "fast_ma_period" in config:
            self.fast_ma_period = int(config["fast_ma_period"])
        if "slow_ma_period" in config:
            self.slow_ma_period = int(config["slow_ma_period"])
        if "rsi_period" in config:
            self.rsi_period = int(config["rsi_period"])
        if "rsi_overbought" in config:
            self.rsi_overbought = int(config["rsi_overbought"])
        if "rsi_oversold" in config:
            self.rsi_oversold = int(config["rsi_oversold"])
        if "stop_loss_percent" in config:
            self.stop_loss_percent = Decimal(str(config["stop_loss_percent"])) / 100
        if "target_percent" in config:
            self.target_percent = Decimal(str(config["target_percent"])) / 100

        # Recalculate max history based on new parameters
        self._max_history = max(self.slow_ma_period, self.rsi_period + 1) + 5

    def __init__(self, context: StrategyContext):
        super().__init__(context)

        # SMA parameters
        self.fast_ma_period = 9
        self.slow_ma_period = 21

        # RSI parameters
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30

        # Risk management
        self.risk_per_trade = Decimal("2")  # 2% risk per trade
        self.stop_loss_percent = Decimal("0.02")  # 2% stop loss
        self.target_percent = Decimal("0.04")  # 4% target

        # Price history for calculations
        # Need enough data for slow MA + RSI
        self._max_history = max(self.slow_ma_period, self.rsi_period + 1) + 5
        self._price_history: Dict[str, deque] = {}

        # Track previous MA values for crossover detection
        self._prev_fast_ma: Dict[str, Optional[Decimal]] = {}
        self._prev_slow_ma: Dict[str, Optional[Decimal]] = {}

        # Initialize state
        self._state = {
            "price_history": {},
            "prev_fast_ma": {},
            "prev_slow_ma": {},
        }

    def on_start(self) -> None:
        """Called when strategy starts running."""
        super().on_start()
        # Initialize tracking for supported symbols
        for symbol in self.supported_symbols:
            self._price_history[symbol] = deque(maxlen=self._max_history)
            self._prev_fast_ma[symbol] = None
            self._prev_slow_ma[symbol] = None

    def _calculate_sma(self, prices: List[Decimal], period: int) -> Optional[Decimal]:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def _calculate_rsi(self, prices: List[Decimal]) -> Optional[Decimal]:
        """
        Calculate Relative Strength Index.

        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        if len(prices) < self.rsi_period + 1:
            return None

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(Decimal("0"))
            else:
                gains.append(Decimal("0"))
                losses.append(abs(change))

        # Use simple average for initial RSI
        avg_gain = sum(gains[-self.rsi_period:]) / self.rsi_period
        avg_loss = sum(losses[-self.rsi_period:]) / self.rsi_period

        if avg_loss == 0:
            return Decimal("100")

        rs = avg_gain / avg_loss
        rsi = Decimal("100") - (Decimal("100") / (1 + rs))

        return rsi

    def on_market_data(self, data: MarketData) -> Optional[Order]:
        """
        Process market data and generate trading signals.

        Combines SMA crossover with RSI confirmation for entries.
        """
        symbol = data.symbol

        # Initialize if new symbol
        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=self._max_history)
            self._prev_fast_ma[symbol] = None
            self._prev_slow_ma[symbol] = None

        # Add price to history
        self._price_history[symbol].append(data.close)
        prices = list(self._price_history[symbol])

        # Need enough data for both indicators
        min_required = max(self.slow_ma_period, self.rsi_period + 1)
        if len(prices) < min_required:
            return None

        # Calculate indicators
        fast_ma = self._calculate_sma(prices, self.fast_ma_period)
        slow_ma = self._calculate_sma(prices, self.slow_ma_period)
        rsi = self._calculate_rsi(prices)

        if fast_ma is None or slow_ma is None or rsi is None:
            return None

        # Get previous MA values for crossover detection
        prev_fast = self._prev_fast_ma.get(symbol)
        prev_slow = self._prev_slow_ma.get(symbol)

        # Update previous values for next iteration
        self._prev_fast_ma[symbol] = fast_ma
        self._prev_slow_ma[symbol] = slow_ma

        # Need previous values for crossover detection
        if prev_fast is None or prev_slow is None:
            return None

        # Get current position
        position = self.context.get_position(symbol)

        # Detect crossover
        bullish_crossover = prev_fast <= prev_slow and fast_ma > slow_ma
        bearish_crossover = prev_fast >= prev_slow and fast_ma < slow_ma

        # Generate signals with combined logic
        if bullish_crossover and rsi < self.rsi_overbought and not position:
            # BUY signal: Bullish crossover + RSI not overbought + no position
            stop_loss = data.ltp * (1 - self.stop_loss_percent)
            target = data.ltp * (1 + self.target_percent)

            quantity = self.calculate_position_size(
                price=data.ltp,
                risk_percent=self.risk_per_trade,
                stop_loss=stop_loss,
            )

            if quantity > 0:
                return Order(
                    symbol=symbol,
                    exchange="NSE",
                    signal=Signal.BUY,
                    quantity=quantity,
                    order_type=OrderType.MARKET,
                    stop_loss=stop_loss,
                    target=target,
                    reason=(
                        f"Bullish crossover + RSI confirmation: "
                        f"Fast MA({float(fast_ma):.2f}) > Slow MA({float(slow_ma):.2f}), "
                        f"RSI={float(rsi):.1f}"
                    ),
                )

        elif position and position.is_long:
            # Check exit conditions for long position
            should_exit = False
            exit_reason = ""

            if bearish_crossover:
                should_exit = True
                exit_reason = (
                    f"Bearish crossover: "
                    f"Fast MA({float(fast_ma):.2f}) < Slow MA({float(slow_ma):.2f})"
                )
            elif rsi > self.rsi_overbought:
                should_exit = True
                exit_reason = f"RSI overbought: {float(rsi):.1f} > {self.rsi_overbought}"

            if should_exit:
                return Order(
                    symbol=symbol,
                    exchange="NSE",
                    signal=Signal.EXIT_LONG,
                    quantity=position.quantity,
                    order_type=OrderType.MARKET,
                    reason=exit_reason,
                )

        return None

    def get_state(self) -> Dict[str, Any]:
        """Save strategy state for persistence."""
        return {
            "price_history": {
                symbol: list(prices)
                for symbol, prices in self._price_history.items()
            },
            "prev_fast_ma": {
                k: float(v) if v is not None else None
                for k, v in self._prev_fast_ma.items()
            },
            "prev_slow_ma": {
                k: float(v) if v is not None else None
                for k, v in self._prev_slow_ma.items()
            },
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore strategy state from saved data."""
        if "price_history" in state:
            for symbol, prices in state["price_history"].items():
                self._price_history[symbol] = deque(
                    [Decimal(str(p)) for p in prices],
                    maxlen=self._max_history,
                )

        if "prev_fast_ma" in state:
            self._prev_fast_ma = {
                k: Decimal(str(v)) if v is not None else None
                for k, v in state["prev_fast_ma"].items()
            }

        if "prev_slow_ma" in state:
            self._prev_slow_ma = {
                k: Decimal(str(v)) if v is not None else None
                for k, v in state["prev_slow_ma"].items()
            }
