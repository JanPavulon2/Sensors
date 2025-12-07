"""
AnimationModeController - controls animation selection and parameter tuning
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from animations.breatheV2 import BreatheAnimationV2
from models.enums import FramePriority, FrameSource, ParamID, ZoneRenderMode
from models.domain.animation import AnimationID
from utils.logger import get_logger, LogCategory
from utils.serialization import Serializer
from services import ServiceContainer
from animations.engine_v2 import AnimationEngine

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
            a.config.id for a in self.animation_service.get_all()
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

        log.info(f"Found {len(animated_zones)} animated zones")

        tasks = []
        for zone in animated_zones:
            anim_id = zone.state.animation_id
            if not anim_id:
                # If zone has no saved animation, fallback to global current animation
                current_anim = self.animation_service.get_current()
                if current_anim:
                    anim_id = current_anim.config.id
                else:
                    log.warn(f"Zone {zone.config.display_name} has no animation_id and no global animation is configured")
                    continue
                
            # zone-specific params or fall back to animation's defaults packed for engine
            if zone.state.animation_parameters:
                params = zone.state.animation_parameters
            else:
                anim_combined = self.animation_service.get_animation(anim_id)
                params = anim_combined.build_params_for_engine(current_zone=zone)
                
            safe_params = Serializer.params_enum_to_str(params)
            # start per-zone
            
            tasks.append(self.animation_engine.start_for_zone(zone.config.id, anim_id, safe_params))
            
            log.info(f"Request start {anim_id.name} for zone {zone.config.id.name}")

        try:
            # Kick off all starts concurrently
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                log.info(f"Animation {anim_id.name} started on {len(animated_zones)} zone(s)")
        except Exception as e:
            log.error(f"Error while switching animation to {anim_id}: {e}", exc_info=True)    
            
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
        Cycle through available animations by encoder rotation.

        Sets animation in AnimationService and triggers running animation switch
        on all ANIMATION-mode zones.
        """
        if not self.available_animations:
            log.warn("No animations available")
            return

        self.selected_animation_index = (self.selected_animation_index + delta) % len(self.available_animations)
        anim_id = self.available_animations[self.selected_animation_index]

        self.animation_service.set_current(anim_id)
        log.info(f"Selected animation: {anim_id.name}")

        # Auto-start/switch animation on all ANIMATION zones
        asyncio.create_task(self._switch_to_selected_animation())

    async def _switch_to_selected_animation(self):
        """
        Switch to currently selected animation on all ANIMATION-mode zones.
        """
        animated_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.ANIMATION)
        if not animated_zones:
            log.warn("No zones in ANIMATION mode")
            return

        anim_id = self.animation_service.get_current().config.id if self.animation_service.get_current() else None
        if not anim_id:
            log.warn("No global current animation available for switching")
            return

        # Build and start new animation on every animated zone (stop old first)
        tasks = []
        for zone in animated_zones:
            # Stop per-zone if running (engine.stop_for_zone is idempotent)
            # Determine params: zone-specific override or animation defaults
            if zone.state.animation_parameters:
                params = zone.state.animation_parameters
            else:
                anim_combined = self.animation_service.get_animation(anim_id)
                params = anim_combined.build_params_for_engine(current_zone=zone)

            safe_params = Serializer.params_enum_to_str(params)

            # Stop existing & start new — engine.start_for_zone will stop previous if needed
            tasks.append(self.animation_engine.start_for_zone(zone.config.id, anim_id, safe_params))

            log.debug(f"Switching zone {zone.config.id.name} to {anim_id.name}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        log.info(f"Switched animation to {anim_id.name} on {len(animated_zones)} zones")

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
            anim_id = zone.state.animation_id
            if not anim_id:
                # fallback to global selected animation
                current_anim = self.animation_service.get_current()
                if not current_anim:
                    log.warn("No animation configured to start")
                    continue
                anim_id = current_anim.config.id

            if zone.state.animation_parameters:
                params = zone.state.animation_parameters
            else:
                anim_combined = self.animation_service.get_animation(anim_id)
                params = anim_combined.build_params_for_engine(current_zone=zone)

            safe_params = Serializer.params_enum_to_str(params)
            tasks.append(self.animation_engine.start_for_zone(zone.config.id, anim_id, safe_params))
            log.info(f"Starting {anim_id.name} on zone {zone.config.id.name}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        log.info("Animation start calls completed")
        
    # --- Parameter Adjustments ---

    def adjust_param(self, delta: int):
        current_anim = self.animation_service.get_current()
        if not current_anim:
            return

        pid = self.current_param
        if pid not in current_anim.parameters:
            return

        self.animation_service.adjust_parameter(current_anim.config.id, pid, delta)
        new_value = current_anim.get_param_value(pid)

        # Propagate param changes to all zones that currently run this animation
        engine = self.animation_engine
        if engine and getattr(engine, "tasks", None):
            # update for every zone where current animation matches
            for zone_id, anim_id in list(engine.active_anim_ids.items()):
                # if we only want to update zones running the current animation, check equality
                if anim_id == current_anim.config.id:
                    # param key name should be string for engine; keep param enum conversion
                    key = pid.name if hasattr(pid, "name") else str(pid)
                    engine.update_param(zone_id, key, new_value)

        log.info(f"Adjusted {pid.name} → {new_value}")
    #     engine = self.animation_engine
    #     if engine and engine.is_running():
    #         if pid == ParamID.ANIM_SPEED:
    #             engine.update_param("speed", new_value)
    #         elif pid == ParamID.ANIM_INTENSITY:
    #             engine.update_param("intensity", new_value)
    #         elif pid == ParamID.ANIM_PRIMARY_COLOR_HUE:
    #             engine.update_param("hue", new_value)

    #     log.info(f"Adjusted {pid.name} → {new_value}")

    # def cycle_param(self):
    #     params = [ParamID.ANIM_SPEED, ParamID.ANIM_INTENSITY]
    #     idx = params.index(self.current_param)
    #     self.current_param = params[(idx + 1) % len(params)]
    #     self.app_state_service.set_current_param(self.current_param)

    #     log.info(f"Cycled animation param: {self.current_param.name}")
