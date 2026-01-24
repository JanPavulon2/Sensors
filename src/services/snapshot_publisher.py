from __future__ import annotations

from api.socketio.zones.dto import ZoneSnapshotDTO
from services.zone_service import ZoneService
from services.event_bus import EventBus
from models.events.types import EventType
from models.events.zone_snapshot_events import ZoneSnapshotUpdatedEvent
from models.enums import ZoneID
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SNAPSHOT)


class SnapshotPublisher:
    """
    Publishes UI-facing ZoneSnapshotUpdatedEvent
    in response to domain-level zone / animation events.

    Responsibilities:
    - listen to zone-related domain events
    - build ZoneSnapshot from current ZoneService state
    - publish snapshot event for frontend / websocket layer
    """

    def __init__(
        self,
        *,
        zone_service: ZoneService,
        event_bus: EventBus,
    ):
        self.zone_service = zone_service
        self.event_bus = event_bus

        self._subscribe()

        log.info("SnapshotPublisher initialized")

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def _subscribe(self) -> None:
        for event_type in (
            EventType.ZONE_STATIC_STATE_CHANGED,
            EventType.ZONE_RENDER_MODE_CHANGED,
            EventType.ZONE_ANIMATION_CHANGED,
            EventType.ZONE_ANIMATION_PARAM_CHANGED,
            EventType.ANIMATION_PARAMETER_CHANGED,
        ):
            self.event_bus.subscribe(event_type, self._on_zone_changed)
            
            
    async def _on_zone_changed(self, event) -> None:
        zone_id: ZoneID | None = getattr(event, "zone_id", None)
        if not zone_id:
            return

        zone = self.zone_service.get_zone(zone_id)
        if not zone:
            return

        snapshot = ZoneSnapshotDTO.from_zone(zone)

        await self.event_bus.publish(
            ZoneSnapshotUpdatedEvent(
                zone_id=zone_id,
                snapshot=snapshot,
            )
        )
    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------
            
    # async def _on_zone_changed(self, event) -> None:
    #     """
    #     Handle ANY zone-related change and emit fresh snapshot.
    #     """

    #     zone_id: ZoneID | None = getattr(event, "zone_id", None)
    #     if not zone_id:
    #         log.warn("Zone change event without zone_id", event=event)
    #         return

    #     zone = self.zone_service.get_zone(zone_id)
    #     if not zone:
    #         log.warn("Snapshot requested for missing zone", zone_id=zone_id)
    #         return

    #     snapshot_event = ZoneSnapshotUpdatedEvent(
    #         zone_id=zone_id,
    #         snapshot=snapshot,
    #     )

    #     self.event_bus.publish(snapshot_event)

    #     log.debug(
    #         "Published zone snapshot",
    #         zone=zone_id.name,
    #     )
