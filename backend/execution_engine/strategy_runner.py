"""
Strategy Runner - Individual strategy execution in isolated process.

This module handles the execution of a single strategy subscription
in its own process for isolation and fault tolerance.
"""

import asyncio
import signal
import sys
import json
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from multiprocessing import Process, Queue
from queue import Empty
import traceback

from strategies.base import BaseStrategy, MarketData, Order, StrategyContext, Signal
from execution_engine.risk_manager import RiskManager, RiskLimits, RiskCheckResult


class StrategyRunner:
    """
    Runs a single strategy subscription in an isolated process.

    Features:
    - Process isolation for fault tolerance
    - Inter-process communication via queues
    - Graceful shutdown handling
    - State persistence for recovery
    """

    def __init__(
        self,
        subscription_id: str,
        user_id: str,
        strategy_class: type,
        context: StrategyContext,
        risk_limits: RiskLimits,
    ):
        self.subscription_id = subscription_id
        self.user_id = user_id
        self.strategy_class = strategy_class
        self.context = context
        self.risk_limits = risk_limits

        self.process: Optional[Process] = None
        self.command_queue: Queue = Queue()
        self.result_queue: Queue = Queue()
        self.market_data_queue: Queue = Queue()

        self._is_running = False
        self._is_paused = False

    def start(self) -> bool:
        """Start the strategy runner process."""
        if self._is_running:
            return False

        self.process = Process(
            target=self._run_strategy_process,
            args=(
                self.subscription_id,
                self.user_id,
                self.strategy_class,
                self.context,
                self.risk_limits,
                self.command_queue,
                self.result_queue,
                self.market_data_queue,
            ),
            daemon=True,
        )
        self.process.start()
        self._is_running = True
        return True

    def stop(self, timeout: float = 10.0) -> bool:
        """
        Stop the strategy runner gracefully.

        Args:
            timeout: Max seconds to wait for graceful shutdown

        Returns:
            True if stopped successfully
        """
        if not self._is_running or not self.process:
            return True

        # Send stop command
        self.command_queue.put({"type": "STOP"})

        # Wait for process to finish
        self.process.join(timeout=timeout)

        if self.process.is_alive():
            # Force terminate if still running
            self.process.terminate()
            self.process.join(timeout=2)

            if self.process.is_alive():
                self.process.kill()

        self._is_running = False
        return True

    def pause(self) -> bool:
        """Pause strategy execution."""
        if not self._is_running:
            return False

        self.command_queue.put({"type": "PAUSE"})
        self._is_paused = True
        return True

    def resume(self) -> bool:
        """Resume strategy execution."""
        if not self._is_running or not self._is_paused:
            return False

        self.command_queue.put({"type": "RESUME"})
        self._is_paused = False
        return True

    def send_market_data(self, data: MarketData) -> None:
        """Send market data to the strategy process."""
        if self._is_running and not self._is_paused:
            self.market_data_queue.put(data)

    def get_result(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """
        Get result from strategy process.

        Returns order or status updates from the strategy.
        """
        try:
            return self.result_queue.get(timeout=timeout)
        except Empty:
            return None

    def is_alive(self) -> bool:
        """Check if strategy process is alive."""
        return self.process is not None and self.process.is_alive()

    @property
    def is_running(self) -> bool:
        return self._is_running and self.is_alive()

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @staticmethod
    def _run_strategy_process(
        subscription_id: str,
        user_id: str,
        strategy_class: type,
        context: StrategyContext,
        risk_limits: RiskLimits,
        command_queue: Queue,
        result_queue: Queue,
        market_data_queue: Queue,
    ):
        """
        Main strategy process function.

        This runs in a separate process and handles:
        - Strategy initialization
        - Market data processing
        - Order generation and validation
        - Command handling (stop, pause, resume)
        """
        # Setup signal handlers
        def handle_signal(signum, frame):
            result_queue.put({
                "type": "STATUS",
                "status": "stopping",
                "reason": f"Received signal {signum}",
            })
            sys.exit(0)

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        # Initialize strategy
        try:
            strategy = strategy_class(context)
            risk_manager = RiskManager()
            is_paused = False
            today_trade_count = 0

            strategy.on_start()

            result_queue.put({
                "type": "STATUS",
                "status": "started",
                "subscription_id": subscription_id,
            })

        except Exception as e:
            result_queue.put({
                "type": "ERROR",
                "error": str(e),
                "traceback": traceback.format_exc(),
            })
            return

        # Main loop
        while True:
            try:
                # Check for commands
                try:
                    cmd = command_queue.get_nowait()
                    cmd_type = cmd.get("type")

                    if cmd_type == "STOP":
                        strategy.on_stop()
                        result_queue.put({
                            "type": "STATUS",
                            "status": "stopped",
                        })
                        break

                    elif cmd_type == "PAUSE":
                        strategy.on_pause()
                        is_paused = True
                        result_queue.put({
                            "type": "STATUS",
                            "status": "paused",
                        })

                    elif cmd_type == "RESUME":
                        strategy.on_resume()
                        is_paused = False
                        result_queue.put({
                            "type": "STATUS",
                            "status": "resumed",
                        })

                    elif cmd_type == "UPDATE_CONTEXT":
                        # Update context with new data
                        new_context = cmd.get("context")
                        if new_context:
                            strategy.context = new_context

                except Empty:
                    pass

                # Skip processing if paused
                if is_paused:
                    asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.1))
                    continue

                # Process market data
                try:
                    market_data = market_data_queue.get(timeout=0.1)

                    # Call strategy's on_market_data
                    order = strategy.on_market_data(market_data)

                    if order:
                        # Validate order with risk manager
                        risk_result = risk_manager.check_order(
                            order=order,
                            context=strategy.context,
                            limits=risk_limits,
                            today_trade_count=today_trade_count,
                        )

                        if risk_result.allowed:
                            result_queue.put({
                                "type": "ORDER",
                                "order": {
                                    "symbol": order.symbol,
                                    "exchange": order.exchange,
                                    "signal": order.signal.value,
                                    "quantity": order.quantity,
                                    "order_type": order.order_type.value,
                                    "price": float(order.price) if order.price else None,
                                    "stop_loss": float(order.stop_loss) if order.stop_loss else None,
                                    "target": float(order.target) if order.target else None,
                                    "reason": order.reason,
                                },
                                "subscription_id": subscription_id,
                            })
                            today_trade_count += 1
                        else:
                            result_queue.put({
                                "type": "RISK_BLOCKED",
                                "reason": risk_result.reason,
                                "limit_type": risk_result.limit_type,
                                "order": {
                                    "symbol": order.symbol,
                                    "signal": order.signal.value,
                                },
                            })

                            # Trigger kill switch if drawdown or daily loss hit
                            if risk_result.limit_type in ["max_drawdown", "daily_loss"]:
                                result_queue.put({
                                    "type": "KILL_SWITCH_TRIGGER",
                                    "reason": risk_result.reason,
                                    "limit_type": risk_result.limit_type,
                                    "subscription_id": subscription_id,
                                })

                except Empty:
                    pass

            except Exception as e:
                result_queue.put({
                    "type": "ERROR",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                })

        # Cleanup
        result_queue.put({
            "type": "STATUS",
            "status": "exited",
            "state": strategy.get_state(),
        })
