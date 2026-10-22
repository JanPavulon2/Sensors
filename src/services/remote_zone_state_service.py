"""Remote Zone State Service - owns the desired state of every remote zone,
pushes it to the owning ESP32, and reconciles when the device reports back
something different.

Was RemoteZoneRenderBridge, which neither rendered nor bridged. It does not go
through FrameManager: FrameManager drives locally-wired GPIO strips, whereas an
ESP32 renders its own pixels and only needs the state (see
docs/architecture-vnext/05-esp32-rpi-roadmap.md Phase 6, "stream state, not
frames").

Why reconciliation rather than per-command acknowledgements: HttpNodeTransport
.send() runs inside HostEngine's single shared message-queue consumer and must
never raise or block there (one escaped exception already killed command
delivery to every node once). So command delivery stays fire-and-forget, and
correctness comes from convergence instead:

  1. desired state is persisted by RigService, surviving a backend restart
  2. the firmware echoes its applied state in every 5s heartbeat
  3. reconcile() compares the two and re-pushes on mismatch

That single mechanism covers offline nodes, ESP32 reboots, dropped commands and
backend restarts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.color import Color
from models.domain.remote_zone import RemoteZone, RemoteZoneState
from models.events import EventType, NodeAppliedStateReportedEvent
from services.event_bus import EventBus
from services.node_registry_service import NodeRegistryService
from services.rig_service import RigService
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.ZONE)

VALID_RENDER_MODES = ("STATIC", "BREATHE")


class RemoteZoneStateService:
    def __init__(
        self,
        node_registry_service: NodeRegistryService,
        rig_service: RigService,
        event_bus: EventBus,
    ):
        self.node_registry_service = node_registry_service
        self.rig_service = rig_service
        self.event_bus = event_bus
        self._out_of_sync_zone_ids: set[str] = set()

        # Subscribed rather than called directly: NodeRegistryService already
        # sits below this service (it is a constructor dependency here), so a
        # back-reference for reconciliation would be a dependency cycle.
        event_bus.subscribe(
            EventType.NODE_APPLIED_STATE_REPORTED,
            self._on_applied_state_reported,
        )

    async def _on_applied_state_reported(self, event: NodeAppliedStateReportedEvent) -> None:
        await self.reconcile_node(event.node_id, event.applied_states)

    # === Reads ===

    def list_zones(self) -> List[RemoteZone]:
        return self.rig_service.list_zones()

    def get_zones_for_node(self, node_id: str) -> List[RemoteZone]:
        return self.rig_service.get_zones_for_node(node_id)

    def get_state(self, zone_id: str) -> RemoteZoneState:
        return self.rig_service.get_zone_state(zone_id)

    def is_in_sync(self, zone_id: str) -> bool:
        return zone_id not in self._out_of_sync_zone_ids

    # === Mutations ===

    async def set_color(self, zone_id: str, color: Color) -> None:
        self.rig_service.update_zone_state(zone_id, color=color)
        await self.push_state(zone_id)

    async def set_brightness(self, zone_id: str, brightness: int) -> None:
        self.rig_service.update_zone_state(zone_id, brightness=max(0, min(100, brightness)))
        await self.push_state(zone_id)

    async def set_is_on(self, zone_id: str, is_on: bool) -> None:
        self.rig_service.update_zone_state(zone_id, is_on=is_on)
        await self.push_state(zone_id)

    async def set_render_mode(self, zone_id: str, render_mode: str) -> None:
        normalized_mode = render_mode.upper()
        if normalized_mode not in VALID_RENDER_MODES:
            raise ValueError(
                f"Unsupported render mode '{render_mode}'. Supported: {list(VALID_RENDER_MODES)}"
            )
        self.rig_service.update_zone_state(zone_id, render_mode=normalized_mode)
        await self.push_state(zone_id)

    # === Push / reconcile ===

    def state_payload(self, zone_id: str) -> Dict[str, Any]:
        state = self.rig_service.get_zone_state(zone_id)
        red, green, blue = state.color.to_rgb()
        return {
            "zone_id": zone_id,
            "is_on": state.is_on,
            "brightness": state.brightness,
            "color": {"r": red, "g": green, "b": blue},
            "render_mode": state.render_mode,
        }

    async def push_state(self, zone_id: str) -> None:
        zone = self.rig_service.get_zone(zone_id)
        if zone is None:
            raise ValueError(f"Unknown remote zone: {zone_id}")

        await self.node_registry_service.send_command(
            zone.node_id, "zone.state", self.state_payload(zone_id)
        )
        log.info(f"Pushed state to remote zone '{zone_id}'", node_id=zone.node_id)

    async def push_all_for_node(self, node_id: str) -> None:
        """Re-send every zone this node owns. Called when a node (re)appears, so
        a rebooted ESP32 returns to the state the host believes it should be in."""
        for zone in self.rig_service.get_zones_for_node(node_id):
            await self.push_state(zone.zone_id)

    async def reconcile_node(self, node_id: str, applied_states: List[dict]) -> List[str]:
        """Compare a heartbeat's echoed state against desired state, re-pushing
        any zone that has drifted. Returns the zone ids that needed correcting.

        A node that reports nothing (older firmware, or one that has not applied
        any state yet) is left alone rather than being spammed every heartbeat.
        """
        if not applied_states:
            return []

        applied_by_zone_id = {
            entry.get("zone_id"): entry for entry in applied_states if entry.get("zone_id")
        }

        corrected_zone_ids: List[str] = []
        for zone in self.rig_service.get_zones_for_node(node_id):
            applied = applied_by_zone_id.get(zone.zone_id)
            if applied is None:
                continue

            if self._matches_desired(zone.zone_id, applied):
                self._out_of_sync_zone_ids.discard(zone.zone_id)
                continue

            self._out_of_sync_zone_ids.add(zone.zone_id)
            corrected_zone_ids.append(zone.zone_id)
            log.warn(
                f"Remote zone '{zone.zone_id}' drifted from desired state - re-pushing",
                node_id=node_id,
            )
            await self.push_state(zone.zone_id)

        return corrected_zone_ids

    def _matches_desired(self, zone_id: str, applied: dict) -> bool:
        desired = self.state_payload(zone_id)

        if bool(applied.get("is_on")) != desired["is_on"]:
            return False
        if int(applied.get("brightness", -1)) != desired["brightness"]:
            return False
        if str(applied.get("render_mode", "")).upper() != desired["render_mode"]:
            return False

        applied_color = applied.get("color") or {}
        desired_color = desired["color"]
        return all(
            int(applied_color.get(channel, -1)) == desired_color[channel]
            for channel in ("r", "g", "b")
        )
