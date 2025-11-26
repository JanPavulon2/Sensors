"""
StaticModeController - controls zone editing (colors, brightness, zone selection)

Renders zone states to FrameManager as ZoneFrames (one color per zone).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from models.enums import ParamID, FramePriority, ZoneRenderMode
from models.domain import ZoneCombined
from services import ServiceContainer
from utils.logger import get_logger, LogCategory

if TYPE_CHECKING:
    from controllers.zone_strip_controller import ZoneStripController
    from controllers.preview_panel_controller import PreviewPanelController

log = get_logger().for_category(LogCategory.GENERAL)

class StaticModeController:
    def __init__(
        self,
        services: ServiceContainer,
        strip_controller: ZoneStripController,
        preview_panel: PreviewPanelController,
    ):
        """
        Initialize static mode controller with dependency injection.

        Args:
            services: ServiceContainer with all core services and managers
            strip_controller: ZoneStripController for rendering
            preview_panel: PreviewPanelController for display
        """
        self.zone_service = services.zone_service
        self.app_state_service = services.app_state_service
        self.frame_manager = services.frame_manager
        self.event_bus = services.event_bus
        self.color_manager = services.color_manager

        self.strip_controller = strip_controller
        self.preview_panel_controller = preview_panel

        self.zone_ids = [z.config.id for z in self.zone_service.get_all()]
        # NOTE: Don't cache current_zone_index - read fresh from state each time
        # This allows pulse and other effects to follow encoder selection
        self.current_param = self.app_state_service.get_state().current_param
        self.pulse_task = None
        self.pulse_active = False
        self.first_enter = True  # Skip rendering on first enter (startup fade handles it)

    # --- Mode Entry/Exit ---

    def enter_mode(self):
        """
        Switch to static mode: reapply zone states and start pulse if edit mode is on

        On first call (during app startup), skips rendering to allow startup_fade_in to handle it.
        On subsequent calls (mode toggle), renders zones normally via FrameManager.
        """
        log.info("Entering STATIC mode")

        # Check if this is first enter BEFORE changing the flag
        is_first_enter = self.first_enter
        log.debug(f"STATIC enter_mode: first_enter={is_first_enter}")

        # Skip rendering on first enter (startup transition handles it)
        if not is_first_enter:
            log.debug(f"STATIC: Rendering {len(self.zone_service.get_all())} zones")
            # Batch all zones and submit through unified FrameManager path
            zone_colors = {
                zone.config.id: (zone.state.color, zone.brightness)
                for zone in self.zone_service.get_all()
            }
            self.strip_controller.submit_all_zones_frame(zone_colors)
            log.debug("STATIC: Rendering complete")
        else:
            log.debug("STATIC: Skipping render (first enter)")
            self.first_enter = False

        self._sync_preview()

        # Start pulse if edit mode is enabled AND not first enter
        # (on startup, pulse will be started after transition completes)
        if not is_first_enter and self.app_state_service.get_state().edit_mode:
            self._start_pulse()

    def exit_mode(self):
        """
        Exit static mode: stop pulsing and cleanup

        Called when switching away from STATIC mode.
        """
        log.info("Exiting STATIC mode")
        self._stop_pulse()

    def on_edit_mode_change(self, enabled: bool):
        """Start or stop pulsing"""
        if enabled:
            self._start_pulse()
        else:
            self._stop_pulse()    
            
    
    def render_all_static_zones(self):
        """
        Render all zones in STATIC mode.
        Called by LEDController when cycling zones to prevent others from being blacked out.
        """
        static_zones = {
            z.config.id: (z.state.color, z.brightness)
            for z in self.zone_service.get_by_render_mode(ZoneRenderMode.STATIC)
        }

        if static_zones:
            self.strip_controller.submit_all_zones_frame(static_zones)
            log.debug(f"Rendered {len(static_zones)} STATIC zones")
        
    # --- Parameter Adjustment ---

    def adjust_param(self, delta: int):
        # Read current zone index fresh from state (not cached)
        current_index = self.app_state_service.get_state().current_zone_index
        zone_id = self.zone_ids[current_index]
        zone = self.zone_service.get_zone(zone_id)

        if self.current_param == ParamID.ZONE_BRIGHTNESS:
            self.zone_service.adjust_parameter(zone_id, ParamID.ZONE_BRIGHTNESS, delta)
            # Get fresh zone after brightness update
            zone = self.zone_service.get_zone(zone_id)
            # Only render if NOT pulsing (pulse task handles rendering)
            if not self.pulse_active:
                self.strip_controller.submit_all_zones_frame({zone_id: (zone.state.color, zone.brightness)})
            log.info("Adjusted brightness", zone=zone.config.display_name, brightness=zone.brightness)

        elif self.current_param == ParamID.ZONE_COLOR_HUE:
            new_color = zone.state.color.adjust_hue(delta * 10)
            self.zone_service.set_color(zone_id, new_color)
            # Only render if NOT pulsing
            if not self.pulse_active:
                self.strip_controller.submit_all_zones_frame({zone_id: (new_color, zone.brightness)})
            log.info("Adjusted hue", zone=zone.config.display_name, delta=delta)

        elif self.current_param == ParamID.ZONE_COLOR_PRESET:
            new_color = zone.state.color.next_preset(delta, self.color_manager)
            self.zone_service.set_color(zone_id, new_color)
            # Only render if NOT pulsing
            if not self.pulse_active:
                self.strip_controller.submit_all_zones_frame({zone_id: (new_color, zone.brightness)})
            log.info("Changed preset", zone=zone.config.display_name, preset=new_color._preset_name)

        self._sync_preview()
        
    def cycle_parameter(self):
        """Cycle through editable parameters"""
        params = [ParamID.ZONE_COLOR_HUE, ParamID.ZONE_COLOR_PRESET, ParamID.ZONE_BRIGHTNESS]

        # If current param is not in list (e.g., ANIM_SPEED from animation mode), start from first param
        if self.current_param not in params:
            self.current_param = params[0]
        else:
            current_index = params.index(self.current_param)
            self.current_param = params[(current_index + 1) % len(params)]

        self.app_state_service.set_current_param(self.current_param)
        self._sync_preview()
        log.info(f"Cycled param to {self.current_param.name}")
        
        
    # --- Preview + Pulse ---

    def _sync_preview(self):
        zone = self._get_current_zone()
        rgb = zone.state.color.to_rgb()
        brightness = zone.brightness

        # Show brightness as progress bar when editing brightness
        # if self.current_param == ParamID.ZONE_BRIGHTNESS:
        #     self.preview_panel_controller.show_bar(brightness, 100, rgb)
        # else:
        #     self.preview_panel_controller.show_color(rgb, brightness)

    def _start_pulse(self):
        # DEBUG: Skip pulse if testing static mode only
        try:
            from main_asyncio import DEBUG_NOPULSE
            if DEBUG_NOPULSE:
                return
        except ImportError:
            pass

        if not self.pulse_active:
            self.pulse_active = True
            self.pulse_task = asyncio.create_task(self._pulse_task())

    def _stop_pulse(self):
        """Stop pulse animation (synchronous version for normal mode changes)"""
        self.pulse_active = False
        if self.pulse_task:
            self.pulse_task.cancel()

        # Restore ALL static zones to prevent them from being turned off
        # (pulse only updated selected zone, other zones need explicit re-render)
        self.render_all_static_zones()

    async def _stop_pulse_async(self):
        """Stop pulse animation asynchronously (for shutdown cleanup)"""
        self.pulse_active = False
        if self.pulse_task and not self.pulse_task.done():
            self.pulse_task.cancel()
            try:
                await self.pulse_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling
            self.pulse_task = None

        # Restore ALL static zones to prevent them from being turned off
        # (pulse only updated selected zone, other zones need explicit re-render)
        self.render_all_static_zones()
    
    async def _pulse_task(self):
        import math
        cycle = 1.0
        steps = 40
        while self.pulse_active:
            for step in range(steps):
                if not self.pulse_active:
                    break

                # Get current zone EACH step (allows pulse to follow zone cycling)
                current_zone = self._get_current_zone()
                base = current_zone.brightness

                # Calculate brightness factor (0.5 to 1.0)
                scale = 0.2 + 0.8 * (math.sin(step / steps * 2 * math.pi - math.pi/2) + 1) / 2
                pulse_brightness = int(base * scale)
                self.strip_controller.submit_all_zones_frame(
                    {current_zone.config.id: (current_zone.state.color, pulse_brightness)},
                    priority=FramePriority.PULSE
                )

                await asyncio.sleep(cycle / steps)  
                
    # --- Helper methods ---

    def _get_current_zone(self) -> ZoneCombined:
        # Read current zone index fresh from state (not cached)
        # This allows pulse and other effects to follow encoder selection
        current_index = self.app_state_service.get_state().current_zone_index
        current_zone_id = self.zone_ids[current_index]
        return self.zone_service.get_zone(current_zone_id)
