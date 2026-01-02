from api.socketio.zones.on_connect import register_zone_on_connect
from api.socketio_handler import socketio_handler

from api.socketio.logs.broadcaster import register_logs
from api.socketio.tasks.broadcaster import register_tasks


async def register_socketio(sio, services):
    # Initialize main Socket.IO handler for zone snapshot updates
    await socketio_handler.setup(sio, services)

    register_zone_on_connect(sio, services)

    register_logs(sio)
    register_tasks(sio)