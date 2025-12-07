"""
WebSocket handlers for real-time task monitoring.

This module provides WebSocket endpoints for streaming task lifecycle events
and status updates to connected clients in real-time.
"""

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
import logging
from typing import Set

# Get Python logger for internal errors only
logger = logging.getLogger(__name__)

# Track active task WebSocket connections
_active_task_websockets: Set[WebSocket] = set()
_websocket_lock = asyncio.Lock()


async def broadcast_task_update(event_type: str, task_data: dict) -> None:
    """
    Broadcast a task update to all connected WebSocket clients.

    Args:
        event_type: Type of event (task:created, task:updated, task:completed, etc.)
        task_data: Task data dictionary to broadcast
    """
    message = {
        "type": event_type,
        "task": task_data,
    }

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
    print("[WEBSOCKET_TASKS] Handler called - about to accept connection")  # DEBUG: Visible output
    try:
        # Accept the connection FIRST
        print("[WEBSOCKET_TASKS] Calling websocket.accept()")  # DEBUG
        await websocket.accept()
        print("[WEBSOCKET_TASKS] Connection accepted successfully")  # DEBUG
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

        try:
            # Send initial task snapshot
            logger.debug(f"Getting stats from registry for {client_addr}")
            stats = registry.get_stats()
            logger.debug(f"Got stats: {type(stats)}, keys: {list(stats.keys()) if isinstance(stats, dict) else 'N/A'}")

            logger.debug(f"Sending stats to {client_addr}")
            await websocket.send_json({
                "type": "tasks:stats",
                "stats": stats,
            })
            logger.debug(f"Sent task stats to {client_addr}")

            # Send all tasks
            logger.debug(f"Getting all tasks from registry for {client_addr}")
            all_tasks = registry.get_all_as_dicts()
            logger.debug(f"Got {len(all_tasks)} tasks, sending to {client_addr}")

            await websocket.send_json({
                "type": "tasks:snapshot",
                "tasks": all_tasks,
            })
            logger.debug(f"Sent {len(all_tasks)} tasks to {client_addr}")
        except WebSocketDisconnect:
            logger.debug(f"Client {client_addr} disconnected during initial data send")
            return
        except Exception as e:
            logger.error(f"Error sending initial data to {client_addr}: {e}", exc_info=True)
            try:
                await websocket.close(code=1011, reason="Error sending initial data")
            except Exception as close_err:
                logger.debug(f"Could not close socket: {close_err}")
            return

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
                logger.warning(f"Invalid JSON from {client_addr}: {data}")
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
        logger.warning(f"Unknown task command: {cmd}")
