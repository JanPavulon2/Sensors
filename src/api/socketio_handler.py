"""
Socket.IO Server Handler

Manages real-time bidirectional communication with web clients.
Handles zone state changes, animation events, and system updates.

Usage:
    from api.socketio_handler import create_socketio_server, socketio_handler

    sio = create_socketio_server()
    # Register handlers
    socketio_handler.setup_event_handlers(sio, services)

    # In FastAPI app:
    from socketio import ASGIApp
    app = FastAPI(...)
    app = ASGIApp(sio, app)
"""

from typing import Optional, Any, Dict
from socketio import AsyncServer, ASGIApp
from models.enums import ZoneID, AnimationID, ZoneRenderMode
from models.animation_params.animation_param_id import AnimationParamID
from models.domain import ZoneCombined
from models.color import Color
from models.events import (
    EventType,
    ZoneStateChangedEvent,
    AnimationStartedEvent,
    AnimationStoppedEvent,
    AnimationParameterChangedEvent
)
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.API)


class SocketIOHandler:
    """Manages Socket.IO server and event handling"""

    def __init__(self):
        self.sio: Optional[AsyncServer] = None
        self.services: Optional[Any] = None

    async def setup_event_handlers(self, sio: AsyncServer, services: Any) -> None:
        """Register all Socket.IO event handlers"""
        self.sio = sio
        self.services = services

        # Subscribe to backend EventBus events
        self._subscribe_to_events()

        # Register Socket.IO client event handlers
        self._register_client_handlers(sio)

        log.info("Socket.IO handlers initialized")

    def _subscribe_to_events(self) -> None:
        """Subscribe to backend EventBus events for broadcasting"""
        if not self.services or not self.services.event_bus:
            log.warn("EventBus not available for Socket.IO")
            return

        event_bus = self.services.event_bus

        # Subscribe to zone state changes
        event_bus.subscribe(
            EventType.ZONE_STATE_CHANGED,
            self._on_zone_state_changed
        )

        # Subscribe to animation events
        event_bus.subscribe(
            EventType.ANIMATION_STARTED,
            self._on_animation_started
        )

        event_bus.subscribe(
            EventType.ANIMATION_STOPPED,
            self._on_animation_stopped
        )

        event_bus.subscribe(
            EventType.ANIMATION_PARAMETER_CHANGED,
            self._on_animation_param_changed
        )

        log.info("Socket.IO subscribed to EventBus events")

    def _register_client_handlers(self, sio: AsyncServer) -> None:
        """Register client-side event handlers"""

        @sio.event
        async def zone_set_color(sid: str, data: Dict[str, Any]) -> None:
            """Client command: Set zone color"""
            try:
                zone_id = ZoneID[data['zone_id'].upper()]
                color = Color.from_hue(data.get('hue', 0))
                self.services.zone_service.set_color(zone_id, color)
                log.info(f"Zone color set via WebSocket: {zone_id.name}")
            except Exception as e:
                log.error(f"Error setting zone color: {e}")
                await sio.emit('error', {'message': str(e)}, room=sid)

        @sio.event
        async def zone_set_brightness(sid: str, data: Dict[str, Any]) -> None:
            """Client command: Set zone brightness"""
            try:
                zone_id = ZoneID[data['zone_id'].upper()]
                brightness = data.get('brightness', 100)
                self.services.zone_service.set_brightness(zone_id, brightness)
                log.info(f"Zone brightness set via WebSocket: {zone_id.name}={brightness}")
            except Exception as e:
                log.error(f"Error setting zone brightness: {e}")
                await sio.emit('error', {'message': str(e)}, room=sid)

        @sio.event
        async def zone_set_enabled(sid: str, data: Dict[str, Any]) -> None:
            """Client command: Toggle zone on/off"""
            try:
                zone_id = ZoneID[data['zone_id'].upper()]
                enabled = data.get('enabled', True)
                self.services.zone_service.set_is_on(zone_id, enabled)
                log.info(f"Zone enabled set via WebSocket: {zone_id.name}={enabled}")
            except Exception as e:
                log.error(f"Error setting zone enabled: {e}")
                await sio.emit('error', {'message': str(e)}, room=sid)

        @sio.event
        async def zone_set_render_mode(sid: str, data: Dict[str, Any]) -> None:
            """Client command: Set zone render mode (STATIC or ANIMATION)"""
            try:
                zone_id = ZoneID[data['zone_id'].upper()]
                mode = ZoneRenderMode[data.get('mode', 'STATIC').upper()]
                zone = self.services.zone_service.get_zone(zone_id)
                zone.state.mode = mode
                self.services.zone_service._save_zone(zone_id)
                log.info(f"Zone render mode set via WebSocket: {zone_id.name}={mode.name}")
            except Exception as e:
                log.error(f"Error setting zone render mode: {e}")
                await sio.emit('error', {'message': str(e)}, room=sid)

        @sio.event
        async def animation_start(sid: str, data: Dict[str, Any]) -> None:
            """Client command: Start animation on zone"""
            try:
                zone_id = ZoneID[data['zone_id'].upper()]
                animation_id = AnimationID[data.get('animation_id', 'BREATHE').upper()]
                parameters = data.get('parameters', {})

                await self.services.animation_engine.start_for_zone(
                    zone_id, animation_id, parameters
                )
                log.info(f"Animation started via WebSocket: {zone_id.name}={animation_id.name}")
            except Exception as e:
                log.error(f"Error starting animation: {e}")
                await sio.emit('error', {'message': str(e)}, room=sid)

        @sio.event
        async def animation_stop(sid: str, data: Dict[str, Any]) -> None:
            """Client command: Stop animation on zone"""
            try:
                zone_id = ZoneID[data['zone_id'].upper()]
                await self.services.animation_engine.stop_for_zone(zone_id)
                log.info(f"Animation stopped via WebSocket: {zone_id.name}")
            except Exception as e:
                log.error(f"Error stopping animation: {e}")
                await sio.emit('error', {'message': str(e)}, room=sid)

        @sio.event
        async def animation_set_param(sid: str, data: Dict[str, Any]) -> None:
            """Client command: Update animation parameter"""
            try:
                zone_id = ZoneID[data['zone_id'].upper()]
                param_id = AnimationParamID[data.get('param_id', '').upper()]
                value = data.get('value')

                self.services.animation_engine.update_param(zone_id, param_id, value)
                log.info(f"Animation param updated via WebSocket: {zone_id.name}.{param_id.name}={value}")
            except Exception as e:
                log.error(f"Error updating animation parameter: {e}")
                await sio.emit('error', {'message': str(e)}, room=sid)

        log.info("Client event handlers registered")

    async def _on_zone_state_changed(self, event: ZoneStateChangedEvent) -> None:
        """EventBus handler: Broadcast zone state change to all clients"""
        if not self.sio:
            return

        zone_id = event.zone_id
        zone = self.services.zone_service.get_zone(zone_id)

        payload = {
            'zone_id': zone_id.name,
            'color': zone.state.color.to_dict() if zone.state.color else None,
            'brightness': zone.state.brightness,
            'is_on': zone.state.is_on,
            'render_mode': zone.state.mode.name,
        }

        await self.sio.emit('zone:state_changed', payload)
        log.debug(f"Broadcasted zone state change: {zone_id.name}")

    async def _on_animation_started(self, event: AnimationStartedEvent) -> None:
        """EventBus handler: Broadcast animation start event"""
        if not self.sio:
            return

        payload = {
            'zone_id': event.zone_id.name,
            'animation_id': event.animation_id.name,
            'parameters': event.parameters or {},
        }

        await self.sio.emit('animation:started', payload)
        log.debug(f"Broadcasted animation started: {event.zone_id.name}={event.animation_id.name}")

    async def _on_animation_stopped(self, event: AnimationStoppedEvent) -> None:
        """EventBus handler: Broadcast animation stop event"""
        if not self.sio:
            return

        payload = {
            'zone_id': event.zone_id.name,
        }

        await self.sio.emit('animation:stopped', payload)
        log.debug(f"Broadcasted animation stopped: {event.zone_id.name}")

    async def _on_animation_param_changed(self, event: AnimationParameterChangedEvent) -> None:
        """EventBus handler: Broadcast animation parameter change"""
        if not self.sio:
            return

        payload = {
            'zone_id': event.zone_id.name,
            'param_id': event.param_id.name,
            'value': event.value,
        }

        await self.sio.emit('animation:param_changed', payload)
        log.debug(f"Broadcasted animation param changed: {event.zone_id.name}.{event.param_id.name}={event.value}")


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
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    sio = AsyncServer(
        async_mode='asgi',
        cors_allowed_origins=cors_origins,
        ping_timeout=60,
        ping_interval=25,
        logger=False,  # Disable logging to avoid noise
        engineio_logger=False,
    )

    log.info(f"Socket.IO server created with CORS origins: {cors_origins}")

    return sio


def wrap_app_with_socketio(app, sio: AsyncServer):
    """
    Wrap FastAPI app with Socket.IO ASGI middleware.

    This makes the app handle both HTTP (FastAPI) and WebSocket (Socket.IO) requests.

    Args:
        app: FastAPI application instance
        sio: AsyncServer instance

    Returns:
        ASGIApp wrapping FastAPI with Socket.IO
    """
    return ASGIApp(sio, app)
