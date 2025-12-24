"""WebSocket endpoints for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.database import get_db
from app.services.websocket_service import websocket_manager
from app.services.auth_service import get_current_user_from_token
from app.models.user import User

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token")
):
    """
    WebSocket endpoint for real-time updates.

    Clients connect with JWT token for authentication.
    Receives platform updates, monitoring status, and notifications.

    Usage:
        ws://localhost:8000/api/ws?token=<jwt_token>
    """
    user = None

    try:
        # Authenticate user from token
        # Note: We can't use Depends here, so we need to validate manually
        from jose import jwt, JWTError
        from app.config import settings

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id = payload.get("sub")

            if user_id is None:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            # Convert to string for connection manager
            user_id_str = str(user_id)

        except JWTError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Connect user
        await websocket_manager.connect(websocket, user_id_str)

        # Send welcome message
        await websocket.send_json({
            "type": "connection_established",
            "message": "WebSocket connected successfully",
            "user_id": user_id_str
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()

                try:
                    message = json.loads(data)
                    message_type = message.get("type")

                    # Handle ping/pong for keepalive
                    if message_type == "ping":
                        await websocket.send_json({"type": "pong"})

                    # Handle subscription requests
                    elif message_type == "subscribe":
                        channel = message.get("channel")
                        await websocket.send_json({
                            "type": "subscribed",
                            "channel": channel,
                            "message": f"Subscribed to {channel}"
                        })

                    # Echo for testing
                    elif message_type == "echo":
                        await websocket.send_json({
                            "type": "echo",
                            "data": message.get("data")
                        })

                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON"
                    })

            except WebSocketDisconnect:
                break

    except Exception as e:
        print(f"WebSocket error: {e}")

    finally:
        # Disconnect user
        if websocket in websocket_manager.connection_metadata:
            websocket_manager.disconnect(websocket)


@router.get("/ws/status")
async def get_websocket_status(
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Get WebSocket connection status.

    Returns information about active connections.
    """
    user_id_str = str(current_user.id)

    return {
        "total_connections": websocket_manager.get_connection_count(),
        "user_connections": websocket_manager.get_user_connection_count(user_id_str),
        "is_connected": websocket_manager.is_user_connected(user_id_str),
        "active_users_count": len(websocket_manager.get_active_users())
    }


@router.post("/ws/broadcast/test")
async def test_broadcast(
    message: str,
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Test endpoint to send message to user's WebSocket connections.

    For testing real-time updates.
    """
    user_id_str = str(current_user.id)

    if not websocket_manager.is_user_connected(user_id_str):
        return JSONResponse(
            status_code=400,
            content={"detail": "User has no active WebSocket connections"}
        )

    await websocket_manager.send_notification(
        user_id_str,
        {
            "title": "Test Notification",
            "message": message,
            "level": "info"
        }
    )

    return {
        "success": True,
        "message": "Broadcast sent",
        "recipients": websocket_manager.get_user_connection_count(user_id_str)
    }


@router.post("/ws/notify")
async def send_notification(
    title: str,
    message: str,
    level: str = "info",
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Send notification to user via WebSocket.

    Args:
        title: Notification title
        message: Notification message
        level: Notification level (info, success, warning, error)
    """
    user_id_str = str(current_user.id)

    if not websocket_manager.is_user_connected(user_id_str):
        return JSONResponse(
            status_code=200,
            content={"detail": "User not connected, notification queued"}
        )

    await websocket_manager.send_notification(
        user_id_str,
        {
            "title": title,
            "message": message,
            "level": level
        }
    )

    return {
        "success": True,
        "delivered_to": websocket_manager.get_user_connection_count(user_id_str)
    }
