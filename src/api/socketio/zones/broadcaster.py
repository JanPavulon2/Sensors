from dataclasses import asdict
from models.events import EventType, ZoneStateChangedEvent
from services.service_container import ServiceContainer
from api.socketio.zones.dto import ZoneSnapshotDTO


def register_zone_broadcaster(sio, services: ServiceContainer):
    bus = services.event_bus

    async def on_zone_changed(event: ZoneStateChangedEvent):
        zone = services.zone_service.get_zone(event.zone_id)
        payload = ZoneSnapshotDTO.from_zone(zone)
        await sio.emit("zone.snapshot", asdict(payload))

    bus.subscribe(EventType.ZONE_STATE_CHANGED, on_zone_changed) # type: ignore