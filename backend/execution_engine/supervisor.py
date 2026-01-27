"""
Strategy Supervisor - Manages multiple strategy runners.

This module provides centralized management of all running strategies:
- Starting/stopping strategies
- Health monitoring
- Auto-recovery on crash
- Kill switch integration
"""

import asyncio
from typing import Dict, Optional, List, Callable
from datetime import datetime
from decimal import Decimal
import importlib
import redis.asyncio as redis

from execution_engine.strategy_runner import StrategyRunner
from execution_engine.kill_switch import KillSwitch
from execution_engine.risk_manager import RiskLimits
from strategies.base import StrategyContext, MarketData, Position


class StrategySupervisor:
    """
    Supervises all running strategy instances.

    Responsibilities:
    - Start/stop strategy runners
    - Monitor health and auto-restart on crash
    - Distribute market data to relevant strategies
    - Handle kill switch events
    - Route orders to order manager
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        order_callback: Optional[Callable] = None,
    ):
        self.redis = redis_client
        self.kill_switch = KillSwitch(redis_client)
        self.order_callback = order_callback

        self._runners: Dict[str, StrategyRunner] = {}
        self._subscription_symbols: Dict[str, List[str]] = {}  # subscription_id -> symbols
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._result_task: Optional[asyncio.Task] = None
        self._kill_switch_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the supervisor."""
        self._running = True

        # Start monitoring tasks
        self._monitor_task = asyncio.create_task(self._monitor_runners())
        self._result_task = asyncio.create_task(self._process_results())
        self._kill_switch_task = asyncio.create_task(self._handle_kill_switch_events())

    async def stop(self):
        """Stop the supervisor and all runners."""
        self._running = False

        # Stop all runners
        for subscription_id in list(self._runners.keys()):
            await self.stop_strategy(subscription_id)

        # Cancel monitoring tasks
        for task in [self._monitor_task, self._result_task, self._kill_switch_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def start_strategy(
        self,
        subscription_id: str,
        user_id: str,
        strategy_module: str,
        strategy_class: str,
        context_data: dict,
        risk_limits_data: dict,
        symbols: List[str],
        dry_run: bool = False,
    ) -> bool:
        """
        Start a strategy for a subscription.

        Args:
            subscription_id: Strategy subscription ID
            user_id: User ID
            strategy_module: Python module path (e.g., 'strategies.implementations.ma_crossover')
            strategy_class: Class name (e.g., 'SimpleMovingAverageCrossover')
            context_data: Strategy context data
            risk_limits_data: Risk limits configuration
            symbols: Symbols to subscribe for market data

        Returns:
            True if started successfully
        """
        if subscription_id in self._runners:
            return False

        # Check kill switch
        if await self.kill_switch.is_strategy_active(subscription_id, user_id):
            return False

        try:
            # Load strategy class
            module = importlib.import_module(strategy_module)
            cls = getattr(module, strategy_class)

            # Create context
            context = StrategyContext(
                strategy_id=context_data.get("strategy_id", ""),
                user_id=user_id,
                subscription_id=subscription_id,
                capital=Decimal(str(context_data.get("capital", 0))),
                max_positions=context_data.get("max_positions", 5),
                max_drawdown_percent=Decimal(str(context_data.get("max_drawdown_percent", 10))),
                daily_loss_limit=Decimal(str(context_data.get("daily_loss_limit", 0))),
                per_trade_sl_percent=Decimal(str(context_data.get("per_trade_sl_percent", 2))),
                is_paper_trading=context_data.get("is_paper_trading", True),
                positions=[],
                today_pnl=Decimal(str(context_data.get("today_pnl", 0))),
                total_pnl=Decimal(str(context_data.get("total_pnl", 0))),
            )

            # Create risk limits
            risk_limits = RiskLimits(
                max_drawdown_percent=Decimal(str(risk_limits_data.get("max_drawdown_percent", 10))),
                daily_loss_limit=Decimal(str(risk_limits_data.get("daily_loss_limit", 0))),
                per_trade_sl_percent=Decimal(str(risk_limits_data.get("per_trade_sl_percent", 2))),
                max_positions=risk_limits_data.get("max_positions", 5),
            )

            # Create runner
            runner = StrategyRunner(
                subscription_id=subscription_id,
                user_id=user_id,
                strategy_class=cls,
                context=context,
                risk_limits=risk_limits,
                dry_run=dry_run,
            )

            # Start runner
            if runner.start():
                self._runners[subscription_id] = runner
                self._subscription_symbols[subscription_id] = symbols
                return True

        except Exception as e:
            print(f"Failed to start strategy {subscription_id}: {e}")

        return False

    async def stop_strategy(self, subscription_id: str, timeout: float = 10.0) -> bool:
        """
        Stop a running strategy.

        Args:
            subscription_id: Strategy subscription to stop
            timeout: Max seconds to wait for graceful stop

        Returns:
            True if stopped successfully
        """
        if subscription_id not in self._runners:
            return False

        runner = self._runners[subscription_id]
        result = runner.stop(timeout=timeout)

        if result:
            del self._runners[subscription_id]
            if subscription_id in self._subscription_symbols:
                del self._subscription_symbols[subscription_id]

        return result

    async def pause_strategy(self, subscription_id: str) -> bool:
        """Pause a running strategy."""
        if subscription_id not in self._runners:
            return False

        return self._runners[subscription_id].pause()

    async def resume_strategy(self, subscription_id: str) -> bool:
        """Resume a paused strategy."""
        if subscription_id not in self._runners:
            return False

        return self._runners[subscription_id].resume()

    def distribute_market_data(self, data: MarketData):
        """
        Distribute market data to relevant strategies.

        Args:
            data: Market data tick
        """
        symbol = f"{data.exchange}:{data.symbol}" if data.exchange else data.symbol

        for subscription_id, symbols in self._subscription_symbols.items():
            if symbol in symbols or data.symbol in symbols:
                runner = self._runners.get(subscription_id)
                if runner and runner.is_running and not runner.is_paused:
                    runner.send_market_data(data)

    async def _monitor_runners(self):
        """Monitor runner health and auto-restart crashed runners."""
        while self._running:
            try:
                for subscription_id, runner in list(self._runners.items()):
                    if not runner.is_alive() and runner._is_running:
                        # Runner crashed - attempt restart
                        print(f"Runner {subscription_id} crashed, attempting restart...")

                        # TODO: Implement restart logic with state recovery
                        # For now, just mark as stopped
                        runner._is_running = False

                await asyncio.sleep(5)  # Check every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Monitor error: {e}")

    async def _process_results(self):
        """Process results from all runners."""
        while self._running:
            try:
                for subscription_id, runner in list(self._runners.items()):
                    result = runner.get_result()

                    if result:
                        result_type = result.get("type")

                        if result_type == "ORDER" and self.order_callback:
                            await self.order_callback(result)

                        elif result_type == "KILL_SWITCH_TRIGGER":
                            # Activate kill switch for this strategy
                            await self.kill_switch.activate_for_strategy(
                                subscription_id=subscription_id,
                                reason=result.get("reason", "Risk limit breached"),
                                activated_by="system",
                            )
                            await self.stop_strategy(subscription_id)

                        elif result_type == "ERROR":
                            print(f"Strategy {subscription_id} error: {result.get('error')}")

                await asyncio.sleep(0.01)  # Small delay to prevent busy loop

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Result processing error: {e}")

    async def _handle_kill_switch_events(self):
        """Handle kill switch events from Redis pub/sub."""
        async def on_event(event):
            event_type = event.get("type")

            if event_type == "GLOBAL_STOP":
                # Stop all strategies
                for subscription_id in list(self._runners.keys()):
                    await self.stop_strategy(subscription_id)

            elif event_type == "USER_STOP":
                user_id = event.get("user_id")
                # Stop all strategies for this user
                for subscription_id, runner in list(self._runners.items()):
                    if runner.user_id == user_id:
                        await self.stop_strategy(subscription_id)

            elif event_type == "STRATEGY_STOP":
                subscription_id = event.get("subscription_id")
                if subscription_id in self._runners:
                    await self.stop_strategy(subscription_id)

        try:
            await self.kill_switch.subscribe_events(on_event)
        except asyncio.CancelledError:
            pass

    def get_status(self, subscription_id: str) -> Optional[dict]:
        """Get status of a strategy runner."""
        if subscription_id not in self._runners:
            return None

        runner = self._runners[subscription_id]
        return {
            "subscription_id": subscription_id,
            "is_running": runner.is_running,
            "is_paused": runner.is_paused,
            "is_alive": runner.is_alive(),
        }

    def get_all_status(self) -> List[dict]:
        """Get status of all runners."""
        return [
            self.get_status(sub_id)
            for sub_id in self._runners.keys()
        ]
