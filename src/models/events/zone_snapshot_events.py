from dataclasses import dataclass

from api.socketio.zones.dto import ZoneSnapshotDTO
from models.events.base import Event
from models.events.types import EventType
from models.events.sources import EventSource
from models.enums import ZoneID


@dataclass(init=False)
class ZoneSnapshotUpdatedEvent(Event):
    """
    UI-facing snapshot event.
    Emitted AFTER state persistence.
    """

    zone_id: ZoneID
    snapshot: ZoneSnapshotDTO

    def __init__(self, zone_id: ZoneID, snapshot: ZoneSnapshotDTO):
        super().__init__(
            type=EventType.ZONE_SNAPSHOT_UPDATED,
            source=EventSource.SNAPSHOT_PUBLISHER,
        )
        self.zone_id = zone_id
        self.snapshot = snapshot
