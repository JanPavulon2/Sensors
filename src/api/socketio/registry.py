from api.socketio.on_connect import register_on_connect
from api.socketio.zones.broadcaster import register_zone_broadcaster
from api.socketio.logs.broadcaster import register_logs
from api.socketio.tasks.broadcaster import register_tasks
from api.socketio.frames.broadcaster import register_frame_broadcaster
from api.socketio.metrics.broadcaster import register_metrics_broadcaster


def register_socketio(sio, services):
    """
    Registers all Socket.IO handlers and EventBus subscriptions.
    """
    # Connection lifecycle - sends initial state (zones, tasks, logs, frames)
    register_on_connect(sio, services)

    # EventBus subscriptions for real-time updates
    register_zone_broadcaster(sio, services)

    # Client command handlers (for on-demand requests)
    register_logs(sio)
    register_tasks(sio)

    # Frame streaming
    register_frame_broadcaster(sio, services)

    # Render metrics streaming
    register_metrics_broadcaster(sio, services)