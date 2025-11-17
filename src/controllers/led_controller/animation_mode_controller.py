"""
AnimationModeController - controls animation selection and parameter tuning
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from models.enums import ParamID, PreviewMode
from utils.logger import get_logger, LogCategory, LogLevel
from services import ServiceContainer
from animations.engine import AnimationEngine

if TYPE_CHECKING:
    from controllers.preview_panel_controller import PreviewPanelController

log = get_logger().for_category(LogCategory.GENERAL)


class AnimationModeController:
    def __init__(
        self,
        services: ServiceContainer,
        animation_engine: AnimationEngine,
        preview_panel: PreviewPanelController,
    ):
        """
        Initialize animation mode controller with dependency injection.

        Args:
            services: ServiceContainer with all core services and managers
            animation_engine: AnimationEngine for running animations
            preview_panel: PreviewPanelController for preview display
        """
        self.animation_service = services.animation_service
        self.app_state_service = services.app_state_service
        self.zone_service = services.zone_service
        self.animation_engine = animation_engine
        self.preview_panel_controller = preview_panel

        # Use saved param if it's an animation param, otherwise default to ANIM_SPEED
        saved_param = self.app_state_service.get_state().current_param
        anim_params = [ParamID.ANIM_SPEED, ParamID.ANIM_INTENSITY]
        self.current_param = saved_param if saved_param in anim_params else ParamID.ANIM_SPEED

        self.available_animations = [
            a.config.id for a in self.animation_service.get_all()
        ]
        self.selected_animation_index = 0

    # --- Mode Entry/Exit ---

    def enter_mode(self):
        """Initialize or resume animation preview and auto-start animation"""
        self._sync_preview()

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

        # Auto-start/switch animation on main strip (always, regardless of current state)
        asyncio.create_task(self._switch_to_selected_animation())

        self._sync_preview()

    async def _switch_to_selected_animation(self):
        """Switch main strip to currently selected animation (with transition)."""
        current_anim = self.animation_service.get_current()
        if not current_anim:
            return

        anim_id = current_anim.config.id
        params = current_anim.build_params_for_engine()

        log.info(f"Auto-switching to animation: {anim_id.name}")
        safe_params = {
            (k.name if hasattr(k, "name") else str(k)): v for k, v in params.items()
        }

        # AnimationEngine.start() will handle stop → fade_out → fade_in → start
        await self.animation_engine.start(anim_id, **safe_params)

    async def toggle_animation(self):
        """Start or stop the currently selected animation."""
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

        anim_id = current_anim.config.id
        params = current_anim.build_params_for_engine()
        
        # Build parameters dynamically
        params = current_anim.build_params_for_engine()
        log.info(f"Starting animation: {anim_id.name} ({params})")
        safe_params = {
            (k.name if hasattr(k, "name") else str(k)): v for k, v in params.items()
        }
        await self.animation_engine.start(anim_id, **safe_params)

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
                
        # Propagate live update to animation engine
        # if self.parent.animation_engine and self.parent.animation_engine.is_running():
        #     param_map = {
        #         ParamID.ANIM_SPEED: "speed",
        #         ParamID.ANIM_INTENSITY: "intensity",
        #     }
        #     if pid in param_map:
        #         self.parent.animation_engine.update_param(param_map[pid], new_value)

        log.info(f"Adjusted {pid.name} → {new_value}")
        self._sync_preview()

    def cycle_param(self):
        params = [ParamID.ANIM_SPEED, ParamID.ANIM_INTENSITY]
        idx = params.index(self.current_param)
        self.current_param = params[(idx + 1) % len(params)]
        self.app_state_service.set_current_param(self.current_param)
        self._sync_preview()
        log.info(f"Cycled animation param: {self.current_param.name}")

    # ------------------------------------------------------------------
    # Preview management
    # ------------------------------------------------------------------

    def _sync_preview(self):
        anim = self.animation_service.get_current()
        if not anim:
            # Fallback: select first available animation if none is current
            if self.available_animations:
                default_id = self.available_animations[0]
                log.info(f"No current animation, defaulting to {default_id.name}")
                self.animation_service.set_current(default_id)
                anim = self.animation_service.get_current()
            else:
                log.error("No animations available!")
                return

        anim_id = anim.config.id

        # Get first zone for color reference (used by BREATHE, COLOR_FADE, etc.)
        zones = self.zone_service.get_all()
        current_zone = zones[0] if zones else None

        params = anim.build_params_for_engine(current_zone)
        safe_params = {
            (k.name if hasattr(k, "name") else str(k)): v for k, v in params.items()
        }
        try:
            self.preview_panel_controller.start_animation_preview(anim_id, **safe_params)
            log.debug(f"Preview synced for {anim_id.name}")
        except Exception as e:
            log.warn(f"Failed to start preview for {anim_id.name}: {e}")
            
