from api.socketio.zones.broadcaster import register_zone_broadcaster
from api.socketio.zones.on_connect import register_zone_on_connect

from api.socketio.logs.broadcaster import register_logs
from api.socketio.tasks.broadcaster import register_tasks


async def register_socketio(sio, services):
    register_zone_broadcaster(sio, services)
    register_zone_on_connect(sio, services)

    register_logs(sio)
    register_tasks(sio)