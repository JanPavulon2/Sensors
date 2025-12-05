"""PowerToggleController - global power on/off feature"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from utils.logger import get_logger, LogCategory
from utils.serialization import Serializer
from models.transition import TransitionConfig
from models.enums import ZoneRenderMode
from services import ServiceContainer

if TYPE_CHECKING:
    from controllers.preview_panel_controller import PreviewPanelController

log = get_logger().for_category(LogCategory.GENERAL)


class PowerToggleController:
    """
    Global power on/off feature controller

    Responsibilities:
    - Toggle all zones on/off
    - Smooth fade transitions for power changes
    - Save/restore brightness state
    """

    def __init__(
        self,
        services: ServiceContainer,
        preview_panel: PreviewPanelController,
        animation_engine,
        static_mode_controller,
    ):
        """
        Initialize power toggle controller with dependency injection.

        Args:
            services: ServiceContainer with all core services and managers
            preview_panel: PreviewPanelController for preview display
            animation_engine: AnimationEngine for animation control
            static_mode_controller: StaticModeController for pulse control
        """
        self.zone_service = services.zone_service
        self.animation_service = services.animation_service
        self.preview_panel_controller = preview_panel
        self.app_state = services.app_state_service
        self.animation_engine = animation_engine
        self.static_mode_controller = static_mode_controller
        self.frame_manager = services.frame_manager
        self.saved_brightness = {}

    async def toggle(self):
        """Power on/off all zones with fade transition"""
        zones = self.zone_service.get_all()
        any_on = any(z.brightness > 0 for z in zones)

        if any_on:
            await self._power_off(zones)
        else:
            await self._power_on(zones)

    async def _power_off(self, zones):
        """Fade out and set all zones to 0 brightness (all GPIO strips + preview panel)"""
        # Save current brightness values before turning off
        self.saved_brightness = {
            zone.config.id: zone.brightness
            for zone in zones
        }

        # Stop animation engine if running
        if self.animation_engine.is_running():
            log.info("Power OFF - stopping animation engine")
            await self.animation_engine.stop(skip_fade=True)

        # Stop pulse from static mode
        if self.static_mode_controller.pulse_active:
            self.static_mode_controller._stop_pulse()

        transition = TransitionConfig(duration_ms=800, steps=20)

        log.info("Power OFF - fading out all GPIO strips and preview")

        # Fade out each GPIO strip
        fades = []
        # TODO: Use frame_manager.zone_strips for per-strip fades
        # for gpio, strip_controller in self.strip_controllers.items():
        #     fade = strip_controller.transition_service.fade_out(transition)
        #     fades.append(fade)

        # Fade out preview panel (if available)
        if self.preview_panel_controller:
            fade_preview = self.preview_panel_controller.transition_service.fade_out(transition)
            fades.append(fade_preview)

        # Run all fades concurrently
        await asyncio.gather(*fades)

        # Set brightness to 0
        for zone in zones:
            self.zone_service.set_brightness(zone.config.id, 0)

        log.info("Power OFF complete")

    async def _power_on(self, zones):
        """Restore brightness and fade in all GPIO strips (all GPIO strips + preview panel)"""
        # Restore brightness values BEFORE building frames
        for zone in zones:
            saved = self.saved_brightness.get(zone.config.id, 100)
            self.zone_service.set_brightness(zone.config.id, saved)

        transition_config = TransitionConfig(duration_ms=1700, steps=20)

        # Build target frame with restored brightness (static zones only)
        # Use Color objects with brightness applied (preserves color mode)
        color_map = {
            z.config.id: z.state.color.with_brightness(z.brightness)
            for z in zones
            if z.state.mode == ZoneRenderMode.STATIC
        }

        log.info("Power ON - fading in all GPIO strips and preview")

        # Per-zone mode architecture:
        # - Static zones: fade in their saved colors
        # - Animated zones: restart their animations with fade in
        has_animated_zones = any(z.state.mode == ZoneRenderMode.ANIMATION for z in zones)

        # Fade in each GPIO strip (each strip renders only its own zones)
        fades = []
        for strip in self.frame_manager.zone_strips:
            frame = strip.build_frame_from_zones(color_map)
            fade = strip.transition_service.fade_in(frame, transition_config)
            fades.append(fade)

        # Fade in preview panel (if available)
        if self.preview_panel_controller:
            fade_preview = self.preview_panel_controller.fade_in_for_power_on(duration_ms=800, steps=20)
            fades.append(fade_preview)

        # Run all fades concurrently
        await asyncio.gather(*fades)

        # If there are animated zones, restart the global animation
        if has_animated_zones:
            current_anim = self.animation_service.get_current()
            if current_anim:
                anim_id = current_anim.config.id
                params = current_anim.build_params_for_engine()
                safe_params = Serializer.params_enum_to_str(params)
                log.info("Power ON - restarting animation for animated zones")
                await self.animation_engine.start(anim_id, **safe_params)

        log.info("Power ON complete")
