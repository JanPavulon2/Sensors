"""Zone service - Business logic for zones"""

import asyncio
from typing import Any, Dict, List, Optional
from models.animation_params.animation_param_id import AnimationParamID
from models.domain.animation import AnimationState
from models.enums import AnimationID, ZoneID, ZoneRenderMode
from models.domain import ZoneCombined
from models.color import Color
from models.events import ZoneStaticStateChangedEvent
from models.events.zone_runtime_events import ZoneAnimationChangedEvent, ZoneRenderModeChangedEvent, ZoneAnimationParamChangedEvent
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
            ZoneStaticStateChangedEvent(
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
            ZoneStaticStateChangedEvent(
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
            ZoneStaticStateChangedEvent(
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
            ZoneStaticStateChangedEvent(
                zone_id=zone_id,
                is_on=is_on,
            )
        ))

    def set_animation(
        self,
        zone_id: ZoneID,
        animation_id: AnimationID
    ) -> None:
        """
        Assign a NEW animation to zone and switch render mode to ANIMATION.

        Semantics:
        - Always resets animation parameters (defaults will be used)
        - Implicitly switches render mode to ANIMATION
        - Persists state
        - Emits domain events
        """
        
        zone = self.get_zone(zone_id)
        if not zone:
            raise ValueError(f"Zone not found: {zone_id}")
        
        
        old_mode = zone.state.mode
        old_animation = zone.state.animation.id if zone.state.animation else None

        # 1. Create NEW animation state (params empty → defaults later)
        zone.state.animation = AnimationState(
            id=animation_id,
            parameters={}
        )
        
        # 2. Switch render mode implicitly
        zone.state.mode = ZoneRenderMode.ANIMATION

        # 3. Persist state
        self.save_state()
        
        log.info(
            "Zone animation changed",
            zone=zone.config.display_name,
            animation=zone.state.animation
        )

        # 3. Publish domain events 
        asyncio.create_task(self.event_bus.publish(
            ZoneAnimationChangedEvent(
                zone_id=zone_id,
                animation_id=animation_id,
                params={}
            )
        ))
        
        if old_mode != ZoneRenderMode.ANIMATION:
            asyncio.create_task(self.event_bus.publish(
                ZoneRenderModeChangedEvent(
                    zone_id=zone_id,
                    old=old_mode,
                    new=ZoneRenderMode.ANIMATION
                )
            ))

    def set_animation_param(self, zone_id: ZoneID, param_id: AnimationParamID, value: Any) -> None:
        """
        Set zone animation parameter value
        """
        zone = self.get_zone(zone_id)

        if zone.state.mode == ZoneRenderMode.STATIC:
            raise ValueError("Zone is in static mode")

        if zone.state.animation is None:
            raise ValueError("Zone has no active animation")

        zone.state.animation.parameters[param_id] = value

        self._save_zone(zone_id)

        log.info(
            "Zone animation parameter changed",
            zone=zone_id,
            animation=zone.state.animation
        )

        # Publish event so AnimationModeController and SnapshotPublisher are notified
        asyncio.create_task(self.event_bus.publish(
            ZoneAnimationParamChangedEvent(
                zone_id=zone_id,
                param_id=param_id,
                value=value
            )
        ))

    
    def set_render_mode(
        self, 
        zone_id: ZoneID, 
        render_mode: ZoneRenderMode
    ) -> None:
        zone = self.get_zone(zone_id)

        old_mode = zone.state.mode
        if old_mode == render_mode:
            log.info(f"Zone already in {zone.state.mode} render mode, no action needed")
            return
        
        # 1. Update domain state
        zone.state.mode = render_mode
    
        # 2. Persist
        self.save_state()

        log.info(
            "Zone render mode changed",
            zone=zone.config.display_name,
            old_mode=old_mode.name,
            new_mode=render_mode.name,
        )

        # 3. Publish domain event
        asyncio.create_task(self.event_bus.publish(
            ZoneRenderModeChangedEvent(
                zone_id=zone_id,
                old=old_mode,
                new=render_mode
            )
        ))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    
    def _save_zone(self, zone_id: ZoneID) -> None:
        """
        Save only the specified zone to state.json (non-blocking).

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
        """Persist current state"""
        self.assembler.save_zone_state(self.zones)