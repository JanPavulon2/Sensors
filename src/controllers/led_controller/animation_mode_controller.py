"""
AnimationModeController - controls animation selection and parameter tuning
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from models.enums import ZoneRenderMode
from models.events.zone_runtime_events import AnimationStartedEvent
from utils.logger import get_logger, LogCategory
from services import ServiceContainer
from animations.engine import AnimationEngine

if TYPE_CHECKING:
    from models.domain.zone import ZoneCombined

log = get_logger().for_category(LogCategory.ANIM_CONTROLLER)

class AnimationModeController:
    """
    Controls animation lifecycle and parameter tuning
    for the currently selected zone.

    PARAMETER FLOW:
    - cycle_param(): Get available params from anim.PARAMS (definitions)
    - adjust_param(): Call anim.adjust_param(id, delta) → stores in zone.state
    - Adjusted values persist in zone.state.animation.parameters
    - Changes saved to state.json via zone_service
    """

    def __init__(
        self,
        services: ServiceContainer,
        animation_engine: AnimationEngine
    ):
        """
        Controls animation selection and parameter tuning
        for a SINGLE selected zone.
        """
        
        self.zone_service = services.zone_service
        self.app_state_service = services.app_state_service
        self.animation_service = services.animation_service
        self.animation_engine = animation_engine

        self.available_animations = [
            a.id for a in self.animation_service.get_all()
        ]
        
        self.selected_animation_index = 0
        self.selected_animation_param_id = 0

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def initialize(self):
        """
        Start animations for all zones that boot in ANIMATION mode.
        """
        log.info("Initializing animation mode...")

        animated_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.ANIMATION)

        if not animated_zones:
            log.info("No animated zones to initialize")
            return

        log.info(f"AnimationMode init: {len(animated_zones)} zones")

        for zone in animated_zones:
            asyncio.create_task(self._start_zone_animation(zone))
            
    def enter_zone(self, zone: ZoneCombined):
        """
        Called when zone enters ANIMATION render mode.
        """
        anim_state = zone.state.animation
        if not anim_state:
            log.warn("Zone entered ANIMATION without animation assigned", zone=zone.id)
            return

        params = self.animation_service.build_params_for_zone(
            anim_state.id,
            anim_state.parameters,
            zone
        )

        log.info(
            "Entering ANIMATION mode",
            zone=zone.config.display_name,
            animation=anim_state.id.name,
            params=params
        )
        
        asyncio.create_task(
            self.animation_engine.start_for_zone(
                zone.config.id,
                anim_state.id,
                params
            )
        )
            
    def leave_zone(self, zone: ZoneCombined):
        """
        Called when zone leaves ANIMATION render mode.
        """
        asyncio.create_task(
            self.animation_engine.stop_for_zone(zone.config.id)
        )
        
    def cycle_animation(self, delta: int) -> None:
        zone = self.zone_service.get_selected_zone()
        if not zone or zone.state.mode != ZoneRenderMode.ANIMATION:
            return

        self.selected_animation_index = (
            self.selected_animation_index + delta
        ) % len(self.available_animations)

        anim_id = self.available_animations[self.selected_animation_index]
        
        self.zone_service.set_animation(zone.id, anim_id)
        
    # ------------------------------------------------------------------
    # Parameter editing
    # ------------------------------------------------------------------
   
    def cycle_param(self) -> None:
        """
        Cycle through editable animation parameters.

        Gets parameter IDs from the animation's PARAMS definitions (not stored values),
        since stored params might be empty while definitions always exist.
        """
        zone = self.zone_service.get_selected_zone()
        if not zone:
            return

        anim = self.animation_engine.active_animations.get(zone.id)
        if not anim:
            return

        # Get available parameters from the animation's PARAMS definitions
        param_ids = list(anim.PARAMS.keys())
        if not param_ids:
            log.debug(f"Animation {type(anim).__name__} has no parameters")
            return

        state = self.app_state_service.get_state()
        selected_param = state.selected_animation_param_id

        if selected_param not in param_ids:
            next_param = param_ids[0]
        else:
            idx = param_ids.index(selected_param)
            next_param = param_ids[(idx + 1) % len(param_ids)]

        self.app_state_service.set_selected_animation_param_id(next_param)

        log.info("Animation param cycled", param=next_param.name)
        
    def adjust_param(self, delta: int):
        """
        Adjust animation parameter for currently selected zone.

        Updates zone.state.animation.parameters and propagates change
        to running animation engine.
        """

        zone = self.zone_service.get_selected_zone()
        if not zone or zone.state.mode != ZoneRenderMode.ANIMATION:
            return

        # Verify zone has animation state
        if not zone.state.animation:
            log.warn("Zone in animation mode but has no animation state")
            return

        anim = self.animation_engine.active_animations[zone.id]
        if not anim:
            return

        param_id = self.app_state_service.get_state().selected_animation_param_id
        if not param_id:
            return

        # Use animation's adjust_param method which properly handles adjustment logic
        new_value = anim.adjust_param(param_id, delta)
        if new_value is None:
            log.debug(f"Parameter {param_id.name} not adjustable")
            return

        # Use zone_service to persist and emit event
        self.zone_service.set_animation_param(zone.id, param_id, new_value)
        
    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _start_zone_animation(self, zone: ZoneCombined) -> None:
        anim = zone.state.animation
        if not anim:
            log.warn(f"Zone {zone.config.display_name} is in animation mode, but has no animation specified")
            return

        params = self.animation_service.build_params_for_zone(
            anim.id,
            anim.parameters,
            zone,
        )

        log.debug(
            "Starting animation",
            zone=zone.config.display_name,
            animation=anim.id.name,
            params=params,
        )
        
        asyncio.create_task(self.animation_engine.start_for_zone(
            zone.id,
            anim.id,
            params
        ))
        
    async def _ensure_animation_assigned(self, zone: ZoneCombined) -> None:
        if zone.state.animation or not self.available_animations:
            return

        from models.domain.animation import AnimationState
        first_anim = self.available_animations[0]
        zone.state.animation = AnimationState(id=first_anim, parameters={})

        log.info(
            "Auto-assigned animation",
            zone=zone.config.display_name,
            animation=first_anim.name,
        )
        
