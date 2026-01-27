"""
Execution Engine - Main entry point for strategy execution.

This module provides the high-level interface for the execution engine,
coordinating strategy supervision, market data, and order management.
"""

import asyncio
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import redis.asyncio as redis
from decimal import Decimal

from execution_engine.supervisor import StrategySupervisor
from execution_engine.kill_switch import KillSwitch
from brokers.base import BaseBroker, MarketQuote
from strategies.base import MarketData


class ExecutionEngine:
    """
    Main execution engine for running trading strategies.

    Coordinates:
    - Strategy supervision
    - Market data distribution
    - Order routing
    - Risk management
    """

    def __init__(
        self,
        redis_url: str,
        broker: Optional[BaseBroker] = None,
        db_session: Optional[Any] = None,
    ):
        self.redis_url = redis_url
        self.broker = broker
        self.db_session = db_session

        self._redis: Optional[redis.Redis] = None
        self._supervisor: Optional[StrategySupervisor] = None
        self._kill_switch: Optional[KillSwitch] = None
        self._running = False

        self._order_handlers: List[Callable] = []
        self._market_data_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the execution engine."""
        # Connect to Redis
        self._redis = redis.from_url(self.redis_url, decode_responses=True)

        # Initialize components
        self._kill_switch = KillSwitch(self._redis)
        self._supervisor = StrategySupervisor(
            redis_client=self._redis,
            order_callback=self._handle_order,
        )

        # Start supervisor
        await self._supervisor.start()
        self._running = True

        print("Execution engine started")

    async def stop(self):
        """Stop the execution engine."""
        self._running = False

        # Stop supervisor
        if self._supervisor:
            await self._supervisor.stop()

        # Stop market data
        if self._market_data_task:
            self._market_data_task.cancel()
            try:
                await self._market_data_task
            except asyncio.CancelledError:
                pass

        # Close Redis connection
        if self._redis:
            await self._redis.close()

        print("Execution engine stopped")

    async def start_strategy(
        self,
        subscription_id: str,
        user_id: str,
        strategy_module: str,
        strategy_class: str,
        config: dict,
    ) -> bool:
        """
        Start a strategy for a subscription.

        Args:
            subscription_id: Strategy subscription ID
            user_id: User ID
            strategy_module: Python module path
            strategy_class: Strategy class name
            config: Configuration including context, risk limits, symbols

        Returns:
            True if started successfully
        """
        if not self._supervisor:
            return False

        return await self._supervisor.start_strategy(
            subscription_id=subscription_id,
            user_id=user_id,
            strategy_module=strategy_module,
            strategy_class=strategy_class,
            context_data=config.get("context", {}),
            risk_limits_data=config.get("risk_limits", {}),
            symbols=config.get("symbols", []),
            dry_run=config.get("dry_run", False),
        )

    async def stop_strategy(self, subscription_id: str) -> bool:
        """Stop a running strategy."""
        if not self._supervisor:
            return False

        return await self._supervisor.stop_strategy(subscription_id)

    async def pause_strategy(self, subscription_id: str) -> bool:
        """Pause a running strategy."""
        if not self._supervisor:
            return False

        return await self._supervisor.pause_strategy(subscription_id)

    async def resume_strategy(self, subscription_id: str) -> bool:
        """Resume a paused strategy."""
        if not self._supervisor:
            return False

        return await self._supervisor.resume_strategy(subscription_id)

    async def activate_global_kill_switch(self, reason: str, activated_by: str):
        """Activate global kill switch."""
        if self._kill_switch:
            await self._kill_switch.activate_global(reason, activated_by)

    async def deactivate_global_kill_switch(self, deactivated_by: str):
        """Deactivate global kill switch."""
        if self._kill_switch:
            await self._kill_switch.deactivate_global(deactivated_by)

    async def activate_user_kill_switch(self, user_id: str, reason: str):
        """Activate kill switch for a user."""
        if self._kill_switch:
            await self._kill_switch.activate_for_user(user_id, reason)

    async def deactivate_user_kill_switch(self, user_id: str):
        """Deactivate kill switch for a user."""
        if self._kill_switch:
            await self._kill_switch.deactivate_for_user(user_id)

    def add_order_handler(self, handler: Callable):
        """Add handler for order events."""
        self._order_handlers.append(handler)

    async def _handle_order(self, order_data: dict):
        """Handle order from strategy."""
        # Log order generation
        await self._log_order_event(
            order_data=order_data,
            event_type="generated",
            is_dry_run=order_data.get("is_dry_run", False)
        )

        # Call all registered handlers
        for handler in self._order_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(order_data)
                else:
                    handler(order_data)
            except Exception as e:
                print(f"Order handler error: {e}")

        # Check if this is a dry-run
        if order_data.get("is_dry_run", False):
            await self._log_order_event(
                order_data=order_data,
                event_type="dry_run",
                is_dry_run=True,
                success=True
            )
            print(f"[DRY-RUN] Order simulated: {order_data.get('order', {}).get('symbol')} {order_data.get('order', {}).get('transaction_type')} {order_data.get('order', {}).get('quantity')}")
            return

        # If broker is connected, place the order
        if self.broker and self.broker.is_connected:
            await self._place_order(order_data)

    async def _place_order(self, order_data: dict):
        """Place order with broker."""
        order = order_data.get("order", {})
        subscription_id = order_data.get("subscription_id")

        try:
            signal = order.get("signal")
            transaction_type = "BUY" if signal in ["BUY"] else "SELL"

            # Log submission attempt
            await self._log_order_event(
                order_data=order_data,
                event_type="submitted",
                success=None
            )

            broker_request = {
                "symbol": order.get("symbol"),
                "exchange": order.get("exchange", "NSE"),
                "transaction_type": transaction_type,
                "quantity": order.get("quantity"),
                "order_type": order.get("order_type", "MARKET"),
                "price": order.get("price"),
                "trigger_price": order.get("stop_loss"),
            }

            result = await self.broker.place_order(**broker_request)

            print(f"Order placed for {subscription_id}: {result}")

            # Log successful placement
            await self._log_order_event(
                order_data=order_data,
                event_type="placed",
                success=True,
                broker_order_id=result.broker_order_id if hasattr(result, 'broker_order_id') else None,
                broker_request=broker_request,
                broker_response=vars(result) if hasattr(result, '__dict__') else {"result": str(result)}
            )

            # TODO: Update database with order details
            # TODO: Send notification

        except Exception as e:
            print(f"Failed to place order: {e}")

            # Log failure
            await self._log_order_event(
                order_data=order_data,
                event_type="failed",
                success=False,
                error_message=str(e)
            )

    async def connect_broker(self, broker: BaseBroker, credentials: dict) -> bool:
        """Connect to a broker."""
        from brokers.base import BrokerCredentials

        creds = BrokerCredentials(
            api_key=credentials.get("api_key", ""),
            api_secret=credentials.get("api_secret", ""),
            access_token=credentials.get("access_token"),
            client_id=credentials.get("client_id"),
        )

        connected = await broker.connect(creds)
        if connected:
            self.broker = broker
        return connected

    async def start_market_data(self, symbols: List[str]):
        """Start receiving market data for symbols."""
        if not self.broker:
            return

        async def on_quote(quote: MarketQuote):
            # Convert to MarketData format
            data = MarketData(
                symbol=quote.symbol,
                ltp=quote.ltp,
                open=quote.open,
                high=quote.high,
                low=quote.low,
                close=quote.close,
                volume=quote.volume,
                timestamp=quote.timestamp,
                bid=quote.bid,
                ask=quote.ask,
            )

            # Distribute to strategies
            if self._supervisor:
                self._supervisor.distribute_market_data(data)

        await self.broker.subscribe_market_data(symbols, on_quote)

    def get_strategy_status(self, subscription_id: str) -> Optional[dict]:
        """Get status of a strategy."""
        if not self._supervisor:
            return None

        return self._supervisor.get_status(subscription_id)

    def get_all_strategy_status(self) -> List[dict]:
        """Get status of all strategies."""
        if not self._supervisor:
            return []

        return self._supervisor.get_all_status()

    async def get_kill_switch_status(self) -> dict:
        """Get current kill switch status."""
        if not self._kill_switch:
            return {"global": False}

        global_state = await self._kill_switch.get_global_state()

        return {
            "global": global_state.is_active if global_state else False,
            "global_reason": global_state.reason if global_state else None,
            "global_activated_at": global_state.activated_at.isoformat() if global_state else None,
        }

    async def _log_order_event(
        self,
        order_data: dict,
        event_type: str,
        is_dry_run: bool = False,
        success: Optional[bool] = None,
        broker_order_id: Optional[str] = None,
        broker_request: Optional[dict] = None,
        broker_response: Optional[dict] = None,
        error_message: Optional[str] = None
    ):
        """Log order event to database for testing and debugging."""
        if not self.db_session:
            return

        try:
            from app.models.order import OrderLog
            from uuid import UUID

            order = order_data.get("order", {})
            subscription_id = order_data.get("subscription_id")

            # Create log entry
            log_entry = OrderLog(
                subscription_id=UUID(subscription_id) if isinstance(subscription_id, str) else subscription_id,
                order_id=None,  # Will be set when actual Order is created
                symbol=order.get("symbol", ""),
                exchange=order.get("exchange", "NSE"),
                order_type=order.get("order_type", "MARKET"),
                transaction_type=order.get("signal", "BUY"),
                quantity=order.get("quantity", 0),
                price=Decimal(str(order.get("price"))) if order.get("price") else None,
                trigger_price=Decimal(str(order.get("stop_loss"))) if order.get("stop_loss") else None,
                event_type=event_type,
                is_dry_run=is_dry_run,
                is_test_order=order_data.get("is_test_order", False),
                success=success,
                broker_order_id=broker_order_id,
                broker_name=self.broker.name if self.broker else None,
                broker_request=broker_request,
                broker_response=broker_response,
                error_message=error_message,
                strategy_name=order_data.get("strategy_name"),
                reason=order.get("reason"),
                market_price=Decimal(str(order.get("market_price"))) if order.get("market_price") else None,
            )

            self.db_session.add(log_entry)
            await self.db_session.commit()
        except Exception as e:
            print(f"Failed to log order event: {e}")
            # Don't fail the order flow if logging fails
            try:
                await self.db_session.rollback()
            except:
                pass
