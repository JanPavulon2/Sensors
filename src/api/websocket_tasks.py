"""
WebSocket and Socket.IO handlers for real-time task monitoring.

This module provides WebSocket and Socket.IO endpoints for streaming task lifecycle events
and status updates to connected clients in real-time.
"""

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
from typing import Set, Optional, TYPE_CHECKING
from utils.logger import get_category_logger, LogCategory

if TYPE_CHECKING:
    from socketio import AsyncServer

# Get Python logger for internal errors only
logger = get_category_logger(LogCategory.WEBSOCKET)

# Track active task WebSocket connections
_active_task_websockets: Set[WebSocket] = set()
_websocket_lock = asyncio.Lock()

# Socket.IO server instance (optional, for event broadcasting)
_socketio_server: Optional["AsyncServer"] = None


def set_socketio_server(socketio_server: "AsyncServer") -> None:
    """
    Set the Socket.IO server for broadcasting task events.

    Args:
        socketio_server: The Socket.IO AsyncServer instance
    """
    global _socketio_server
    _socketio_server = socketio_server
    logger.debug("Socket.IO server registered with task handler")


async def broadcast_task_update(event_type: str, task_data: dict) -> None:
    """
    Broadcast a task update to all connected clients (WebSocket and/or Socket.IO).

    Args:
        event_type: Type of event (task:created, task:updated, task:completed, etc.)
        task_data: Task data dictionary to broadcast
    """
    message = {
        "type": event_type,
        "task": task_data,
    }

    # Broadcast via WebSocket (legacy, can be removed later)
    disconnected = set()

    async with _websocket_lock:
        for websocket in _active_task_websockets:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.debug(f"Error sending to task WebSocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            _active_task_websockets.discard(ws)

    # Broadcast via Socket.IO (primary method)
    if _socketio_server:
        try:
            # Convert message to Socket.IO format: event name + data payload
            await _socketio_server.emit(event_type, message.get("task", {}))
        except Exception as e:
            logger.error(f"Error broadcasting task update via Socket.IO: {e}")


async def websocket_tasks_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time task monitoring.

    Clients connect to this endpoint to receive a stream of task lifecycle events:
    - task:created - New task registered
    - task:updated - Task status changed
    - task:completed - Task finished successfully
    - task:failed - Task failed with error
    - task:cancelled - Task was cancelled

    Clients can send commands to query task state:
    - {"command": "get_all"} - Get all tasks
    - {"command": "get_active"} - Get only running tasks
    - {"command": "get_stats"} - Get task statistics

    Example message received:
    {
        "type": "task:created",
        "task": {
            "id": 1,
            "category": "RENDER",
            "description": "Frame Manager render loop",
            "created_at": "2025-12-07T12:34:56.789Z",
            "status": "running",
            ...
        }
    }

    Args:
        websocket: The WebSocket connection
    """
    client_addr = None
    registry = None
    try:
        # Accept the connection
        await websocket.accept()
        client_addr = websocket.client
        logger.info(f"Task WebSocket connection accepted from {client_addr}")

        # Register connection
        async with _websocket_lock:
            _active_task_websockets.add(websocket)

        logger.info(f"Active task WebSocket connections: {len(_active_task_websockets)}")

        # Get task registry
        try:
            from lifecycle.task_registry import TaskRegistry
            registry = TaskRegistry.instance()
            logger.debug("TaskRegistry imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import TaskRegistry: {e}")
            await websocket.close(code=1011, reason="Server initialization error")
            return

        # Client will request data via commands - don't auto-send initial data
        # This avoids timeout issues when preparing large snapshots

        # Keep connection open and handle incoming commands
        while True:
            try:
                data = await websocket.receive_text()
                command = json.loads(data)
                await _handle_task_command(websocket, command, registry)
            except WebSocketDisconnect:
                # Proper disconnect - re-raise to outer handler
                raise
            except json.JSONDecodeError:
                logger.warn(f"Invalid JSON from {client_addr}: {data}")
            except RuntimeError as e:
                # RuntimeError is raised when trying to receive after disconnect message
                if "disconnect message" in str(e).lower():
                    logger.debug(f"Task WebSocket client {client_addr} disconnected (RuntimeError)")
                    break
                logger.error(f"Task WebSocket RuntimeError from {client_addr}: {e}")
                break
            except Exception as e:
                logger.error(f"Error handling task command from {client_addr}: {e}", exc_info=True)
                break

    except WebSocketDisconnect:
        logger.info(f"Task WebSocket client {client_addr} disconnected normally")
        async with _websocket_lock:
            _active_task_websockets.discard(websocket)
    except Exception as e:
        logger.error(f"Task WebSocket error from {client_addr}: {type(e).__name__}: {e}", exc_info=True)
        async with _websocket_lock:
            _active_task_websockets.discard(websocket)


async def _handle_task_command(
    websocket: WebSocket,
    command: dict,
    registry: "TaskRegistry"
) -> None:
    """
    Handle incoming task commands from client.

    Args:
        websocket: The WebSocket connection
        command: Command dictionary with "command" key
        registry: TaskRegistry instance
    """
    from lifecycle.task_registry import TaskRegistry

    cmd = command.get("command")

    if cmd == "get_all":
        tasks = registry.get_all_as_dicts()
        await websocket.send_json({
            "type": "tasks:all",
            "tasks": tasks,
        })

    elif cmd == "get_active":
        tasks = registry.get_active_as_dicts()
        await websocket.send_json({
            "type": "tasks:active",
            "tasks": tasks,
        })

    elif cmd == "get_stats":
        stats = registry.get_stats()
        await websocket.send_json({
            "type": "tasks:stats",
            "stats": stats,
        })

    elif cmd == "get_tree":
        tree = registry.get_task_tree()
        await websocket.send_json({
            "type": "tasks:tree",
            "tree": tree,
        })

    else:
        logger.warn(f"Unknown task command: {cmd}")
