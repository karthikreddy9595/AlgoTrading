"""
Test script for indicator calculations.

Run with: python -m pytest tests/test_indicators.py -v
Or manually: python tests/test_indicators.py
"""

from decimal import Decimal
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.indicators import calculate_sma, calculate_rsi, calculate_indicators_for_strategy
from strategies.implementations.ma_crossover import SimpleMovingAverageCrossover, RSIMomentum
from strategies.implementations.sma_rsi_crossover import SMARSICrossover


def test_sma_calculation():
    """Test Simple Moving Average calculation."""
    print("\n=== Testing SMA Calculation ===")

    # Sample price data
    prices = [Decimal(str(x)) for x in [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]]
    period = 3

    # Calculate SMA
    sma_values = calculate_sma(prices, period)

    print(f"Input prices: {[float(p) for p in prices]}")
    print(f"Period: {period}")
    print(f"SMA values: {[float(v) if v else None for v in sma_values]}")

    # Verify first few values are None (insufficient data)
    assert sma_values[0] is None
    assert sma_values[1] is None

    # Verify first valid SMA (average of 10, 11, 12)
    expected_first = Decimal("11")
    actual_first = sma_values[2]
    assert abs(actual_first - expected_first) < Decimal("0.01"), f"Expected {expected_first}, got {actual_first}"

    # Verify last SMA (average of 18, 19, 20)
    expected_last = Decimal("19")
    actual_last = sma_values[-1]
    assert abs(actual_last - expected_last) < Decimal("0.01"), f"Expected {expected_last}, got {actual_last}"

    print("[PASS] SMA calculation test passed!")


def test_rsi_calculation():
    """Test RSI calculation."""
    print("\n=== Testing RSI Calculation ===")

    # Sample price data with clear trend
    prices = [Decimal(str(x)) for x in [
        100, 101, 102, 103, 104, 105, 106, 107, 108, 109,  # Uptrend
        110, 111, 112, 113, 114, 115  # Continued uptrend
    ]]
    period = 14

    # Calculate RSI
    rsi_values = calculate_rsi(prices, period)

    print(f"Input prices (first 5): {[float(p) for p in prices[:5]]}")
    print(f"Input prices (last 5): {[float(p) for p in prices[-5:]]}")
    print(f"Period: {period}")
    print(f"RSI values (first 5): {[float(v) if v else None for v in rsi_values[:5]]}")
    print(f"RSI values (last 5): {[float(v) if v else None for v in rsi_values[-5:]]}")

    # Verify first values are None (insufficient data)
    for i in range(period):
        assert rsi_values[i] is None, f"Expected None at index {i}"

    # RSI should be high (>70) during strong uptrend
    last_rsi = rsi_values[-1]
    assert last_rsi is not None, "Last RSI should not be None"
    assert last_rsi > Decimal("70"), f"RSI should be high during uptrend, got {float(last_rsi)}"
    assert last_rsi <= Decimal("100"), f"RSI should be <= 100, got {float(last_rsi)}"

    print(f"[PASS] RSI calculation test passed! Last RSI: {float(last_rsi):.2f}")


def test_indicators_for_sma_crossover():
    """Test indicator calculation for SMA Crossover strategy."""
    print("\n=== Testing Indicators for SMA Crossover Strategy ===")

    # Generate sample candle data
    base_time = datetime.now()
    candles = []
    for i in range(50):
        candles.append({
            'timestamp': (base_time - timedelta(minutes=5 * (50 - i))).isoformat(),
            'close': 100 + i,  # Uptrend
        })

    # Calculate indicators with default config
    indicators = calculate_indicators_for_strategy(
        strategy_class=SimpleMovingAverageCrossover,
        candles=candles,
        config_params={}
    )

    print(f"Number of candles: {len(candles)}")
    print(f"Number of indicators: {len(indicators)}")

    # Should have Fast SMA and Slow SMA
    assert len(indicators) == 2, f"Expected 2 indicators, got {len(indicators)}"

    # Verify Fast SMA
    fast_sma = next((ind for ind in indicators if 'Fast' in ind.name), None)
    assert fast_sma is not None, "Fast SMA indicator not found"
    assert fast_sma.type == 'sma'
    assert fast_sma.pane == 'main'
    assert fast_sma.params['period'] == 9
    print(f"[PASS] Fast SMA: {fast_sma.name}, color: {fast_sma.color}")

    # Verify Slow SMA
    slow_sma = next((ind for ind in indicators if 'Slow' in ind.name), None)
    assert slow_sma is not None, "Slow SMA indicator not found"
    assert slow_sma.type == 'sma'
    assert slow_sma.pane == 'main'
    assert slow_sma.params['period'] == 21
    print(f"[PASS] Slow SMA: {slow_sma.name}, color: {slow_sma.color}")

    print("[PASS] SMA Crossover strategy indicators test passed!")


def test_indicators_for_sma_rsi_strategy():
    """Test indicator calculation for SMA+RSI strategy."""
    print("\n=== Testing Indicators for SMA+RSI Strategy ===")

    # Generate sample candle data
    base_time = datetime.now()
    candles = []
    for i in range(50):
        candles.append({
            'timestamp': (base_time - timedelta(minutes=15 * (50 - i))).isoformat(),
            'close': 100 + i * 0.5,
        })

    # Calculate indicators with custom config
    config_params = {
        'fast_ma_period': 5,
        'slow_ma_period': 10,
        'rsi_period': 14,
        'rsi_overbought': 75,
        'rsi_oversold': 25,
    }

    indicators = calculate_indicators_for_strategy(
        strategy_class=SMARSICrossover,
        candles=candles,
        config_params=config_params
    )

    print(f"Number of candles: {len(candles)}")
    print(f"Number of indicators: {len(indicators)}")
    print(f"Config params: {config_params}")

    # Should have Fast SMA, Slow SMA, and RSI
    assert len(indicators) == 3, f"Expected 3 indicators, got {len(indicators)}"

    # Verify Fast SMA with custom period
    fast_sma = next((ind for ind in indicators if 'Fast' in ind.name), None)
    assert fast_sma is not None, "Fast SMA indicator not found"
    assert fast_sma.params['period'] == 5, f"Expected period 5, got {fast_sma.params['period']}"
    print(f"[PASS] Fast SMA: {fast_sma.name}, period: {fast_sma.params['period']}")

    # Verify Slow SMA with custom period
    slow_sma = next((ind for ind in indicators if 'Slow' in ind.name), None)
    assert slow_sma is not None, "Slow SMA indicator not found"
    assert slow_sma.params['period'] == 10, f"Expected period 10, got {slow_sma.params['period']}"
    print(f"[PASS] Slow SMA: {slow_sma.name}, period: {slow_sma.params['period']}")

    # Verify RSI with custom parameters
    rsi = next((ind for ind in indicators if 'RSI' in ind.name), None)
    assert rsi is not None, "RSI indicator not found"
    assert rsi.type == 'rsi'
    assert rsi.pane == 'oscillator'
    assert rsi.params['period'] == 14
    assert rsi.params['overbought'] == 75
    assert rsi.params['oversold'] == 25
    print(f"[PASS] RSI: {rsi.name}, params: {rsi.params}")

    print("[PASS] SMA+RSI strategy indicators test passed!")


def test_indicators_for_rsi_momentum():
    """Test indicator calculation for RSI Momentum strategy."""
    print("\n=== Testing Indicators for RSI Momentum Strategy ===")

    # Generate sample candle data
    base_time = datetime.now()
    candles = []
    for i in range(50):
        candles.append({
            'timestamp': (base_time - timedelta(minutes=15 * (50 - i))).isoformat(),
            'close': 100 + (i % 10) * 2,  # Oscillating pattern
        })

    # Calculate indicators
    indicators = calculate_indicators_for_strategy(
        strategy_class=RSIMomentum,
        candles=candles,
        config_params={}
    )

    print(f"Number of candles: {len(candles)}")
    print(f"Number of indicators: {len(indicators)}")

    # Should have only RSI
    assert len(indicators) == 1, f"Expected 1 indicator, got {len(indicators)}"

    # Verify RSI
    rsi = indicators[0]
    assert 'RSI' in rsi.name, "RSI indicator not found"
    assert rsi.type == 'rsi'
    assert rsi.pane == 'oscillator'
    assert rsi.params['period'] == 14
    print(f"[PASS] RSI: {rsi.name}, color: {rsi.color}")

    print("[PASS] RSI Momentum strategy indicators test passed!")


def run_all_tests():
    """Run all indicator tests."""
    print("\n" + "="*60)
    print("INDICATOR CALCULATION TESTS")
    print("="*60)

    try:
        test_sma_calculation()
        test_rsi_calculation()
        test_indicators_for_sma_crossover()
        test_indicators_for_sma_rsi_strategy()
        test_indicators_for_rsi_momentum()

        print("\n" + "="*60)
        print("[PASS] ALL TESTS PASSED!")
        print("="*60 + "\n")
        return True
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}\n")
        return False
    except Exception as e:
        print(f"\n[FAIL] UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
