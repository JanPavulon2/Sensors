"""
StaticModeController - controls zone editing (colors, brightness, zone selection)

Renders zone states to FrameManager as ZoneFrames (one color per zone).
"""

from __future__ import annotations

import asyncio
from models.enums import FramePriority, FrameSource, ZoneEditTarget, ZoneRenderMode
from models.domain import ZoneCombined
from models.frame import MultiZoneFrame, SingleZoneFrame
from models.events import ZoneStateChangedEvent, EventType
from services import ServiceContainer
from services.zone_service import ZoneService
from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.STATIC_CONTROLLER)


class StaticModeController:    
    """
    Handles editing of zones in STATIC render mode.

    Responsibilities:
    - adjust zone parameters (hue, preset, brightness)
    - push updated frames to FrameManager
    - render initial STATIC zones on startup

    Does NOT:
    - manage zone selection
    - manage edit mode
    - run animation loops
    """
    
    EDIT_TARGETS = [
        ZoneEditTarget.COLOR_HUE,
        ZoneEditTarget.COLOR_PRESET,
        ZoneEditTarget.BRIGHTNESS,
    ]

    def __init__(self, services: ServiceContainer):
        self.zone_service: ZoneService = services.zone_service
        self.app_state_service = services.app_state_service
        self.frame_manager = services.frame_manager
        self.color_manager = services.color_manager
        self.event_bus: EventBus = services.event_bus

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def initialize(self):
        """
        Render all zones that start in STATIC mode.

        Called once during LightingController initialization.
        Must be async to ensure frames are submitted to FrameManager before returning.
        """

        log.info("Initializing static mode controller...")

        static_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.STATIC)
        if not static_zones:
            log.info("No static zones to initialize")
            return

        zones_colors={}

        for zone in static_zones:
            zones_colors[zone.id] = zone.state.color.with_brightness(zone.brightness)

        # Ensure valid edit target
        state = self.app_state_service.get_state()
        if state.selected_zone_edit_target not in self.EDIT_TARGETS:
            self.app_state_service.set_selected_zone_edit_target(ZoneEditTarget.BRIGHTNESS)
            
        frame = MultiZoneFrame(
            zone_colors=zones_colors,
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
            ttl=10.0,
        )
        await self.frame_manager.push_frame(frame)

        # Subscribe to zone state changes (e.g., from API) to re-submit frames
        self.event_bus.subscribe(
            event_type=EventType.ZONE_STATE_CHANGED,
            handler=self._on_zone_state_changed
        )

        log.info(f"Rendered {len(zones_colors)} STATIC zones")

    # ------------------------------------------------------------------
    # Parameter editing
    # ------------------------------------------------------------------

    def cycle_edit_target(self) -> None:
        """
        Cycle through zone edit targets (brightness → color → preset).
        """
        state = self.app_state_service.get_state()
        current = state.selected_zone_edit_target

        if current not in self.EDIT_TARGETS:
            next_target = self.EDIT_TARGETS[0]
        else:
            idx = self.EDIT_TARGETS.index(current)
            next_target = self.EDIT_TARGETS[(idx + 1) % len(self.EDIT_TARGETS)]

        self.app_state_service.set_selected_zone_edit_target(next_target)

        log.info(
            "Zone edit target changed",
            target=next_target.name,
        )

    def adjust_selected_target(self, delta: int) -> None:
        """
        Adjust currently selected parameter for the selected zone.
        """
        zone = self.zone_service.get_selected_zone()
        if not zone:
            log.debug("StaticModeController.adjust_param: no selected zone")
            return

        target = self.app_state_service.get_state().selected_zone_edit_target

        if target == ZoneEditTarget.BRIGHTNESS:
            self.zone_service.adjust_brightness(zone.id, delta)


        elif target == ZoneEditTarget.COLOR_HUE:
            self.zone_service.set_color(
                zone.id,
                zone.state.color.adjust_hue(delta * 10),
            )

        elif target == ZoneEditTarget.COLOR_PRESET:
            self.zone_service.set_color(
                zone.id,
                zone.state.color.next_preset(delta, self.color_manager),
            )

        else:
            log.warn("Unsupported ZoneEditTarget", target=target)
            return

        
        self.submit_zone(zone)
        
        log.info(
            "Static zone edited",
            zone=zone.config.display_name,
            target=target.name,
        )

    def submit_zone(self, zone: ZoneCombined):
        """Submit single zone update to FrameManager"""
        # Respect is_on state: show black when powered off
        if not zone.state.is_on:
            color = zone.state.color.black()
        else:
            color = zone.state.color.with_brightness(zone.brightness)

        frame = SingleZoneFrame(
            zone_id=zone.config.id,
            color=color,
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
            ttl=10.0,  # Match initialize() TTL to keep static zones persistent
        )
        asyncio.create_task(self.frame_manager.push_frame(frame))

    # ------------------------------------------------------------------
    # Event Handling
    # ------------------------------------------------------------------

    async def _on_zone_state_changed(self, event: ZoneStateChangedEvent) -> None:
        """
        Handle zone state changes from API or hardware.

        When a zone's state is updated (brightness, color, is_on),
        re-submit its frame to FrameManager so hardware reflects the change.
        """
        log.debug(
            "Zone state changed: ", 
            event=event
        )
        
        zone = self.zone_service.get_zone(event.zone_id)
        if not zone:
            log.warn(f"Zone state changed but zone not found: {event.zone_id}")
            return

        # Only re-render if zone is in STATIC mode
        if zone.state.mode != ZoneRenderMode.STATIC:
            return

        log.debug(
            f"Zone state changed, re-submitting frame",
            zone=zone.config.display_name,
            brightness=zone.brightness,
        )

        self.submit_zone(zone)
