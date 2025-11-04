"""
AnimationModeController - controls animation selection and parameter tuning
"""

import asyncio
from controllers.preview_panel_controller import PreviewPanelController
from models.enums import ParamID, PreviewMode
from utils.logger import get_logger, LogCategory, LogLevel
from services import AnimationService, ApplicationStateService

log = get_logger()


class AnimationModeController:
    def __init__(self, parent):
        self.parent = parent
        self.animation_service: AnimationService = parent.animation_service
        self.animation_engine = parent.animation_engine
        self.preview_panel_controller: PreviewPanelController = parent.preview_panel_controller
        self.app_state = parent.app_state_service

        self.current_param = self.app_state.get_state().current_param
        self.available_animations = [
            a.config.id for a in self.animation_service.get_all()
        ]
        self.selected_animation_index = 0

    # --- Mode Entry/Exit ---

    def enter_mode(self):
        """Initialize or resume animation preview"""
        self._sync_preview()

    def on_edit_mode_change(self, enabled: bool):
        """No pulse here"""
        log.debug(LogCategory.SYSTEM, f"Edit mode={enabled} (no pulse in ANIMATION mode)")

    # --- Animation Selection ---

    def select_animation(self, delta: int):
        self.selected_animation_index = (
            self.selected_animation_index + delta
        ) % len(self.available_animations)
        anim_id = self.available_animations[self.selected_animation_index]
        self.animation_service.set_current(anim_id)
        self._sync_preview()
        log.animation(f"Selected animation: {anim_id.name}")

    async def toggle_animation(self):
        """Start or stop current animation"""
        current_anim = self.animation_service.get_current()
        if not current_anim:
            log.warn(LogCategory.ANIMATION, "No animation selected")
            return

        if self.parent.animation_engine and self.parent.animation_engine.is_running():
            await self.parent.animation_engine.stop()
        else:
            await self.parent.start_animation()

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

        # Propagate live update to animation engine
        if self.parent.animation_engine and self.parent.animation_engine.is_running():
            param_map = {
                ParamID.ANIM_SPEED: "speed",
                ParamID.ANIM_INTENSITY: "intensity",
            }
            if pid in param_map:
                self.parent.animation_engine.update_param(param_map[pid], new_value)

        log.animation(f"Adjusted {pid.name} → {new_value}")
        self._sync_preview()

    def cycle_param(self):
        params = [ParamID.ANIM_SPEED, ParamID.ANIM_INTENSITY]
        idx = params.index(self.current_param)
        self.current_param = params[(idx + 1) % len(params)]
        self.app_state.set_current_param(self.current_param)
        self._sync_preview()
        log.info(LogCategory.SYSTEM, f"Cycled animation param: {self.current_param.name}")

    def _sync_preview(self):
        anim = self.animation_service.get_current()
        if anim:
            speed = anim.get_param_value(ParamID.ANIM_SPEED)
            hue = anim.get_param_value(ParamID.ANIM_PRIMARY_COLOR_HUE)
            self.preview_panel_controller.start_animation_preview("snake", speed=speed, hue=hue)
