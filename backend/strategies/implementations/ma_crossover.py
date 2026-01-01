from typing import Optional, List
from decimal import Decimal
from collections import deque

from strategies.base import (
    BaseStrategy,
    MarketData,
    Order,
    Signal,
    OrderType,
    StrategyContext,
)


class SimpleMovingAverageCrossover(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy.

    This strategy generates buy signals when the fast MA crosses above the slow MA,
    and sell signals when the fast MA crosses below the slow MA.

    Parameters:
        fast_period: Period for the fast moving average (default: 9)
        slow_period: Period for the slow moving average (default: 21)
        risk_per_trade: Percentage of capital to risk per trade (default: 2%)
    """

    name = "Simple MA Crossover"
    description = "Buys when fast MA crosses above slow MA, sells on cross below"
    version = "1.0.0"
    author = "Platform"
    min_capital = Decimal("10000")
    supported_symbols = ["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX", "NSE:RELIANCE", "NSE:TCS"]
    timeframe = "5min"

    def __init__(self, context: StrategyContext):
        super().__init__(context)

        # Strategy parameters
        self.fast_period = 9
        self.slow_period = 21
        self.risk_per_trade = Decimal("2")  # 2% risk per trade

        # Price history for each symbol
        self._price_history: dict[str, deque] = {}

        # Track previous MA values for crossover detection
        self._prev_fast_ma: dict[str, Optional[Decimal]] = {}
        self._prev_slow_ma: dict[str, Optional[Decimal]] = {}

        # Initialize state
        self._state = {
            "price_history": {},
            "prev_fast_ma": {},
            "prev_slow_ma": {},
        }

    def on_start(self) -> None:
        super().on_start()
        # Initialize price history for supported symbols
        for symbol in self.supported_symbols:
            self._price_history[symbol] = deque(maxlen=self.slow_period)
            self._prev_fast_ma[symbol] = None
            self._prev_slow_ma[symbol] = None

    def on_market_data(self, data: MarketData) -> Optional[Order]:
        """
        Process market data and generate trading signals.
        """
        symbol = data.symbol

        # Initialize if new symbol
        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=self.slow_period)
            self._prev_fast_ma[symbol] = None
            self._prev_slow_ma[symbol] = None

        # Add price to history
        self._price_history[symbol].append(data.close)

        # Need enough data for slow MA
        if len(self._price_history[symbol]) < self.slow_period:
            return None

        # Calculate moving averages
        prices = list(self._price_history[symbol])
        fast_ma = sum(prices[-self.fast_period:]) / self.fast_period
        slow_ma = sum(prices) / len(prices)

        # Get previous MA values
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

        # Generate signals
        if bullish_crossover and not position:
            # Buy signal - no existing position
            stop_loss = data.ltp * Decimal("0.98")  # 2% stop loss
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
                    target=data.ltp * Decimal("1.04"),  # 4% target
                    reason=f"Bullish MA crossover: Fast({fast_ma:.2f}) > Slow({slow_ma:.2f})",
                )

        elif bearish_crossover and position and position.is_long:
            # Exit long position
            return Order(
                symbol=symbol,
                exchange="NSE",
                signal=Signal.EXIT_LONG,
                quantity=position.quantity,
                order_type=OrderType.MARKET,
                reason=f"Bearish MA crossover: Fast({fast_ma:.2f}) < Slow({slow_ma:.2f})",
            )

        return None

    def get_state(self) -> dict:
        """Save strategy state for persistence."""
        return {
            "price_history": {
                symbol: list(prices)
                for symbol, prices in self._price_history.items()
            },
            "prev_fast_ma": dict(self._prev_fast_ma),
            "prev_slow_ma": dict(self._prev_slow_ma),
        }

    def set_state(self, state: dict) -> None:
        """Restore strategy state."""
        if "price_history" in state:
            for symbol, prices in state["price_history"].items():
                self._price_history[symbol] = deque(prices, maxlen=self.slow_period)

        if "prev_fast_ma" in state:
            self._prev_fast_ma = state["prev_fast_ma"]

        if "prev_slow_ma" in state:
            self._prev_slow_ma = state["prev_slow_ma"]


class RSIMomentum(BaseStrategy):
    """
    RSI Momentum Strategy.

    This strategy uses the Relative Strength Index (RSI) to identify
    overbought and oversold conditions.

    Buy when RSI < 30 (oversold)
    Sell when RSI > 70 (overbought)
    """

    name = "RSI Momentum"
    description = "Trades based on RSI oversold/overbought conditions"
    version = "1.0.0"
    author = "Platform"
    min_capital = Decimal("10000")
    supported_symbols = ["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX"]
    timeframe = "15min"

    def __init__(self, context: StrategyContext):
        super().__init__(context)

        # RSI parameters
        self.rsi_period = 14
        self.oversold_level = 30
        self.overbought_level = 70

        # Price history
        self._price_history: dict[str, deque] = {}

    def _calculate_rsi(self, prices: List[Decimal]) -> Optional[Decimal]:
        """Calculate RSI from price list."""
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

        avg_gain = sum(gains[-self.rsi_period:]) / self.rsi_period
        avg_loss = sum(losses[-self.rsi_period:]) / self.rsi_period

        if avg_loss == 0:
            return Decimal("100")

        rs = avg_gain / avg_loss
        rsi = Decimal("100") - (Decimal("100") / (1 + rs))

        return rsi

    def on_market_data(self, data: MarketData) -> Optional[Order]:
        """Process market data and generate trading signals."""
        symbol = data.symbol

        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=self.rsi_period + 10)

        self._price_history[symbol].append(data.close)

        rsi = self._calculate_rsi(list(self._price_history[symbol]))
        if rsi is None:
            return None

        position = self.context.get_position(symbol)

        # Oversold - buy signal
        if rsi < self.oversold_level and not position:
            quantity = self.calculate_position_size(data.ltp)
            if quantity > 0:
                return Order(
                    symbol=symbol,
                    exchange="NSE",
                    signal=Signal.BUY,
                    quantity=quantity,
                    order_type=OrderType.MARKET,
                    stop_loss=data.ltp * Decimal("0.97"),
                    reason=f"RSI oversold: {rsi:.2f}",
                )

        # Overbought - exit signal
        elif rsi > self.overbought_level and position and position.is_long:
            return Order(
                symbol=symbol,
                exchange="NSE",
                signal=Signal.EXIT_LONG,
                quantity=position.quantity,
                order_type=OrderType.MARKET,
                reason=f"RSI overbought: {rsi:.2f}",
            )

        return None
