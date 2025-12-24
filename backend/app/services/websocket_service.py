"""WebSocket service for real-time updates."""

from fastapi import WebSocket
from typing import Dict, List, Set
from uuid import UUID
import json
from datetime import datetime


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        """Initialize connection manager."""
        # Store active connections by user_id
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, user_id: str, client_info: dict = None):
        """
        Accept and register new WebSocket connection.

        Args:
            websocket: WebSocket connection
            user_id: User identifier
            client_info: Optional client metadata
        """
        await websocket.accept()

        # Add to user's connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)

        # Store metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
            "client_info": client_info or {}
        }

        print(f"📡 WebSocket connected: user={user_id}, total_connections={self.get_connection_count()}")

    def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        # Get user_id from metadata
        metadata = self.connection_metadata.get(websocket, {})
        user_id = metadata.get("user_id")

        if user_id and user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)

            # Clean up empty user entries
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # Remove metadata
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]

        print(f"📡 WebSocket disconnected: user={user_id}, total_connections={self.get_connection_count()}")

    async def send_personal_message(self, message: dict, user_id: str):
        """
        Send message to specific user's connections.

        Args:
            message: Message data (will be JSON serialized)
            user_id: Target user identifier
        """
        if user_id in self.active_connections:
            disconnected = []

            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending to user {user_id}: {e}")
                    disconnected.append(connection)

            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)

    async def broadcast_to_user(self, message: dict, user_id: str):
        """
        Broadcast message to all of user's active connections.

        Alias for send_personal_message for clarity.

        Args:
            message: Message data
            user_id: Target user identifier
        """
        await self.send_personal_message(message, user_id)

    async def send_platform_update(self, user_id: str, platform: str, data: dict):
        """
        Send platform-specific update to user.

        Args:
            user_id: Target user identifier
            platform: Platform name (twitter, youtube, reddit, twitch)
            data: Update data
        """
        message = {
            "type": "platform_update",
            "platform": platform,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        await self.broadcast_to_user(message, user_id)

    async def send_monitoring_update(self, user_id: str, entity_type: str, entity_id: str, status: dict):
        """
        Send monitoring status update.

        Args:
            user_id: Target user identifier
            entity_type: Type of entity (channel, user, subreddit, etc.)
            entity_id: Entity identifier
            status: Status data
        """
        message = {
            "type": "monitoring_update",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status
        }
        await self.broadcast_to_user(message, user_id)

    async def send_analytics_update(self, user_id: str, analytics_type: str, data: dict):
        """
        Send analytics update.

        Args:
            user_id: Target user identifier
            analytics_type: Type of analytics (engagement, sentiment, etc.)
            data: Analytics data
        """
        message = {
            "type": "analytics_update",
            "analytics_type": analytics_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        await self.broadcast_to_user(message, user_id)

    async def send_notification(self, user_id: str, notification: dict):
        """
        Send notification to user.

        Args:
            user_id: Target user identifier
            notification: Notification data (title, message, level)
        """
        message = {
            "type": "notification",
            "timestamp": datetime.utcnow().isoformat(),
            "notification": notification
        }
        await self.broadcast_to_user(message, user_id)

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    def get_user_connection_count(self, user_id: str) -> int:
        """
        Get number of active connections for user.

        Args:
            user_id: User identifier

        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(user_id, []))

    def get_active_users(self) -> List[str]:
        """
        Get list of users with active connections.

        Returns:
            List of user identifiers
        """
        return list(self.active_connections.keys())

    def is_user_connected(self, user_id: str) -> bool:
        """
        Check if user has any active connections.

        Args:
            user_id: User identifier

        Returns:
            True if user has active connections
        """
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


# Global connection manager instance
websocket_manager = ConnectionManager()
