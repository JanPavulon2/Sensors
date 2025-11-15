"""PowerToggleController - global power on/off feature"""

import asyncio
from typing import TYPE_CHECKING
from utils.logger import get_logger, LogCategory
from models.transition import TransitionConfig
from models.enums import MainMode

if TYPE_CHECKING:
    from controllers.led_controller.led_controller import LEDController

log = get_logger()


class PowerToggleController:
    """
    Global power on/off feature controller

    Responsibilities:
    - Toggle all zones on/off
    - Smooth fade transitions for power changes
    - Save/restore brightness state
    """

    def __init__(self, parent: "LEDController"):
        self.parent = parent
        self.zone_service = parent.zone_service
        self.animation_service = parent.animation_service
        self.strip_controller = parent.zone_strip_controller
        self.preview_panel_controller = parent.preview_panel_controller
        self.app_state = parent.app_state_service
        self.saved_brightness = {}  # Store brightness values during power off

    async def toggle(self):
        """Power on/off all zones with fade transition"""
        zones = self.zone_service.get_all()
        any_on = any(z.brightness > 0 for z in zones)

        if any_on:
            await self._power_off(zones)
        else:
            await self._power_on(zones)

    async def _power_off(self, zones):
        """Fade out and set all zones to 0 brightness (main strip + preview panel)"""
        # Save current brightness values before turning off
        self.saved_brightness = {
            zone.config.id: zone.brightness
            for zone in zones
        }

        # In ANIMATION mode: stop animation engine before fade
        if self.parent.main_mode == MainMode.ANIMATION:
            log.info(LogCategory.SYSTEM, "Power OFF in ANIMATION mode - stopping animation engine")
            if self.parent.animation_engine.is_running():
                # Stop animation WITHOUT fade (we'll fade the whole strip)
                await self.parent.animation_engine.stop(skip_fade=True)

        # In STATIC mode: stop pulse
        elif self.parent.main_mode == MainMode.STATIC:
            if self.parent.static_mode_controller.pulse_active:
                self.parent.static_mode_controller._stop_pulse()

        transition = TransitionConfig(duration_ms=800, steps=20)

        log.info(LogCategory.TRANSITION, "Power OFF - fading out main strip and preview")

        # Fade out main strip (uses TransitionService)
        fade_main = self.strip_controller.transition_service.fade_out(transition)

        # Fade out preview panel (delegate to PreviewPanelController)
        fade_preview = self.preview_panel_controller.transition_service.fade_out(transition)

        # Run both fades concurrently
        await asyncio.gather(fade_main, fade_preview)

        # Set brightness to 0
        for zone in zones:
            self.zone_service.set_brightness(zone.config.id, 0)

        log.info(LogCategory.SYSTEM, "Power OFF complete")

    async def _power_on(self, zones):
        """Restore brightness and fade in (main strip + preview panel)"""
        # Restore brightness values BEFORE building frame
        for zone in zones:
            saved = self.saved_brightness.get(zone.config.id, 100)  # Default to 100% if no saved value
            self.zone_service.set_brightness(zone.config.id, saved)

        transition_config = TransitionConfig(duration_ms=800, steps=20)

        # Build target frame with restored brightness
        color_map = {
            z.config.id.name: z.get_rgb()
            for z in zones
        }
        main_frame = self.strip_controller.zone_strip.build_frame_from_zones(color_map)

        log.info(LogCategory.TRANSITION, "Power ON - fading in main strip and preview")

        # In STATIC mode: fade in from the saved state
        if self.parent.main_mode == MainMode.STATIC:
            # Fade in main strip
            fade_main = self.strip_controller.transition_service.fade_in(main_frame, transition_config)

            # Fade in preview panel (delegate to PreviewPanelController)
            fade_preview = self.parent.preview_panel_controller.fade_in_for_power_on(duration_ms=800, steps=20)

            # Run both fades concurrently
            await asyncio.gather(fade_main, fade_preview)

        # In ANIMATION mode: restart animation with fade in
        elif self.parent.main_mode == MainMode.ANIMATION:
            log.info(LogCategory.SYSTEM, "Power ON in ANIMATION mode - restarting animation")
            current_anim = self.animation_service.get_current()
            if current_anim:
                anim_id = current_anim.config.id
                params = current_anim.build_params_for_engine()
                safe_params = {
                    (k.name if hasattr(k, "name") else str(k)): v for k, v in params.items()
                }
                # Start animation with fade in
                await self.parent.animation_engine.start(anim_id, **safe_params)
            else:
                # No animation selected - just fade in the main frame
                fade_main = self.strip_controller.transition_service.fade_in(main_frame, transition_config)
                fade_preview = self.parent.preview_panel_controller.fade_in_for_power_on(duration_ms=800, steps=20)
                await asyncio.gather(fade_main, fade_preview)

        log.info(LogCategory.SYSTEM, "Power ON complete")
