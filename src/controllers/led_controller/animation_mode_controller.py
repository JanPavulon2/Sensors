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
from animations.engine_v2 import AnimationEngine

if TYPE_CHECKING:
    from models.domain.zone import ZoneCombined

log = get_logger().for_category(LogCategory.GENERAL)


class AnimationModeController:
    def __init__(
        self,
        services: ServiceContainer,
        animation_engine: AnimationEngine
    ):
        """
        Initialize animation mode controller with dependency injection.

        Args:
            services: ServiceContainer with all core services and managers
            animation_engine: AnimationEngine for running animations
        """
        self.animation_service = services.animation_service
        self.app_state_service = services.app_state_service
        self.zone_service = services.zone_service
        self.animation_engine = animation_engine

        # Use saved param if it's an animation param, otherwise default to ANIM_SPEED
        saved_param = self.app_state_service.get_state().current_param
        anim_params = [ParamID.ANIM_SPEED, ParamID.ANIM_INTENSITY]
        self.current_param = saved_param if saved_param in anim_params else ParamID.ANIM_SPEED

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
        """
        
        log.info("Initializing animation mode...")

        animated_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.ANIMATION)
        if not animated_zones:
            log.info("No animated zones to initialize")
            return

        log.info(f"Found {len(animated_zones)} animated zones: {[z.config.display_name for z in animated_zones]}")

        tasks = []
        zone_names_for_start = []
        for zone in animated_zones:
            # Check if zone has animation configured
            if not zone.state.animation:
                log.warn(f"Zone {zone.config.display_name} is in ANIMATION mode but has no animation configured")
                continue

            anim_id = zone.state.animation.id

            # Build parameters for engine
            params = self.animation_service.build_params_for_zone(
                anim_id,
                zone.state.animation.parameter_values,
                zone
            )

            safe_params = Serializer.params_enum_to_str(params)
            tasks.append(self.animation_engine.start_for_zone(zone.config.id, anim_id, safe_params))
            zone_names_for_start.append(zone.config.display_name)

            log.info(f"Request start {anim_id.name} for zone {zone.config.id.name}")

        try:
            # Kick off all starts concurrently
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                failed = [r for r in results if isinstance(r, Exception)]
                log.info(f"Started animations on {len(zone_names_for_start)} zones: {zone_names_for_start}")
                if failed:
                    log.error(f"Animation start failures: {len(failed)} tasks failed")
                    for i, err in enumerate(failed):
                        log.error(f"  Task {i}: {err}")
        except Exception as e:
            log.error(f"Error while initializing animations: {e}", exc_info=True)    
            
    # --- Mode Entry/Exit ---

    def enter_mode(self):
        """
        Initialize or resume animation preview and auto-start animation.
        If engine already runs something, skip starting duplicate.
        """
        # Auto-start animation if not already running (engine decides duplicates)
        if not getattr(self.animation_engine, "tasks", None):
            asyncio.create_task(self.toggle_animation())
             
    async def exit_mode(self):
        """
        Exit animation mode: stop running animations and cleanup.
        """
        log.info("Exiting ANIMATION mode")
        # stop all per-zone animations
        await self.animation_engine.stop_all()
        
    def on_edit_mode_change(self, enabled: bool):
        """No pulse here"""
        log.debug(f"Edit mode={enabled} (no pulse in ANIMATION mode)")

    # --- Animation Selection ---

    def select_animation(self, delta: int):
        """
        Cycle through available animations for currently selected zone.

        Updates the animation on the currently selected zone that's in ANIMATION mode,
        then applies the change to the animation engine.
        """
        if not self.available_animations:
            log.warn("No animations available")
            return

        # Get currently selected zone
        current_zone = self.zone_service.get_selected_zone()
        if not current_zone:
            log.warn("No zone selected")
            return

        # Only allow animation selection for zones in ANIMATION mode
        if current_zone.state.mode != ZoneRenderMode.ANIMATION:
            log.warn(f"Zone {current_zone.config.display_name} is not in ANIMATION mode")
            return

        # Cycle to next animation
        self.selected_animation_index = (self.selected_animation_index + delta) % len(self.available_animations)
        anim_id = self.available_animations[self.selected_animation_index]

        # Update zone's animation state
        from models.domain.animation import AnimationState
        current_zone.state.animation = AnimationState(
            id=anim_id,
            parameter_values={}
        )

        log.info(f"Selected animation for {current_zone.config.display_name}: {anim_id.name}")

        # Auto-start animation with defaults
        asyncio.create_task(self._apply_animation_to_zone(current_zone))

    async def _apply_animation_to_zone(self, zone: 'ZoneCombined') -> None:
        """
        Apply current animation configuration to a specific zone.

        Builds parameters from zone state and starts animation in engine.
        """
        if not zone.state.animation:
            log.warn(f"Zone {zone.config.display_name} has no animation configured")
            return

        anim_id = zone.state.animation.id
        anim_params = zone.state.animation.parameter_values

        # Build parameters for engine
        params = self.animation_service.build_params_for_zone(anim_id, anim_params, zone)
        safe_params = Serializer.params_enum_to_str(params)

        # Start animation in engine
        await self.animation_engine.start_for_zone(zone.config.id, anim_id, safe_params)
        log.debug(f"Applied {anim_id.name} to zone {zone.config.id.name}")

    async def toggle_animation(self):
        """
        Start or stop animations on all zones in ANIMATION render mode.
        If anything is running in engine.tasks -> stop_all, otherwise start all.
        """
        log.info("Toggle animation called")

        engine = self.animation_engine

        # if there are any running tasks, treat as "stop"
        if getattr(engine, "tasks", None) and len(engine.tasks) > 0:
            log.info("Stopping all running animations")
            await engine.stop_all()
            return

        # Otherwise start animations on all ANIMATION-mode zones
        animated_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.ANIMATION)
        if not animated_zones:
            log.warn("No zones in ANIMATION mode")
            return

        tasks = []
        for zone in animated_zones:
            # Check if zone has animation configured
            if not zone.state.animation:
                # Fallback to first available animation with defaults
                if not self.available_animations:
                    log.warn("No animations configured to start")
                    continue
                anim_id = self.available_animations[0]
                anim_params = {}
            else:
                anim_id = zone.state.animation.id
                anim_params = zone.state.animation.parameter_values

            # Build parameters for engine
            params = self.animation_service.build_params_for_zone(
                anim_id,
                anim_params,
                zone
            )

            safe_params = Serializer.params_enum_to_str(params)
            tasks.append(self.animation_engine.start_for_zone(zone.config.id, anim_id, safe_params))
            log.info(f"Starting {anim_id.name} on zone {zone.config.id.name}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        log.info("Animation start calls completed")
        
    # --- Parameter Adjustments ---

    def adjust_param(self, delta: int):
        """
        Adjust animation parameter for currently selected zone.

        Updates zone.state.animation.parameter_values and propagates change
        to running animation engine.
        """
        # Get current zone from app state
        current_index = self.app_state_service.get_state().current_zone_index
        all_zones = self.zone_service.get_all()
        if current_index >= len(all_zones):
            log.warn(f"Invalid zone index: {current_index}")
            return

        current_zone = all_zones[current_index]

        # Only adjust if zone has animation
        if not current_zone.state.animation:
            log.warn(f"Zone {current_zone.config.display_name} has no animation to adjust")
            return

        # Determine parameter bounds based on selected parameter
        if self.current_param == ParamID.ANIM_SPEED:
            current_val = current_zone.state.animation.parameter_values.get(ParamID.ANIM_SPEED, 50)
            new_val = max(1, min(100, current_val + delta))
        elif self.current_param == ParamID.ANIM_INTENSITY:
            current_val = current_zone.state.animation.parameter_values.get(ParamID.ANIM_INTENSITY, 100)
            new_val = max(0, min(100, current_val + delta))
        elif self.current_param == ParamID.ANIM_PRIMARY_COLOR_HUE:
            current_val = current_zone.state.animation.parameter_values.get(ParamID.ANIM_PRIMARY_COLOR_HUE, 0)
            new_val = (current_val + delta * 10) % 360
        else:
            log.warn(f"Unsupported animation parameter: {self.current_param.name}")
            return

        # Update zone state
        current_zone.state.animation.parameter_values[self.current_param] = new_val

        # Propagate to running animation engine
        asyncio.create_task(self._apply_parameter_change(current_zone))

        log.info(f"Adjusted {self.current_param.name} to {new_val} for zone {current_zone.config.display_name}")

    async def _apply_parameter_change(self, zone: 'ZoneCombined'):
        """Apply parameter change to running animation in engine."""
        if not zone.state.animation:
            return

        anim_id = zone.state.animation.id

        # Rebuild parameters with updated values
        params = self.animation_service.build_params_for_zone(
            anim_id,
            zone.state.animation.parameter_values,
            zone
        )

        safe_params = Serializer.params_enum_to_str(params)

        # Restart animation with new parameters
        await self.animation_engine.start_for_zone(zone.config.id, anim_id, safe_params)
        log.debug(f"Parameter change applied to zone {zone.config.id.name}")
