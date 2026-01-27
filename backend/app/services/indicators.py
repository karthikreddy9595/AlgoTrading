
"""
Indicator calculation utilities for chart visualization.

This module provides reusable functions for calculating technical indicators
used by trading strategies. Calculations match the strategy implementations
to ensure consistency between chart display and actual trading logic.
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal


def calculate_sma(prices: List[Decimal], period: int) -> List[Optional[Decimal]]:
    """
    Calculate Simple Moving Average.

    Args:
        prices: List of prices (close prices typically)
        period: Number of periods for SMA calculation

    Returns:
        List of SMA values (None for insufficient data points)
    """
    result = []

    for i in range(len(prices)):
        if i < period - 1:
            # Not enough data yet
            result.append(None)
        else:
            # Calculate SMA for this point
            window = prices[i - period + 1:i + 1]
            sma = sum(window) / period
            result.append(sma)

    return result


def calculate_rsi(prices: List[Decimal], period: int = 14) -> List[Optional[Decimal]]:
    """
    Calculate Relative Strength Index (RSI).

    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss

    Args:
        prices: List of prices (close prices typically)
        period: RSI period (default: 14)

    Returns:
        List of RSI values (None for insufficient data points)
    """
    if len(prices) < period + 1:
        return [None] * len(prices)

    result = []

    # Calculate price changes
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

    # Calculate RSI for each point
    for i in range(len(prices)):
        if i < period:
            # Not enough data yet
            result.append(None)
        else:
            # Calculate average gain and loss for this window
            window_gains = gains[i - period:i]
            window_losses = losses[i - period:i]

            avg_gain = sum(window_gains) / period
            avg_loss = sum(window_losses) / period

            if avg_loss == 0:
                rsi = Decimal("100")
            else:
                rs = avg_gain / avg_loss
                rsi = Decimal("100") - (Decimal("100") / (1 + rs))

            result.append(rsi)

    return result


def calculate_indicators_for_strategy(
    strategy_class,
    candles: List[Dict[str, Any]],
    config_params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Calculate indicators used by a specific strategy.

    This function dynamically determines which indicators a strategy uses
    and calculates them with the user's configured parameters.

    Args:
        strategy_class: The strategy class (e.g., SMARSICrossover)
        candles: List of OHLC candles with 'close' prices
        config_params: User's configuration parameters for the strategy

    Returns:
        List of indicator dictionaries with calculated data (compatible with ChartIndicator schema)
    """
    if not candles:
        return []

    config = config_params or {}
    indicators = []

    # Extract close prices
    close_prices = [Decimal(str(candle.get('close', 0))) for candle in candles]
    timestamps = [candle.get('timestamp') for candle in candles]

    # Import strategy classes for type checking
    from strategies.implementations.ma_crossover import SimpleMovingAverageCrossover, RSIMomentum
    from strategies.implementations.sma_rsi_crossover import SMARSICrossover

    # Calculate indicators based on strategy type
    if strategy_class in [SimpleMovingAverageCrossover, SMARSICrossover]:
        # SMA-based strategies
        fast_period = config.get('fast_ma_period', 9)
        slow_period = config.get('slow_ma_period', 21)

        # Calculate Fast SMA
        fast_sma_values = calculate_sma(close_prices, fast_period)
        fast_sma_data = [
            {
                "time": timestamps[i],
                "value": float(val) if val is not None else None
            }
            for i, val in enumerate(fast_sma_values)
        ]
        indicators.append({
            "name": f"Fast SMA ({fast_period})",
            "type": "sma",
            "pane": "main",
            "color": "#2962FF",  # Blue
            "data": fast_sma_data,
            "params": {"period": fast_period}
        })

        # Calculate Slow SMA
        slow_sma_values = calculate_sma(close_prices, slow_period)
        slow_sma_data = [
            {
                "time": timestamps[i],
                "value": float(val) if val is not None else None
            }
            for i, val in enumerate(slow_sma_values)
        ]
        indicators.append({
            "name": f"Slow SMA ({slow_period})",
            "type": "sma",
            "pane": "main",
            "color": "#FF6D00",  # Orange
            "data": slow_sma_data,
            "params": {"period": slow_period}
        })

    if strategy_class in [RSIMomentum, SMARSICrossover]:
        # RSI-based strategies
        rsi_period = config.get('rsi_period', 14)
        rsi_overbought = config.get('rsi_overbought', 70)
        rsi_oversold = config.get('rsi_oversold', 30)

        # Calculate RSI
        rsi_values = calculate_rsi(close_prices, rsi_period)
        rsi_data = [
            {
                "time": timestamps[i],
                "value": float(val) if val is not None else None
            }
            for i, val in enumerate(rsi_values)
        ]
        indicators.append({
            "name": f"RSI ({rsi_period})",
            "type": "rsi",
            "pane": "oscillator",
            "color": "#9C27B0",  # Purple
            "data": rsi_data,
            "params": {
                "period": rsi_period,
                "overbought": rsi_overbought,
                "oversold": rsi_oversold
            }
        })

    return indicators
