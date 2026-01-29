from dataclasses import asdict
from models.events import EventType
from models.events.zone_snapshot_events import ZoneSnapshotUpdatedEvent
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SOCKETIO)


def register_zone_broadcaster(sio, services):
    """
    Registers EventBus subscription for zone snapshot updates.
    Broadcasts zone state changes to all connected clients.
    """

    async def on_zone_snapshot_updated(event: ZoneSnapshotUpdatedEvent) -> None:
        """Broadcast zone snapshot to all connected clients"""
        await sio.emit("zone:snapshot", asdict(event.snapshot))

    services.event_bus.subscribe(
        EventType.ZONE_SNAPSHOT_UPDATED,
        on_zone_snapshot_updated,
    )

    log.info("Zone broadcaster registered with EventBus")
