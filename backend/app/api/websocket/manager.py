"""
WebSocket connection manager for handling real-time updates.
"""

from typing import Dict, List, Set, Optional
from fastapi import WebSocket
import asyncio
import json


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Supports:
    - User-specific connections (portfolio updates)
    - Topic-based subscriptions (market data)
    """

    def __init__(self):
        # User connections: user_id -> list of websockets
        self.user_connections: Dict[str, List[WebSocket]] = {}

        # Topic subscriptions: topic -> set of websockets
        self.topic_subscriptions: Dict[str, Set[WebSocket]] = {}

        # WebSocket to user mapping for cleanup
        self.websocket_to_user: Dict[WebSocket, str] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection for a user."""
        await websocket.accept()

        async with self._lock:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
            self.websocket_to_user[websocket] = user_id

    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection."""
        async with self._lock:
            # Remove from user connections
            user_id = self.websocket_to_user.get(websocket)
            if user_id and user_id in self.user_connections:
                if websocket in self.user_connections[user_id]:
                    self.user_connections[user_id].remove(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]

            # Remove from topic subscriptions
            for topic in list(self.topic_subscriptions.keys()):
                if websocket in self.topic_subscriptions[topic]:
                    self.topic_subscriptions[topic].discard(websocket)
                if not self.topic_subscriptions[topic]:
                    del self.topic_subscriptions[topic]

            # Clean up mapping
            if websocket in self.websocket_to_user:
                del self.websocket_to_user[websocket]

    async def subscribe_to_topic(self, websocket: WebSocket, topic: str):
        """Subscribe a WebSocket to a topic."""
        async with self._lock:
            if topic not in self.topic_subscriptions:
                self.topic_subscriptions[topic] = set()
            self.topic_subscriptions[topic].add(websocket)

    async def unsubscribe_from_topic(self, websocket: WebSocket, topic: str):
        """Unsubscribe a WebSocket from a topic."""
        async with self._lock:
            if topic in self.topic_subscriptions:
                self.topic_subscriptions[topic].discard(websocket)
                if not self.topic_subscriptions[topic]:
                    del self.topic_subscriptions[topic]

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all connections of a user."""
        if user_id not in self.user_connections:
            return

        disconnected = []
        for websocket in self.user_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_to_topic(self, topic: str, message: dict):
        """Broadcast a message to all subscribers of a topic."""
        if topic not in self.topic_subscriptions:
            return

        disconnected = []
        for websocket in self.topic_subscriptions[topic]:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected users."""
        all_websockets = set()
        for connections in self.user_connections.values():
            all_websockets.update(connections)

        disconnected = []
        for websocket in all_websockets:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(ws)

    def get_user_connection_count(self, user_id: str) -> int:
        """Get the number of active connections for a user."""
        return len(self.user_connections.get(user_id, []))

    def get_topic_subscriber_count(self, topic: str) -> int:
        """Get the number of subscribers for a topic."""
        return len(self.topic_subscriptions.get(topic, set()))

    def get_total_connections(self) -> int:
        """Get the total number of active connections."""
        return sum(len(conns) for conns in self.user_connections.values())


# Global connection manager instance
manager = ConnectionManager()
