"""Socket.IO event handlers for the /metrics namespace (render metrics streaming)."""

from utils.logger import get_logger
from models.enums import LogCategory

log = get_logger().for_category(LogCategory.FRAME_MANAGER)


def register_metrics_broadcaster(sio, services):
    """
    Register /metrics namespace handlers for render metrics streaming.

    Auto-starts/stops metrics collection based on client connections.
    Streaming only — mutations (reset, set interval) go through REST API.
    """
    metrics_streamer = services.metrics_streamer

    @sio.event(namespace="/metrics")
    async def connect(sid, environ):
        log.info(f"Metrics client {sid} connected to /metrics namespace")
        if metrics_streamer:
            metrics_streamer.on_client_connect()
            snapshot = metrics_streamer.collector.get_snapshot()
            await sio.emit("metrics:snapshot", snapshot, namespace="/metrics", room=sid)

    @sio.event(namespace="/metrics")
    async def disconnect(sid):
        log.info(f"Metrics client {sid} disconnected from /metrics namespace")
        if metrics_streamer:
            metrics_streamer.on_client_disconnect()
