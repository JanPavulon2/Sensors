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
        Called once during LightingController initialization.

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

        # Get current animation from state or auto-select first available
        current_anim = self.animation_service.get_current()
        if not current_anim:
            if not self.available_animations:
                log.warn("ANIMATION: No animations available to start")
                return
            # Auto-select first animation
            first_anim_id = self.available_animations[0]
            self.animation_service.set_current(first_anim_id)
            current_anim = self.animation_service.get_current()
            log.info(f"ANIMATION: Auto-selected {first_anim_id.name}")

        # Build excluded zones list (all zones except the animated one)
        excluded_zone_ids = [
            z.config.id for z in self.zone_service.get_all()
            if z.config.id != first_animated_zone.config.id
        ]

        # Start animation
        anim_id = current_anim.config.id
        params = current_anim.build_params_for_engine()
        safe_params = Serializer.params_enum_to_str(params)

        log.info(f"ANIMATION: Starting {anim_id.name} on zone {first_animated_zone.config.id.name}")
        await self.animation_engine.start(anim_id, excluded_zones=excluded_zone_ids, **safe_params)
        log.info(f"ANIMATION initialized: {anim_id.name} running on {first_animated_zone.config.id.name}")

    # --- Mode Entry/Exit ---

    def enter_mode(self):
        """Initialize or resume animation preview and auto-start animation"""
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
        Switch main strip to currently selected animation (with transition).

        Per-zone mode: Only animate the currently selected zone.
        All other zones are excluded from animation.
        """
        current_anim = self.animation_service.get_current()
        if not current_anim:
            return

        anim_id = current_anim.config.id
        params = current_anim.build_params_for_engine()

        log.info(f"Auto-switching to animation: {anim_id.name}")
        safe_params = Serializer.params_enum_to_str(params)

        # Get the currently selected zone
        selected_zone = self.zone_service.get_selected_zone()
        if not selected_zone:
            log.warn("No zone selected for animation")
            return

        # Build list of zones to exclude: ALL zones except the selected one
        excluded_zone_ids = [
            zone.config.id for zone in self.zone_service.get_all()
            if zone.config.id != selected_zone.config.id
        ]

        log.debug(f"Animation on selected zone {selected_zone.config.id.name}, excluded: {[z.name for z in excluded_zone_ids]}")

        # AnimationEngine.start() will handle stop → fade_out → fade_in → start
        await self.animation_engine.start(anim_id, excluded_zones=excluded_zone_ids, **safe_params)

    async def toggle_animation(self):
        """
        Start or stop the currently selected animation.

        Per-zone mode: Only animate the currently selected zone.
        """
        log.info("Toggle animation called")

        current_anim = self.animation_service.get_current()
        if not current_anim:
            log.warn("No animation selected")
            return

        engine = self.animation_engine

        if engine and engine.is_running():
            log.info(f"Stopping running animation: {engine.get_current_animation_id().name}")
            await engine.stop()
            return

        # Get the currently selected zone
        selected_zone = self.zone_service.get_selected_zone()
        if not selected_zone:
            log.warn("No zone selected for animation")
            return

        anim_id = current_anim.config.id
        params = current_anim.build_params_for_engine()
        log.info(f"Starting animation: {anim_id.name} ({params})")
        safe_params = Serializer.params_enum_to_str(params)

        # Build list of zones to exclude: ALL zones except the selected one
        excluded_zone_ids = [
            zone.config.id for zone in self.zone_service.get_all()
            if zone.config.id != selected_zone.config.id
        ]

        log.debug(f"Animation on selected zone {selected_zone.config.id.name}, excluded: {[z.name for z in excluded_zone_ids]}")

        # Only animate the selected zone
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
