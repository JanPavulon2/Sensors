"""
AnimationModeController - controls animation selection and parameter tuning
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from models.enums import ParamID, ZoneRenderMode
from utils.logger import get_logger, LogCategory
from utils.serialization import Serializer
from services import ServiceContainer
from animations.engine import AnimationEngine

if TYPE_CHECKING:
    from models.domain.zone import ZoneCombined

log = get_logger().for_category(LogCategory.ANIM_CONTROLLER)


class AnimationModeController:
    """
    Controls animation lifecycle and parameter tuning
    for the currently selected zone.
    """
    
    ANIM_PARAMS = [
        ParamID.ANIM_SPEED,
        ParamID.ANIM_INTENSITY,
        ParamID.ANIM_PRIMARY_COLOR_HUE,
    ]
    
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

        # Use saved param if it's an animation param, otherwise default to ANIM_SPEED
        saved_param = self.app_state_service.get_state().selected_param_id
        self.selected_param_id = saved_param if saved_param in self.ANIM_PARAMS else ParamID.ANIM_SPEED

        self.available_animations = [
            a.id for a in self.animation_service.get_all()
        ]
        self.selected_animation_index = 0

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
            await self._ensure_animation_assigned(zone)
            await self._start_zone_animation(zone)
            
            self.zone_service.save_state()
            
            
    def cycle_animation(self, delta: int) -> None:
        zone = self.zone_service.get_selected_zone()
        if not zone or zone.state.mode != ZoneRenderMode.ANIMATION:
            return

        self.selected_animation_index = (
            self.selected_animation_index + delta
        ) % len(self.available_animations)

        anim_id = self.available_animations[self.selected_animation_index]
        
        from models.domain.animation import AnimationState
        zone.state.animation = AnimationState(
            id=anim_id, 
            parameter_values={}
        )

        log.info(
            "Animation changed",
            zone=zone.config.display_name,
            animation=anim_id.name,
        )
        asyncio.create_task(self._start_zone_animation(zone))

    # ------------------------------------------------------------------
    # Parameter editing
    # ------------------------------------------------------------------
   
    def cycle_parameter(self) -> None:
        """
        Cycle through editable STATIC parameters.
        """
        params = [
            ParamID.ANIM_SPEED,
            ParamID.ANIM_PRIMARY_COLOR_HUE,
            ParamID.ANIM_SECONDARY_COLOR_HUE,
            ParamID.ANIM_TERTIARY_COLOR_HUE,
            ParamID.ANIM_INTENSITY,
        ]

        if self.selected_param_id not in params:
            self.selected_param_id = params[0]
        else:
            idx = params.index(self.selected_param_id)
            self.selected_param_id = params[(idx + 1) % len(params)]

        self.app_state_service.set_selected_param_id(self.selected_param_id)
        log.info(f"Animation param selected", param=self.selected_param_id.name)
        
    def adjust_param(self, delta: int):
        """
        Adjust animation parameter for currently selected zone.

        Updates zone.state.animation.parameter_values and propagates change
        to running animation engine.
        """
        
        selected_zone = self.zone_service.get_selected_zone()
        if not selected_zone or selected_zone.state.mode != ZoneRenderMode.ANIMATION:
            return
        
        zone_animation = selected_zone.state.animation
        if not zone_animation:
            log.warn("adjust_param: zone has no animation")
            return
        
        selected_param_id = self.selected_param_id
        values = zone_animation.parameter_values
        
        if selected_param_id == ParamID.ANIM_SPEED:
            values[selected_param_id] = max(1, min(100, values.get(selected_param_id, 50) + delta))
            
            current_val = values.get(ParamID.ANIM_SPEED, 50)
            new_val = max(1, min(100, current_val + delta))
            
        elif selected_param_id == ParamID.ANIM_INTENSITY:
            values[selected_param_id] = max(0, min(100, values.get(selected_param_id, 100) + delta))
            
            current_val = values.get(ParamID.ANIM_INTENSITY, 100)
            new_val = max(0, min(100, current_val + delta))
            
        elif selected_param_id == ParamID.ANIM_PRIMARY_COLOR_HUE:
            values[selected_param_id] = (values.get(selected_param_id, 0) + delta * 10) % 360
            
            current_val = values.get(ParamID.ANIM_PRIMARY_COLOR_HUE, 0)
            new_val = (current_val + delta * 10) % 360
        else:
            log.warn(f"Unsupported animation parameter: {self.selected_param_id.name}")
            return
        
        log.info(
            "Animation param adjusted",
            zone=selected_zone.config.display_name,
            param=selected_param_id.name,
            value=values[selected_param_id],
        )
        
        asyncio.create_task(self._apply_parameter_change(selected_zone))
        
    async def _apply_parameter_change(self, zone: 'ZoneCombined'):
        """Apply parameter change to running animation in engine."""
        if not zone.state.animation:
            return

        await self._start_zone_animation(zone)
        
    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _start_zone_animation(self, zone: ZoneCombined) -> None:
        anim = zone.state.animation
        if not anim:
            return

        params = self.animation_service.build_params_for_zone(
            anim.id,
            anim.parameter_values,
            zone,
        )

        
        log.debug(
            "Starting animation",
            zone=zone.config.display_name,
            animation=anim.id.name,
            params=params,
        )
        
        await self.animation_engine.start_for_zone(
            zone.id,
            anim.id,
            Serializer.params_enum_to_str(params)
        )
        
    async def _ensure_animation_assigned(self, zone: ZoneCombined) -> None:
        if zone.state.animation or not self.available_animations:
            return

        from models.domain.animation import AnimationState
        first_anim = self.available_animations[0]
        zone.state.animation = AnimationState(id=first_anim, parameter_values={})

        log.info(
            "Auto-assigned animation",
            zone=zone.config.display_name,
            animation=first_anim.name,
        )
        
    
    def _get_selected_animation_zone(self) -> ZoneCombined | None:
        zone = self.zone_service.get_selected_zone()
        if not zone or zone.state.mode != ZoneRenderMode.ANIMATION:
            return None
        return zone