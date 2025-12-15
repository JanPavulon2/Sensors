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

    # --- Initialization ---

    async def initialize(self):
        """
        Initialize animation mode during app startup.

        Queries all ANIMATION zones and starts animations on them.
        Uses zone-specific animation parameters.

        If a zone is in ANIMATION mode but has no animation configured,
        automatically assigns the first available animation.
        """
        log.info("Initializing animation mode...")

        animated_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.ANIMATION)

        if not animated_zones:
            log.info("No animated zones to initialize")
            return

        log.info(f"AnimationMode init: {len(animated_zones)} zones")

        for zone in animated_zones:
            # Auto-assign first animation if zone has none configured
            if not zone.state.animation and self.available_animations:
                from models.domain.animation import AnimationState
                first_anim_id = self.available_animations[0]
                zone.state.animation = AnimationState(id=first_anim_id, parameter_values={})
                log.info(
                    "Auto-assigned animation to zone with no animation configured",
                    zone=zone.config.display_name,
                    animation=first_anim_id.name,
                )

            await self._start_zone_animation(zone)

        # Persist all changes after initialization
        self.zone_service.save_state()
            
        # ------------------------------------------------------------------

    def select_animation(self, delta: int) -> None:
        zone = self.zone_service.get_selected_zone()
        if not zone or zone.state.mode != ZoneRenderMode.ANIMATION:
            return

        self.selected_animation_index = (
            self.selected_animation_index + delta
        ) % len(self.available_animations)

        anim_id = self.available_animations[self.selected_animation_index]

        from models.domain.animation import AnimationState
        zone.state.animation = AnimationState(id=anim_id, parameter_values={})

        asyncio.create_task(self._start_zone_animation(zone))

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
        log.info(f"Static param cycled to {self.selected_param_id.name}")
        


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
        
        log.info(f"Adjusted {self.selected_param_id.name} to {new_val} for zone {selected_zone.config.display_name}")

        asyncio.create_task(self._apply_parameter_change(selected_zone))
        
        # Update zone state
        #current_zone.state.animation.parameter_values[self.selected_param_id] = new_val
        
    async def _apply_parameter_change(self, zone: 'ZoneCombined'):
        """Apply parameter change to running animation in engine."""
        if not zone.state.animation:
            return

        await self._start_zone_animation(zone)
        
        # anim_id = zone.state.animation.id

        # # Rebuild parameters with updated values
        # params = self.animation_service.build_params_for_zone(
        #     anim_id,
        #     zone.state.animation.parameter_values,
        #     zone
        # )

        # safe_params = Serializer.params_enum_to_str(params)

        # # Restart animation with new parameters
        # await self.animation_engine.start_for_zone(zone.config.id, anim_id, safe_params)
        # log.debug(f"Parameter change applied to zone {zone.config.id.name}")

        # tasks = []
        # zone_names_for_start = []
        # for zone in animated_zones:
        #     # Check if zone has animation configured
        #     if not zone.state.animation:
        #         log.warn(f"Zone {zone.config.display_name} is in ANIMATION mode but has no animation configured")
        #         continue

        #     anim_id = zone.state.animation.id

        #     # Build parameters for engine
        #     params = self.animation_service.build_params_for_zone(
        #         anim_id,
        #         zone.state.animation.parameter_values,
        #         zone
        #     )

        #     safe_params = Serializer.params_enum_to_str(params)
        #     tasks.append(self.animation_engine.start_for_zone(zone.config.id, anim_id, safe_params))
        #     zone_names_for_start.append(zone.config.display_name)

        #     log.info(f"Request start {anim_id.name} for zone {zone.config.id.name}")

        # try:
        #     # Kick off all starts concurrently
        #     if tasks:
        #         results = await asyncio.gather(*tasks, return_exceptions=True)
        #         failed = [r for r in results if isinstance(r, Exception)]
        #         log.info(f"Started animations on {len(zone_names_for_start)} zones: {zone_names_for_start}")
        #         if failed:
        #             log.error(f"Animation start failures: {len(failed)} tasks failed")
        #             for i, err in enumerate(failed):
        #                 log.error(f"  Task {i}: {err}")
        # except Exception as e:
        #     log.error(f"Error while initializing animations: {e}", exc_info=True)    
  
    # def select_animation(self, delta: int):
    #     """
    #     Cycle through available animations for currently selected zone.

    #     Updates the animation on the currently selected zone that's in ANIMATION mode,
    #     then applies the change to the animation engine.
    #     """
    #     if not self.available_animations:
    #         log.warn("No animations available")
    #         return

    #     # Get currently selected zone
    #     current_zone = self.zone_service.get_selected_zone()
    #     if not current_zone:
    #         log.warn("No zone selected")
    #         return

    #     # Only allow animation selection for zones in ANIMATION mode
    #     if current_zone.state.mode != ZoneRenderMode.ANIMATION:
    #         log.warn(f"Zone {current_zone.config.display_name} is not in ANIMATION mode")
    #         return

    #     # Cycle to next animation
    #     self.selected_animation_index = (self.selected_animation_index + delta) % len(self.available_animations)
    #     anim_id = self.available_animations[self.selected_animation_index]

    #     # Update zone's animation state
    #     from models.domain.animation import AnimationState
    #     current_zone.state.animation = AnimationState(
    #         id=anim_id,
    #         parameter_values={}
    #     )

    #     log.info(f"Selected animation for {current_zone.config.display_name}: {anim_id.name}")

    #     # Auto-start animation with defaults
    #     asyncio.create_task(self._apply_animation_to_zone(current_zone))

    # async def _apply_animation_to_zone(self, zone: 'ZoneCombined') -> None:
    #     """
    #     Apply current animation configuration to a specific zone.

    #     Builds parameters from zone state and starts animation in engine.
    #     """
    #     if not zone.state.animation:
    #         log.warn(f"Zone {zone.config.display_name} has no animation configured")
    #         return

    #     anim_id = zone.state.animation.id
    #     anim_params = zone.state.animation.parameter_values

    #     # Build parameters for engine
    #     params = self.animation_service.build_params_for_zone(anim_id, anim_params, zone)
    #     safe_params = Serializer.params_enum_to_str(params)

    #     # Start animation in engine
    #     await self.animation_engine.start_for_zone(zone.config.id, anim_id, safe_params)
    #     log.debug(f"Applied {anim_id.name} to zone {zone.config.id.name}")

    # async def toggle_animation(self):
    #     """
    #     Start or stop animations on all zones in ANIMATION render mode.
    #     If anything is running in engine.tasks -> stop_all, otherwise start all.
    #     """
    #     log.info("Toggle animation called")

    #     engine = self.animation_engine

    #     # if there are any running tasks, treat as "stop"
    #     if getattr(engine, "tasks", None) and len(engine.tasks) > 0:
    #         log.info("Stopping all running animations")
    #         await engine.stop_all()
    #         return

    #     # Otherwise start animations on all ANIMATION-mode zones
    #     animated_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.ANIMATION)
    #     if not animated_zones:
    #         log.warn("No zones in ANIMATION mode")
    #         return

    #     tasks = []
    #     for zone in animated_zones:
    #         # Check if zone has animation configured
    #         if not zone.state.animation:
    #             # Fallback to first available animation with defaults
    #             if not self.available_animations:
    #                 log.warn("No animations configured to start")
    #                 continue
    #             anim_id = self.available_animations[0]
    #             anim_params = {}
    #         else:
    #             anim_id = zone.state.animation.id
    #             anim_params = zone.state.animation.parameter_values

    #         # Build parameters for engine
    #         params = self.animation_service.build_params_for_zone(
    #             anim_id,
    #             anim_params,
    #             zone
    #         )

    #         safe_params = Serializer.params_enum_to_str(params)
    #         tasks.append(self.animation_engine.start_for_zone(zone.config.id, anim_id, safe_params))
    #         log.info(f"Starting {anim_id.name} on zone {zone.config.id.name}")

    #     if tasks:
    #         await asyncio.gather(*tasks, return_exceptions=True)
    #     log.info("Animation start calls completed")
        
    # # --- Parameter Adjustments ---
