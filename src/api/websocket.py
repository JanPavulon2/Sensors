"""
WebSocket handlers for real-time log streaming.

This module provides WebSocket endpoints for streaming application logs
to connected clients in real-time.
"""

from fastapi import WebSocket, WebSocketDisconnect
from services.log_broadcaster import get_broadcaster
import logging

# Get Python logger for internal errors only (avoid infinite recursion)
logger = logging.getLogger(__name__)


async def websocket_logs_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming logs in real-time.

    Clients connect to this endpoint to receive a stream of log messages
    as they occur in the application. Each message is a JSON object with:
    - timestamp: ISO 8601 timestamp
    - level: Log level (DEBUG, INFO, WARN, ERROR)
    - category: Log category (ZONE, COLOR, etc.)
    - message: Log message text

    Example message:
    {
        "timestamp": "2025-11-27T14:30:45.123456",
        "level": "INFO",
        "category": "ZONE",
        "message": "Zone FLOOR selected"
    }

    Args:
        websocket: The WebSocket connection

    Behavior:
    - Client connects and registers with ConnectionManager
    - Receives all subsequent log messages until disconnect
    - Automatically handles reconnection from frontend
    - No authentication required (can be added later)
    """
    broadcaster = get_broadcaster()

    try:
        # Register connection with broadcaster
        await broadcaster.manager.connect(websocket)

        # Keep connection open indefinitely
        # Messages are sent asynchronously by the broadcaster
        while True:
            # This receive just keeps the connection alive and detects disconnects
            # The actual sending happens in the broadcaster's broadcast() method
            data = await websocket.receive_text()
            # Ignore any incoming data (this is a one-way stream)

    except WebSocketDisconnect:
        # Client disconnected normally
        await broadcaster.manager.disconnect(websocket)
    except Exception as e:
        # Any other error
        logger.error(f"WebSocket error: {e}")
        try:
            await broadcaster.manager.disconnect(websocket)
        except Exception:
            pass
