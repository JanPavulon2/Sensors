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
        Uses zone-specific animation parameters saved in ZoneState.

        Current limitation: Only ONE animation can run at a time.
        If multiple zones are in ANIMATION mode, only the first one will animate.
        """
        log.info("Initializing ANIMATION mode...")

        animated_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.ANIMATION)
        if not animated_zones:
            log.info("ANIMATION: No animated zones to initialize")
            return

        log.info(f"ANIMATION: Found {len(animated_zones)} animated zones")

        if len(animated_zones) > 1:
            log.warn(
                f"ANIMATION: Multiple zones in ANIMATION mode ({[z.config.id.name for z in animated_zones]}), "
                f"only animating {animated_zones[0].config.id.name} (architecture limitation)"
            )

        # Only animate the first zone in ANIMATION mode
        first_animated_zone = animated_zones[0]

        # Get animation to run: use zone's saved animation settings
        anim_id = first_animated_zone.state.animation_id
        if not anim_id:
            # Zone has no saved animation, try to use current or auto-select
            current_anim = self.animation_service.get_current()
            if not current_anim:
                if not self.available_animations:
                    log.warn("ANIMATION: No animations available to start")
                    return
                # Auto-select first animation
                first_anim_id = self.available_animations[0]
                self.animation_service.set_current(first_anim_id)
                current_anim = self.animation_service.get_current()
                anim_id = first_anim_id
                log.info(f"ANIMATION: Auto-selected {first_anim_id.name}")
            else:
                anim_id = current_anim.config.id

        # Build excluded zones list (all zones except the animated one)
        excluded_zone_ids = [
            z.config.id for z in self.zone_service.get_all()
            if z.config.id != first_animated_zone.config.id
        ]

        # Use zone's saved animation parameters if available, otherwise use current animation's parameters
        zone_params = first_animated_zone.state.animation_parameters
        if zone_params:
            params = zone_params
        else:
            # Fall back to current animation's parameters if no zone params are saved
            current_anim = self.animation_service.get_current()
            if current_anim:
                params = current_anim.build_params_for_engine()
            else:
                params = {}

        safe_params = Serializer.params_enum_to_str(params)

        log.info(f"ANIMATION: Starting {anim_id.name} on zone {first_animated_zone.config.id.name}")
        await self.animation_engine.start(anim_id, excluded_zones=excluded_zone_ids, **safe_params)
        log.info(f"ANIMATION initialized: {anim_id.name} running on {first_animated_zone.config.id.name}")

    # --- Mode Entry/Exit ---

    def enter_mode(self):
        """
        Initialize or resume animation preview and auto-start animation.

        Per-zone mode: Start animation on all zones with ANIMATION render mode.
        """
        # Auto-start animation if not already running
        if not self.animation_engine.is_running():
            asyncio.create_task(self.toggle_animation())

    async def exit_mode(self):
        """
        Exit animation mode: stop running animation and cleanup

        Called when switching away from ANIMATION mode.
        NOTE: Caller (_toggle_main_mode) handles fade_out, so we skip it here.
        """
        log.info("Exiting ANIMATION mode")
        if self.animation_engine.is_running():
            await self.animation_engine.stop(skip_fade=True)

    def on_edit_mode_change(self, enabled: bool):
        """No pulse here"""
        log.debug(f"Edit mode={enabled} (no pulse in ANIMATION mode)")

    # --- Animation Selection ---

    def select_animation(self, delta: int):
        """
        Cycle through available animations by encoder rotation.

        Automatically starts/switches to selected animation on main strip.
        """
        if not self.available_animations:
            log.warn("No animations available")
            return

        self.selected_animation_index = (self.selected_animation_index + delta) % len(self.available_animations)
        anim_id = self.available_animations[self.selected_animation_index]

        self.animation_service.set_current(anim_id)
        log.info(f"Selected animation: {anim_id.name}")

        # Auto-start/switch animation on main strip
        asyncio.create_task(self._switch_to_selected_animation())

    async def _switch_to_selected_animation(self):
        """
        Switch to currently selected animation (with transition).

        Per-zone mode: Animate all zones with ANIMATION render mode using their animations.
        """
        # Get all zones in ANIMATION render mode
        animated_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.ANIMATION)
        if not animated_zones:
            log.warn("No zones in ANIMATION mode")
            return

        # Use first animated zone's animation (TODO: support different animations per zone)
        first_animated_zone = animated_zones[0]
        anim_id = first_animated_zone.state.animation_id
        if not anim_id:
            log.warn(f"Zone {first_animated_zone.config.display_name} in ANIMATION mode but no animation_id set")
            return

        zone_params = first_animated_zone.state.animation_parameters or {}
        params = zone_params if zone_params else {}
        log.info(f"Auto-switching to animation: {anim_id.name}")
        safe_params = Serializer.params_enum_to_str(params)

        # Build list of zones to exclude: ALL zones except animated zones
        animated_zone_ids = {z.config.id for z in animated_zones}
        excluded_zone_ids = [
            z.config.id for z in self.zone_service.get_all()
            if z.config.id not in animated_zone_ids
        ]

        log.debug(f"Animation on {len(animated_zones)} zone(s), excluded: {[z.name for z in excluded_zone_ids]}")

        # AnimationEngine.start() will handle stop → fade_out → fade_in → start
        await self.animation_engine.start(anim_id, excluded_zones=excluded_zone_ids, **safe_params)

    async def toggle_animation(self):
        """
        Start or stop animation.

        Per-zone mode: Animate all zones with ANIMATION render mode using their individual animations.
        """
        log.info("Toggle animation called")

        engine = self.animation_engine

        if engine and engine.is_running():
            log.info(f"Stopping running animation: {engine.get_current_animation_id().name}")
            await engine.stop()
            return

        # Get all zones in ANIMATION render mode
        animated_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.ANIMATION)
        if not animated_zones:
            log.warn("No zones in ANIMATION mode")
            return

        # For now: use first animated zone's animation (TODO: support different animations per zone)
        first_animated_zone = animated_zones[0]
        anim_id = first_animated_zone.state.animation_id
        if not anim_id:
            log.warn(f"Zone {first_animated_zone.config.display_name} in ANIMATION mode but no animation_id set")
            return

        # Get animation parameters from the zone (or fall back to defaults)
        zone_params = first_animated_zone.state.animation_parameters or {}
        params = zone_params if zone_params else {}
        log.info(f"Starting animation: {anim_id.name} on {len(animated_zones)} zone(s)")
        safe_params = Serializer.params_enum_to_str(params)

        # Build list of zones to exclude: ALL zones except animated zones
        animated_zone_ids = {z.config.id for z in animated_zones}
        excluded_zone_ids = [
            z.config.id for z in self.zone_service.get_all()
            if z.config.id not in animated_zone_ids
        ]

        log.debug(f"Animated zones: {[z.config.id.name for z in animated_zones]}, excluded: {[z.name for z in excluded_zone_ids]}")

        await self.animation_engine.start(anim_id, excluded_zones=excluded_zone_ids, **safe_params)

        log.info("Animation start call completed")

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

        engine = self.animation_engine
        if engine and engine.is_running():
            if pid == ParamID.ANIM_SPEED:
                engine.update_param("speed", new_value)
            elif pid == ParamID.ANIM_INTENSITY:
                engine.update_param("intensity", new_value)
            elif pid == ParamID.ANIM_PRIMARY_COLOR_HUE:
                engine.update_param("hue", new_value)

        log.info(f"Adjusted {pid.name} → {new_value}")

    def cycle_param(self):
        params = [ParamID.ANIM_SPEED, ParamID.ANIM_INTENSITY]
        idx = params.index(self.current_param)
        self.current_param = params[(idx + 1) % len(params)]
        self.app_state_service.set_current_param(self.current_param)

        log.info(f"Cycled animation param: {self.current_param.name}")
