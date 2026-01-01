"""
Kill Switch - Emergency stop mechanism for all trading activities.

This module provides a global and per-user/strategy kill switch that can
immediately halt all trading when activated.
"""

import redis.asyncio as redis
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
import json


@dataclass
class KillSwitchState:
    """State of a kill switch."""
    is_active: bool
    reason: str
    activated_by: str
    activated_at: datetime
    scope: str  # global, user, strategy


class KillSwitch:
    """
    Kill switch for emergency trading halt.

    Provides three levels of control:
    - Global: Stop ALL trading across the platform
    - User: Stop all trading for a specific user
    - Strategy: Stop a specific strategy subscription

    Uses Redis for fast distributed state management.
    """

    GLOBAL_KEY = "killswitch:global"
    USER_KEY_PREFIX = "killswitch:user:"
    STRATEGY_KEY_PREFIX = "killswitch:strategy:"
    CHANNEL = "killswitch:events"

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def activate_global(
        self,
        reason: str,
        activated_by: str,
    ) -> None:
        """
        Activate global kill switch - stops ALL trading.

        Args:
            reason: Reason for activation
            activated_by: User/system that activated (user_id or 'system')
        """
        state = {
            "active": True,
            "reason": reason,
            "activated_by": activated_by,
            "activated_at": datetime.utcnow().isoformat(),
            "scope": "global",
        }

        await self.redis.hset(self.GLOBAL_KEY, mapping={
            k: json.dumps(v) if isinstance(v, bool) else str(v)
            for k, v in state.items()
        })

        # Publish event for real-time notification
        await self.redis.publish(
            self.CHANNEL,
            json.dumps({
                "type": "GLOBAL_STOP",
                "reason": reason,
                "activated_by": activated_by,
            })
        )

    async def deactivate_global(self, deactivated_by: str) -> None:
        """Deactivate global kill switch."""
        await self.redis.delete(self.GLOBAL_KEY)
        await self.redis.publish(
            self.CHANNEL,
            json.dumps({
                "type": "GLOBAL_RESUME",
                "deactivated_by": deactivated_by,
            })
        )

    async def activate_for_user(
        self,
        user_id: str,
        reason: str,
        activated_by: str = "system",
    ) -> None:
        """
        Activate kill switch for a specific user.

        Args:
            user_id: User to stop trading for
            reason: Reason for activation
            activated_by: Who activated (admin_id or 'system')
        """
        key = f"{self.USER_KEY_PREFIX}{user_id}"

        await self.redis.hset(key, mapping={
            "active": "true",
            "reason": reason,
            "activated_by": activated_by,
            "activated_at": datetime.utcnow().isoformat(),
        })

        await self.redis.publish(
            self.CHANNEL,
            json.dumps({
                "type": "USER_STOP",
                "user_id": user_id,
                "reason": reason,
            })
        )

    async def deactivate_for_user(self, user_id: str) -> None:
        """Deactivate kill switch for a user."""
        key = f"{self.USER_KEY_PREFIX}{user_id}"
        await self.redis.delete(key)

        await self.redis.publish(
            self.CHANNEL,
            json.dumps({
                "type": "USER_RESUME",
                "user_id": user_id,
            })
        )

    async def activate_for_strategy(
        self,
        subscription_id: str,
        reason: str,
        activated_by: str = "system",
    ) -> None:
        """
        Activate kill switch for a specific strategy subscription.

        Args:
            subscription_id: Strategy subscription to stop
            reason: Reason for activation
            activated_by: Who activated
        """
        key = f"{self.STRATEGY_KEY_PREFIX}{subscription_id}"

        await self.redis.hset(key, mapping={
            "active": "true",
            "reason": reason,
            "activated_by": activated_by,
            "activated_at": datetime.utcnow().isoformat(),
        })

        await self.redis.publish(
            self.CHANNEL,
            json.dumps({
                "type": "STRATEGY_STOP",
                "subscription_id": subscription_id,
                "reason": reason,
            })
        )

    async def deactivate_for_strategy(self, subscription_id: str) -> None:
        """Deactivate kill switch for a strategy."""
        key = f"{self.STRATEGY_KEY_PREFIX}{subscription_id}"
        await self.redis.delete(key)

    async def is_global_active(self) -> bool:
        """Check if global kill switch is active."""
        active = await self.redis.hget(self.GLOBAL_KEY, "active")
        return active == "true"

    async def is_user_active(self, user_id: str) -> bool:
        """Check if kill switch is active for a user."""
        # Check global first
        if await self.is_global_active():
            return True

        key = f"{self.USER_KEY_PREFIX}{user_id}"
        active = await self.redis.hget(key, "active")
        return active == "true"

    async def is_strategy_active(self, subscription_id: str, user_id: str) -> bool:
        """Check if kill switch is active for a strategy."""
        # Check global first
        if await self.is_global_active():
            return True

        # Check user-level
        if await self.is_user_active(user_id):
            return True

        # Check strategy-level
        key = f"{self.STRATEGY_KEY_PREFIX}{subscription_id}"
        active = await self.redis.hget(key, "active")
        return active == "true"

    async def get_global_state(self) -> Optional[KillSwitchState]:
        """Get global kill switch state."""
        data = await self.redis.hgetall(self.GLOBAL_KEY)

        if not data:
            return None

        return KillSwitchState(
            is_active=data.get("active") == "true",
            reason=data.get("reason", ""),
            activated_by=data.get("activated_by", ""),
            activated_at=datetime.fromisoformat(data.get("activated_at", datetime.utcnow().isoformat())),
            scope="global",
        )

    async def get_user_state(self, user_id: str) -> Optional[KillSwitchState]:
        """Get user-level kill switch state."""
        key = f"{self.USER_KEY_PREFIX}{user_id}"
        data = await self.redis.hgetall(key)

        if not data:
            return None

        return KillSwitchState(
            is_active=data.get("active") == "true",
            reason=data.get("reason", ""),
            activated_by=data.get("activated_by", ""),
            activated_at=datetime.fromisoformat(data.get("activated_at", datetime.utcnow().isoformat())),
            scope=f"user:{user_id}",
        )

    async def subscribe_events(self, callback):
        """
        Subscribe to kill switch events.

        Args:
            callback: Async function to call on each event
        """
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.CHANNEL)

        async for message in pubsub.listen():
            if message["type"] == "message":
                event = json.loads(message["data"])
                await callback(event)
