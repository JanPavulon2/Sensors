"""
WebSocket handlers for real-time log streaming.

This module provides WebSocket endpoints for streaming application logs
to connected clients in real-time.
"""

import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from utils.logger import get_category_logger, LogCategory
import sys
import traceback

# Get Python logger for internal errors only (avoid infinite recursion)
log = get_category_logger(LogCategory.WEBSOCKET)


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
    broadcaster = None
    client_addr = None
    try:
        # Accept the connection FIRST, before doing anything else
        await websocket.accept()
        client_addr = websocket.client  # Safe to access AFTER accept()
        log.info(f"WebSocket connection accepted from {client_addr}")

        # NOW try to initialize the broadcaster
        log.debug("Initializing broadcaster for log streaming")

        # Lazy import to avoid circular dependency
        from services.log_broadcaster import get_broadcaster

        broadcaster = get_broadcaster()

        if broadcaster is None:
            log.error("Broadcaster is None - WebSocket initialization failed")
            await websocket.close(code=1008, reason="Server initialization error")
            return

        # Register connection with broadcaster's manager (add to active connections)
        log.info(f"WebSocket {client_addr} registered with broadcaster")
        async with broadcaster.manager._lock:
            broadcaster.manager.active_connections.add(websocket)

        log.info(f"Active WebSocket connections: {broadcaster.manager.get_connection_count()}")

        # Keep connection open indefinitely
        # Messages are sent asynchronously by the broadcaster
        while True:
            # This receive just keeps the connection alive and detects disconnects
            # The actual sending happens in the broadcaster's broadcast() method
            try:
                data = await websocket.receive_text()
            except asyncio.CancelledError:
                log.debug("WS cancelled (shutdown)")
                break
            # Ignore any incoming data (this is a one-way stream)

    except WebSocketDisconnect:
        # Client disconnected normally
        log.info(f"WebSocket client {client_addr} disconnected normally")
        if broadcaster:
            await broadcaster.manager.disconnect(websocket)
    except Exception as e:
        # Any other error
        log.error(f"WebSocket error from {client_addr}: {type(e).__name__}: {e}", exc_info=True)
        if broadcaster:
            try:
                await broadcaster.manager.disconnect(websocket)
            except Exception as disconnect_error:
                log.error(f"Error disconnecting after exception: {disconnect_error}")

    