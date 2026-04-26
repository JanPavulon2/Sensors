from api.socketio.on_connect import register_on_connect
from api.socketio.zones.broadcaster import register_zone_broadcaster
from api.socketio.logs.broadcaster import register_logs
from api.socketio.tasks.broadcaster import register_tasks


async def register_socketio(sio, services):
    # Initialize main Socket.IO handler for zone snapshot updates
    await socketio_handler.setup(sio, services)

    register_zone_on_connect(sio, services)

    register_logs(sio)
    register_tasks(sio)

    # Frame streaming
    register_frame_broadcaster(sio, services)

    # Render metrics streaming
    register_metrics_broadcaster(sio, services)