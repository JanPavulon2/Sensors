"""
Socket.IO Server Handler

Manages real-time bidirectional communication with web clients.
Handles zone state changes, animation events, and system updates.

Usage:
    from api.socketio_handler import create_socketio_server, socketio_handler

    socketio_server = create_socketio_server()
    # Register handlers
    socketio_handler.setup_event_handlers(socketio_server, services)

    # In FastAPI app:
    from socketio import ASGIApp
    app = FastAPI(...)
    app = ASGIApp(socketio_server, app)
"""

from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict
from socketio import AsyncServer, ASGIApp
from models.domain import ZoneCombined
from models.events import (
    EventType,
    ZoneStateChangedEvent
)
from services.event_bus import EventBus
from services.service_container import ServiceContainer
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SOCKETIO)



class SocketIOHandler:
    """Manages Socket.IO server and event handling"""

    def __init__(self):
        self.socketio_server: Optional[AsyncServer] = None
        self.services: Optional[ServiceContainer] = None
        
    async def setup(self, socketio_server: AsyncServer, services: ServiceContainer) -> None:
        self.socketio_server = socketio_server
        self.services = services

        # Subscribe to backend EventBus events
        self._subscribe_to_events()
        
        # Register Socket.IO client event handlers
        self._register_connection_handlers()

        log.info("Socket.IO ready")

    def _subscribe_to_events(self) -> None:
        """Subscribe to backend EventBus events for broadcasting"""
        if not self.services or not self.services.event_bus:
            log.warn("EventBus not available for Socket.IO")
            return

        event_bus: EventBus = self.services.event_bus

        # Subscribe to zone state changes
        # Note: EventBus.subscribe() supports async handlers despite type hint saying otherwise
        event_bus.subscribe(
            EventType.ZONE_STATE_CHANGED,
            self._on_zone_state_changed  # type: ignore
        )

        log.info("Socket.IO subscribed to EventBus events")

    def _register_connection_handlers(self) -> None:
        """Register client-side event handlers"""
        
        if not self.socketio_server:
            return
        
        if not self.services or not self.services.zone_service:
            return
        
        socketio_server = self.socketio_server
         
        @socketio_server.event
        async def connect(sid, environ, auth=None):
            """Handle client connection and send initial state"""
            client_ip = environ.get('REMOTE_ADDR', 'unknown')
            log.info(f"Client connected: {sid} from {client_ip}")

            # Guard: ensure services are available
            if not self.services or not self.services.zone_service:
                log.warn(f"Skipping initial zone snapshot for {sid}: services not ready")
                return

            zones = self.services.zone_service.get_all()
            snapshots = [
                asdict(ZoneSnapshotDTO.from_zone(z))
                for z in zones
            ]

            await socketio_server.emit("zones.snapshot", snapshots, room=sid)

        @socketio_server.event
        async def disconnect(sid):
            log.info(f"Client disconnected: {sid}")
            
        # Task monitoring commands
        @socketio_server.event
        async def task_get_all(sid: str) -> None:
            """Client command: Get all tasks"""
            try:
                from lifecycle.task_registry import TaskRegistry
                registry = TaskRegistry.instance()
                tasks = registry.get_all_as_dicts()
                await socketio_server.emit('tasks:all', {'tasks': tasks}, room=sid)
            except Exception as e:
                log.error(f"Error getting all tasks: {e}", exc_info=True)
                await socketio_server.emit('error', {'message': str(e)}, room=sid)

        @socketio_server.event
        async def task_get_active(sid: str) -> None:
            """Client command: Get active tasks"""
            try:
                from lifecycle.task_registry import TaskRegistry
                registry = TaskRegistry.instance()
                tasks = registry.get_active_as_dicts()
                await socketio_server.emit('tasks:active', {'tasks': tasks}, room=sid)
            except Exception as e:
                log.error(f"Error getting active tasks: {e}")
                await socketio_server.emit('error', {'message': str(e)}, room=sid)

        @socketio_server.event
        async def task_get_stats(sid: str) -> None:
            """Client command: Get task statistics"""
            try:
                from lifecycle.task_registry import TaskRegistry
                registry = TaskRegistry.instance()
                stats = registry.get_stats()
                await socketio_server.emit('tasks:stats', {'stats': stats}, room=sid)
            except Exception as e:
                log.error(f"Error getting task stats: {e}", exc_info=True)
                await socketio_server.emit('error', {'message': str(e)}, room=sid)

        @socketio_server.event
        async def task_get_tree(sid: str) -> None:
            """Client command: Get task tree"""
            try:
                from lifecycle.task_registry import TaskRegistry
                registry = TaskRegistry.instance()
                tree = registry.get_task_tree()
                await socketio_server.emit('tasks:tree', {'tree': tree}, room=sid)
            except Exception as e:
                log.error(f"Error getting task tree: {e}")
                await socketio_server.emit('error', {'message': str(e)}, room=sid)

        # Log history command
        @socketio_server.event
        async def logs_request_history(sid: str, data: dict) -> None:
            """Client command: Request recent log history"""
            try:
                from services.log_broadcaster import get_broadcaster

                limit = data.get('limit', 100)
                broadcaster = get_broadcaster()
                logs = broadcaster.get_recent_logs(limit)

                # Convert LogMessage objects to dicts for Socket.IO
                log_dicts = [log.model_dump() for log in logs]

                await socketio_server.emit('logs:history', {'logs': log_dicts}, room=sid)
            except Exception as e:
                log.error(f"Error getting log history: {e}")
                await socketio_server.emit('error', {'message': str(e)}, room=sid)

        log.info("Client event handlers registered (zones, animations, tasks, logs)")

    async def _on_zone_state_changed(self, event: ZoneStateChangedEvent) -> None:
        """EventBus handler: Broadcast zone state change to all clients"""
        if not self.socketio_server:
            return
        
        if self.services is None or self.services.zone_service is None:
            return
            
        zone = self.services.zone_service.get_zone(event.zone_id)
        payload = ZoneSnapshotDTO.from_zone(zone)

        await self.socketio_server.emit("zone.snapshot", asdict(payload))

        # await self.socketio_server.emit('zone:state_changed', payload)
        log.debug(f"Emitted zone snapshot: {zone.config.id.name}")


# Global instance
socketio_handler = SocketIOHandler()


def create_socketio_server(cors_origins: Optional[list[str]] = None) -> AsyncServer:
    """
    Create and configure a Socket.IO AsyncServer.

    Args:
        cors_origins: CORS allowed origins for WebSocket connections

    Returns:
        Configured AsyncServer instance
    """
    if cors_origins is None:
        cors_origins = [
            "http://192.168.137.139:3000",
            "http://192.168.137.139:8000",
            "http://192.168.137.139:5173",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:5173",
        ]

    # Setup Socket.IO logging to use Diuna logger
    # from utils.socketio_logger import setup_socketio_logging
    # setup_socketio_logging()

    socketio_server = AsyncServer(
        async_mode='asgi',
        cors_allowed_origins=cors_origins,
        ping_timeout=60,
        ping_interval=25,
        logger=False,  
        engineio_logger=False,  
    )

    log.info(f"Socket.IO server created with CORS origins: {cors_origins}")

    return socketio_server


def wrap_app_with_socketio(app, socketio_server: AsyncServer):
    """
    Wrap FastAPI app with Socket.IO ASGI middleware.

    This makes the app handle both HTTP (FastAPI) and WebSocket (Socket.IO) requests.

    Args:
        app: FastAPI application instance
        socketio_server: AsyncServer instance

    Returns:
        ASGIApp wrapping FastAPI with Socket.IO
    """
    return ASGIApp(socketio_server, app)
