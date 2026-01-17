"""
Monte Carlo Parameter Optimizer for trading strategies.

Randomly samples parameter combinations from specified ranges
and runs backtests to find optimal parameters.
"""

import random
import asyncio
from typing import Dict, List, Any, Optional, Callable
from decimal import Decimal
from dataclasses import dataclass, field
from datetime import datetime
from itertools import product
from collections import defaultdict

from backtest.engine import BacktestEngine, BacktestConfig
from backtest.metrics import PerformanceMetrics


@dataclass
class ParameterRange:
    """Defines the range and step for a parameter."""
    name: str
    min_value: float
    max_value: float
    step: float
    param_type: str = "float"  # 'int' or 'float'

    def get_possible_values(self) -> List[float]:
        """Generate all possible values within the range."""
        values = []
        current = self.min_value
        while current <= self.max_value + 0.0001:  # Small epsilon for float comparison
            if self.param_type == 'int':
                values.append(int(round(current)))
            else:
                values.append(round(current, 4))
            current += self.step
        return values

    def sample_value(self) -> float:
        """Randomly sample a value from the range."""
        possible = self.get_possible_values()
        return random.choice(possible)


@dataclass
class OptimizationConfig:
    """Configuration for an optimization run."""
    backtest_config: BacktestConfig  # Base backtest configuration
    parameter_ranges: List[ParameterRange]
    num_samples: int
    objective_metric: str  # Metric to optimize


@dataclass
class SampleResult:
    """Result of a single parameter sample."""
    parameters: Dict[str, Any]
    metrics: Dict[str, Any]
    objective_value: float
    trades_count: int
    error: Optional[str] = None


# Type alias for progress callback
ProgressCallback = Callable[[int, int, str], Any]


class MonteCarloOptimizer:
    """
    Monte Carlo parameter optimizer.

    Randomly samples parameter combinations and evaluates them
    using backtesting to find optimal settings.
    """

    def __init__(self, engine: Optional[BacktestEngine] = None):
        """
        Initialize the optimizer.

        Args:
            engine: BacktestEngine instance. If None, creates a new one.
        """
        self.engine = engine or BacktestEngine()
        self.results: List[SampleResult] = []

    def _generate_samples(
        self,
        parameter_ranges: List[ParameterRange],
        num_samples: int
    ) -> List[Dict[str, Any]]:
        """
        Generate random parameter combinations using Monte Carlo sampling.

        Uses smart sampling to ensure good coverage:
        - First ensures corner cases (min/max combinations) are included
        - Then fills remaining samples randomly
        - Falls back to exhaustive search if total combinations <= num_samples
        """
        samples = []

        # Calculate total possible combinations
        total_combinations = 1
        for param in parameter_ranges:
            total_combinations *= len(param.get_possible_values())

        # If we can test all combinations, do exhaustive search
        if total_combinations <= num_samples:
            return self._generate_exhaustive_samples(parameter_ranges)

        # Add corner cases (all min, all max, etc.) - up to 25% of samples
        corner_samples = self._generate_corner_samples(parameter_ranges)
        max_corners = min(len(corner_samples), num_samples // 4)
        samples.extend(corner_samples[:max_corners])

        # Generate random samples for remaining
        seen = {tuple(sorted(s.items())) for s in samples}
        attempts = 0
        max_attempts = num_samples * 10

        while len(samples) < num_samples and attempts < max_attempts:
            sample = {
                param.name: param.sample_value()
                for param in parameter_ranges
            }
            sample_key = tuple(sorted(sample.items()))
            if sample_key not in seen:
                seen.add(sample_key)
                samples.append(sample)
            attempts += 1

        return samples

    def _generate_exhaustive_samples(
        self,
        parameter_ranges: List[ParameterRange]
    ) -> List[Dict[str, Any]]:
        """Generate all possible parameter combinations."""
        all_values = [
            [(param.name, v) for v in param.get_possible_values()]
            for param in parameter_ranges
        ]

        samples = []
        for combination in product(*all_values):
            samples.append(dict(combination))

        return samples

    def _generate_corner_samples(
        self,
        parameter_ranges: List[ParameterRange]
    ) -> List[Dict[str, Any]]:
        """Generate samples at parameter extremes."""
        extremes = [
            [(param.name, param.min_value), (param.name, param.max_value)]
            for param in parameter_ranges
        ]

        samples = []
        for combination in product(*extremes):
            sample = {}
            for name, value in combination:
                # Get the param to check if it should be int
                for param in parameter_ranges:
                    if param.name == name:
                        if param.param_type == 'int':
                            sample[name] = int(value)
                        else:
                            sample[name] = value
                        break
            samples.append(sample)

        return samples

    async def run(
        self,
        config: OptimizationConfig,
        historical_data: List[Dict[str, Any]],
        on_progress: Optional[ProgressCallback] = None,
    ) -> List[SampleResult]:
        """
        Run Monte Carlo optimization.

        Args:
            config: Optimization configuration
            historical_data: OHLC data for backtesting
            on_progress: Callback for progress updates (completed, total, message)

        Returns:
            List of results sorted by objective metric (descending)
        """
        self.results = []

        # Generate parameter samples
        samples = self._generate_samples(
            config.parameter_ranges,
            config.num_samples
        )

        total = len(samples)

        for i, params in enumerate(samples):
            try:
                # Create backtest config with this parameter set
                bt_config = BacktestConfig(
                    strategy_module_path=config.backtest_config.strategy_module_path,
                    strategy_class_name=config.backtest_config.strategy_class_name,
                    symbol=config.backtest_config.symbol,
                    exchange=config.backtest_config.exchange,
                    interval=config.backtest_config.interval,
                    start_date=config.backtest_config.start_date,
                    end_date=config.backtest_config.end_date,
                    initial_capital=config.backtest_config.initial_capital,
                    strategy_config=params,  # Apply sampled parameters
                    slippage_percent=config.backtest_config.slippage_percent,
                    commission=config.backtest_config.commission,
                )

                # Run backtest
                result = await self.engine.run(bt_config, historical_data)

                if result.error:
                    sample_result = SampleResult(
                        parameters=params,
                        metrics={},
                        objective_value=float('-inf'),
                        trades_count=0,
                        error=result.error
                    )
                else:
                    # Extract metrics
                    metrics = self._extract_metrics(result.metrics)

                    # Get objective value (handle metrics where lower is better)
                    obj_value = metrics.get(config.objective_metric, 0)
                    if config.objective_metric == 'max_drawdown':
                        obj_value = -obj_value  # Invert for minimization

                    sample_result = SampleResult(
                        parameters=params,
                        metrics=metrics,
                        objective_value=obj_value,
                        trades_count=metrics.get('total_trades', 0),
                    )

                self.results.append(sample_result)

            except Exception as e:
                self.results.append(SampleResult(
                    parameters=params,
                    metrics={},
                    objective_value=float('-inf'),
                    trades_count=0,
                    error=str(e)
                ))

            # Report progress
            if on_progress:
                await self._report_progress(
                    on_progress, i + 1, total,
                    f"Completed sample {i + 1}/{total}"
                )

            # Allow other tasks to run
            await asyncio.sleep(0)

        # Sort by objective value (descending)
        self.results.sort(key=lambda r: r.objective_value, reverse=True)

        return self.results

    def _extract_metrics(self, perf_metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Extract metrics from PerformanceMetrics to a dictionary."""
        return {
            'total_return': float(perf_metrics.total_return),
            'total_return_percent': float(perf_metrics.total_return_percent),
            'cagr': float(perf_metrics.cagr),
            'sharpe_ratio': float(perf_metrics.sharpe_ratio),
            'sortino_ratio': float(perf_metrics.sortino_ratio),
            'calmar_ratio': float(perf_metrics.calmar_ratio),
            'max_drawdown': float(perf_metrics.max_drawdown),
            'avg_drawdown': float(perf_metrics.avg_drawdown),
            'win_rate': float(perf_metrics.win_rate),
            'profit_factor': float(perf_metrics.profit_factor),
            'total_trades': perf_metrics.total_trades,
            'winning_trades': perf_metrics.winning_trades,
            'losing_trades': perf_metrics.losing_trades,
            'final_capital': float(perf_metrics.final_capital),
            'max_capital': float(perf_metrics.max_capital),
        }

    async def _report_progress(
        self,
        callback: ProgressCallback,
        completed: int,
        total: int,
        message: str
    ) -> None:
        """Report progress via callback."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(completed, total, message)
            else:
                callback(completed, total, message)
        except Exception:
            pass  # Ignore progress reporting errors

    def get_best_result(self) -> Optional[SampleResult]:
        """Get the best result from the optimization."""
        valid_results = [r for r in self.results if r.error is None]
        return valid_results[0] if valid_results else None

    def get_heatmap_data(
        self,
        param_x: str,
        param_y: str,
        metric: str = 'total_return_percent'
    ) -> Dict[str, Any]:
        """
        Generate heatmap data for two parameters.

        For cells with multiple samples, uses the average metric value.

        Args:
            param_x: Name of parameter for X axis
            param_y: Name of parameter for Y axis
            metric: Metric to display (default: total_return_percent)

        Returns:
            Dictionary with heatmap data including x_values, y_values,
            data points, and best coordinates.
        """
        # Group results by (x, y) parameter values
        grouped = defaultdict(list)
        x_values = set()
        y_values = set()

        for result in self.results:
            if result.error:
                continue

            x_val = result.parameters.get(param_x)
            y_val = result.parameters.get(param_y)
            metric_val = result.metrics.get(metric, 0)

            if x_val is not None and y_val is not None:
                grouped[(x_val, y_val)].append(metric_val)
                x_values.add(x_val)
                y_values.add(y_val)

        # Build heatmap data points (average for each cell)
        data = []
        best_x, best_y, best_value = None, None, float('-inf')

        for (x, y), values in grouped.items():
            avg_value = sum(values) / len(values)
            data.append({
                'x': x,
                'y': y,
                'value': round(avg_value, 4)
            })
            if avg_value > best_value:
                best_x, best_y, best_value = x, y, avg_value

        return {
            'param_x': param_x,
            'param_y': param_y,
            'x_values': sorted(x_values),
            'y_values': sorted(y_values),
            'data': data,
            'best_x': best_x,
            'best_y': best_y,
            'best_value': round(best_value, 4) if best_value != float('-inf') else None,
            'metric': metric
        }
