from dataclasses import asdict
from api.socketio.zones.dto import ZoneSnapshotDTO


def register_zone_on_connect(sio, services):
    @sio.event
    async def connect(sid, environ, auth=None):
        zones = services.zone_service.get_all()
        payload = [asdict(ZoneSnapshotDTO.from_zone(z)) for z in zones]
        await sio.emit("zones:snapshot", payload, room=sid)