from dataclasses import asdict
from api.socketio.zones.dto import ZoneSnapshotDTO
from lifecycle.task_registry import TaskRegistry
from services.log_broadcaster import get_broadcaster
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SOCKETIO)


def register_on_connect(sio, services):
    """
    Registers connection lifecycle handlers for Socket.IO.
    Sends initial state (zones, tasks, logs) on client connect.
    """

    @sio.event
    async def connect(sid, environ, auth=None):
        """Handle client connection and send initial state"""
        client_ip = environ.get('REMOTE_ADDR', 'unknown')
        log.info(f"Client connected: {sid} from {client_ip}")

        # === Zones ===
        if services and services.zone_service:
            zones = services.zone_service.get_all()
            payload = [asdict(ZoneSnapshotDTO.from_zone(z)) for z in zones]
            await sio.emit("zones:snapshot", payload, room=sid)
        else:
            log.warn(f"Skipping initial zone snapshot for {sid}: services not ready")

        # === Tasks ===
        try:
            registry = TaskRegistry.instance()
            tasks = registry.get_all_as_dicts()
            stats = registry.get_stats()
            await sio.emit("tasks:all", {'tasks': tasks}, room=sid)
            await sio.emit("tasks:stats", {'stats': stats}, room=sid)
        except Exception as e:
            log.error(f"Failed to send initial tasks to {sid}: {e}")

        # === Logs (current app run, max 100) ===
        try:
            broadcaster = get_broadcaster()
            logs = broadcaster.get_recent_logs(limit=100)
            payload = [entry.model_dump() for entry in logs]
            await sio.emit("logs:history", {'logs': payload}, room=sid)
        except Exception as e:
            log.error(f"Failed to send initial logs to {sid}: {e}")

    @sio.event
    async def disconnect(sid):
        """Handle client disconnection"""
        log.info(f"Client disconnected: {sid}")