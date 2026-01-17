"""
Backtest engine for testing trading strategies on historical data.
"""

from backtest.metrics import MetricsCalculator
from backtest.simulator import OrderSimulator
from backtest.engine import BacktestEngine
from backtest.optimizer import MonteCarloOptimizer, ParameterRange, OptimizationConfig, SampleResult

__all__ = [
    "MetricsCalculator",
    "OrderSimulator",
    "BacktestEngine",
    "MonteCarloOptimizer",
    "ParameterRange",
    "OptimizationConfig",
    "SampleResult",
]
