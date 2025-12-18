"""Zone service - Business logic for zones"""

import asyncio
from typing import List, Optional
from models.enums import ZoneID, ZoneRenderMode
from models.domain import ZoneCombined
from models.color import Color
from models.events import EventType, ZoneStateChangedEvent
from services.data_assembler import DataAssembler
from services.application_state_service import ApplicationStateService
from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.ZONE)

class ZoneService:
    """High-level zone operations"""

    def __init__(self, assembler: DataAssembler, app_state_service: ApplicationStateService, event_bus: EventBus):
        self.assembler = assembler
        self.zones = assembler.build_zones()
        self._by_id = {zone.config.id: zone for zone in self.zones}
        self.app_state_service = app_state_service
        self.event_bus = event_bus
        
        # Track which zone was last modified to enable selective saves
        self._last_modified_zone_id: Optional[ZoneID] = None

        log.info(f"ZoneService initialized with {len(self.zones)} zones")

    def get_zone(self, zone_id: ZoneID) -> ZoneCombined:
        """Get zone by ID"""
        return self._by_id[zone_id]

    def get_all(self) -> List[ZoneCombined]:
        """Get all zones"""
        return self.zones

    def get_selected_zone(self) -> Optional[ZoneCombined]:
        """
        Get currently selected zone based on ApplicationState.selected_zone_index
        """
        if not self.app_state_service:
            log.warn("Cannot get selected zone: app_state_service not configured")
            return None

        app_state = self.app_state_service.get_state()
        zone_index = app_state.selected_zone_index

        if 0 <= zone_index < len(self.zones):
            return self.zones[zone_index]
        
        log.warn(f"Invalid zone index: {zone_index}, clamping to 0")
        return self.zones[0] if self.zones else None

    def get_enabled(self) -> List[ZoneCombined]:
        """Get only enabled zones"""
        return [zone for zone in self.zones if zone.config.enabled]

    def get_by_render_mode(self, mode: ZoneRenderMode) -> List[ZoneCombined]:
        """Get zones filtered by render mode"""
        return [zone for zone in self.zones if zone.state.mode == mode]

    def get_total_pixel_count(self) -> int:
        """Get total pixel count from all enabled zones"""
        return sum(zone.config.pixel_count for zone in self.get_all())

    # ------------------------------------------------------------------
    # Zone state mutation
    # ------------------------------------------------------------------

    def set_color(self, zone_id: ZoneID, color: Color) -> None:
        zone = self.get_zone(zone_id)
        zone.state.color = color
        
        self._save_zone(zone_id)
        
        log.info(
            "Zone color set", 
            zone=zone.config.display_name,
            color=color
        )
        
        
        asyncio.create_task(self.event_bus.publish(
            ZoneStateChangedEvent(
                zone_id=zone_id,
                color=color,
            )
        ))


    def set_brightness(self, zone_id: ZoneID, brightness: int) -> None:
        zone = self.get_zone(zone_id)
        zone.state.brightness = max(0, min(100, brightness))
        self._save_zone(zone_id)

        log.info(
            "Zone brightness set",
            zone=zone.config.display_name,
            brightness=zone.state.brightness,
        )

        asyncio.create_task(self.event_bus.publish(
            ZoneStateChangedEvent(
                zone_id=zone_id,
                brightness=zone.state.brightness,
            )
        ))

    def adjust_brightness(self, zone_id: ZoneID, delta: int) -> None:
        zone = self.get_zone(zone_id)
        zone.state.brightness = max(0, min(100, zone.state.brightness + delta))
        self._save_zone(zone_id)

        log.info(
            "Zone brightness adjusted",
            zone=zone.config.display_name,
            brightness=zone.state.brightness,
        )

        asyncio.create_task(self.event_bus.publish(
            ZoneStateChangedEvent(
                zone_id=zone_id,
                brightness=zone.state.brightness,
            )
        ))
        
    def set_is_on(self, zone_id: ZoneID, is_on: bool) -> None:
        zone = self.get_zone(zone_id)
        zone.state.is_on = is_on
        self._save_zone(zone_id)

        log.info(
            "Zone power state changed",
            zone=zone.config.display_name,
            is_on=is_on,
        )

        asyncio.create_task(self.event_bus.publish(
            ZoneStateChangedEvent(
                zone_id=zone_id,
                is_on=is_on,
            )
        ))

    def set_render_mode(self, zone_id: ZoneID, mode: ZoneRenderMode, animation=None) -> None:
        """
        Set zone render mode (STATIC, ANIMATION, or OFF).

        Args:
            zone_id: Zone ID to change
            mode: New render mode (ZoneRenderMode enum)
            animation: AnimationState for ANIMATION mode, None otherwise
        """
        zone = self.get_zone(zone_id)
        zone.state.mode = mode
        if animation is not None:
            zone.state.animation = animation

        self._save_zone(zone_id)

        log.info(
            "Zone render mode changed",
            zone=zone.config.display_name,
            mode=mode.name,
            animation=animation.id.name if animation else None,
        )

        asyncio.create_task(self.event_bus.publish(
            ZoneStateChangedEvent(
                zone_id=zone_id,
                render_mode=mode,
            )
        ))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _save_zone(self, zone_id: ZoneID) -> None:
        """
        Save only the specified zone to state.json.

        This is more efficient than saving all zones when only one was modified.
        The assembler's debouncing will batch rapid saves within 500ms window.

        Args:
            zone_id: ID of the zone to save
        """
        self._last_modified_zone_id = zone_id
        zone = self.get_zone(zone_id)
        # Pass only the modified zone to reduce I/O (assembler handles debouncing)
        self.assembler.save_zone_state([zone])

    def save_state(self) -> None:
        """Persist current state (alias for save)"""
        self.save()
       
    def save(self) -> None:
        """Persist current state"""
        self.assembler.save_zone_state(self.zones)

