"""
Log broadcasting service for WebSocket and Socket.IO streaming.

This module provides real-time log streaming to connected WebSocket clients
and Socket.IO connections. Maintains a connection pool and broadcasts log
messages asynchronously through both protocols.
"""

import asyncio
import json
from typing import List, Set, Optional, TYPE_CHECKING
from datetime import datetime
from fastapi import WebSocket
from utils.logger import get_logger, LogCategory
from api.schemas.logger import LogMessage
from lifecycle.task_registry import create_tracked_task, TaskCategory

if TYPE_CHECKING:
    from socketio import AsyncServer

log = get_logger().for_category(LogCategory.RENDER_ENGINE)

class ConnectionManager:
    """Manages WebSocket connections for log streaming."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """
        Add a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to add
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
        """
        async with self._lock:
            self.active_connections.discard(websocket)

    async def broadcast(self, message: LogMessage) -> None:
        """
        Send a log message to all connected clients.

        Handles disconnected clients gracefully without blocking
        on slow connections.

        Args:
            message: LogMessage to broadcast
        """
        message_json = message.model_dump_json()

        async with self._lock:
            # Create copy to iterate safely
            connections = list(self.active_connections)

        # Send to all connections without holding lock
        disconnected = []
        for connection in connections:
            try:
                await asyncio.wait_for(
                    connection.send_text(message_json),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                # Connection too slow, mark for removal
                disconnected.append(connection)
            except Exception:
                # Connection broken, mark for removal
                disconnected.append(connection)

        # Clean up disconnected connections
        if disconnected:
            async with self._lock:
                for connection in disconnected:
                    self.active_connections.discard(connection)

    def get_connection_count(self) -> int:
        """
        Get the number of active connections.

        Returns:
            Number of connected WebSocket clients
        """
        return len(self.active_connections)


class LogBroadcaster:
    """
    Service for broadcasting logs to WebSocket and Socket.IO clients.

    Decouples the logger from transport by using an asyncio queue.
    This allows the logger to remain fast and non-blocking while logs are
    streamed asynchronously to connected clients via WebSocket and/or Socket.IO.
    """

    def __init__(self, queue_size: int = 1000) -> None:
        """
        Initialize the log broadcaster.

        Args:
            queue_size: Maximum size of the log queue
        """
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self.manager = ConnectionManager()
        self._broadcast_task: asyncio.Task | None = None
        self.socketio_server: Optional["AsyncServer"] = None

    def set_socketio_server(self, socketio_server: "AsyncServer") -> None:
        """
        Set the Socket.IO server for broadcasting logs.

        Args:
            socketio_server: The Socket.IO AsyncServer instance
        """
        self.socketio_server = socketio_server
        log.debug("Socket.IO server registered with LogBroadcaster")

    def start(self) -> None:
        """Start the background broadcasting task."""
        if self._broadcast_task is None:
            self._broadcast_task = create_tracked_task(
                self._broadcast_worker(),
                category=TaskCategory.SYSTEM,
                description="LogBroadcaster: Log broadcasting worker (WebSocket + Socket.IO)"
            )

    async def stop(self) -> None:
        """Stop the background broadcasting task."""
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
            self._broadcast_task = None

    def log(
        self,
        timestamp: str,
        level: str,
        category: str,
        message: str
    ) -> None:
        """
        Queue a log message for broadcasting.

        Non-blocking: logs dropped if queue is full rather than blocking.

        Args:
            timestamp: ISO 8601 timestamp
            level: Log level (DEBUG, INFO, WARN, ERROR)
            category: Log category
            message: Log message text
        """
        log_msg = LogMessage(
            timestamp=timestamp,
            level=level,
            category=category,
            message=message
        )

        try:
            # Non-blocking put - drop oldest message if queue full
            self.queue.put_nowait(log_msg)
        except asyncio.QueueFull:
            # Queue full, try to remove oldest and add new
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(log_msg)
            except asyncio.QueueEmpty:
                pass

    async def _broadcast_worker(self) -> None:
        """
        Background task that consumes logs and broadcasts to clients.

        Runs continuously and broadcasts each log to all connected clients
        via WebSocket and/or Socket.IO.
        """
        while True:
            try:
                message = await self.queue.get()

                # Broadcast via WebSocket (legacy, can be removed later)
                await self.manager.broadcast(message)

                # Broadcast via Socket.IO (primary method)
                if self.socketio_server:
                    try:
                        # Convert LogMessage to dict for Socket.IO emission
                        log_data = message.model_dump()
                        await self.socketio_server.emit('log:entry', log_data)
                    except Exception as sio_err:
                        log.error(f"Error broadcasting log via Socket.IO: {sio_err}")
                        # Continue processing even if Socket.IO fails

            except asyncio.CancelledError:
                break
            except Exception as ex:
                log.error(f"Error when broadcasting log message: {ex}")
                # Log error internally (avoid infinite recursion)
                # Just continue processing
                pass


# Global singleton instance
_broadcaster: LogBroadcaster | None = None


def get_broadcaster() -> LogBroadcaster:
    """
    Get or create the global LogBroadcaster instance.

    Returns:
        The LogBroadcaster singleton
    """
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = LogBroadcaster()
    return _broadcaster


def set_broadcaster(broadcaster: LogBroadcaster) -> None:
    """
    Set the global LogBroadcaster instance.

    Useful for testing or custom initialization.

    Args:
        broadcaster: The LogBroadcaster instance to set globally
    """
    global _broadcaster
    _broadcaster = broadcaster