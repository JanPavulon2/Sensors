"""
StaticModeController - controls zone editing (colors, brightness, zone selection)

Renders zone states to FrameManager as ZoneFrames (one color per zone).
"""

from __future__ import annotations

import asyncio
import math
from typing import Dict, TYPE_CHECKING
from models.enums import ParamID, FramePriority, FrameSource, ZoneRenderMode
from models.domain import ZoneCombined
from models.frame import ZoneFrame
from services import ServiceContainer
from utils.logger import get_logger, LogCategory

if TYPE_CHECKING:
    from controllers.zone_strip_controller import ZoneStripController
    from services.zone_service import ZoneService

log = get_logger().for_category(LogCategory.GENERAL)

class StaticModeController:
    def __init__(self, services: ServiceContainer):
        """
        Initialize static mode controller with dependency injection.

        Args:
            services: ServiceContainer with all core services and managers
            strip_controllers: Dict mapping GPIO pin → ZoneStripController (unused - kept for compatibility)
            preview_panel: PreviewPanelController for display
        """
        self.zone_service = services.zone_service
        self.app_state_service = services.app_state_service
        self.frame_manager = services.frame_manager
        self.event_bus = services.event_bus
        self.color_manager = services.color_manager

        self.zone_ids = [z.config.id for z in self.zone_service.get_all()]
        self.current_param = self.app_state_service.get_state().current_param
        self.pulse_task = None
        self.pulse_active = False
        self.first_enter = True

    # --- Mode Entry/Exit ---

    def initialize(self):
        """
        Initialize static mode during app startup.

        Queries all STATIC zones and submits initial frame to FrameManager.
        Called once during LightingController initialization.
        """
        log.info("Initializing STATIC mode...")

        static_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.STATIC)
        if static_zones:
            log.debug(f"STATIC: Submitting {len(static_zones)} static zones")
            zone_colors = {
                z.config.id: z.state.color.with_brightness(z.brightness)
                for z in static_zones
            }
            frame = ZoneFrame(
                zone_colors=zone_colors,
                priority=FramePriority.MANUAL,
                source=FrameSource.STATIC,
                ttl=10.0  # Long TTL for initial state (persists until changed)
            )
            asyncio.create_task(self.frame_manager.submit_zone_frame(frame))
            log.info(f"STATIC initialized: {len(static_zones)} zones rendered")
        else:
            log.info("STATIC: No static zones to initialize")

        # Mark first_enter as complete so enter_mode behaves normally
        self.first_enter = False

    def enter_mode(self):
        """
        Switch to static mode: reapply zone states and start pulse if edit mode is on

        On first call (during app startup), skips rendering (initialize handles it).
        On subsequent calls (mode toggle), renders zones normally via FrameManager.
        """
        log.info("Entering STATIC mode")

        is_first_enter = self.first_enter
        log.debug(f"STATIC enter_mode: first_enter={is_first_enter}")

        # Skip rendering on first enter (initialize handles it)
        if is_first_enter:
            log.debug("STATIC: Skipping render (first enter - handled by initialize)")
            self.first_enter = False
        else:
            # Subsequent enters: render all STATIC zones
            log.debug(f"STATIC: Rendering {len(self.zone_service.get_all())} zones")
            static_zones = self.zone_service.get_by_render_mode(ZoneRenderMode.STATIC)
            if static_zones:
                zone_colors = {
                    z.config.id: z.state.color.with_brightness(z.brightness)
                    for z in static_zones
                }
                frame = ZoneFrame(
                    zone_colors=zone_colors,
                    priority=FramePriority.MANUAL,
                    source=FrameSource.STATIC,
                    ttl=1.5
                )
                asyncio.create_task(self.frame_manager.submit_zone_frame(frame))
            log.debug("STATIC: Rendering complete")

        # Start pulse if edit mode is enabled AND not first enter
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

    # --- Parameter Adjustment ---

    def adjust_param(self, delta: int):
        # Read current zone index fresh from state (not cached)
        # current_index = self.app_state_service.get_state().current_zone_index
        # zone_id = self.zone_ids[current_index]
        zone = self._get_current_zone()
        zone_id = zone.id
        
        if self.current_param == ParamID.ZONE_BRIGHTNESS:
            self.zone_service.adjust_parameter(zone_id, ParamID.ZONE_BRIGHTNESS, delta)
            
        elif self.current_param == ParamID.ZONE_COLOR_HUE:
            new_color = zone.state.color.adjust_hue(delta * 10)
            self.zone_service.set_color(zone_id, new_color)
            
        elif self.current_param == ParamID.ZONE_COLOR_PRESET:
            new_color = zone.state.color.next_preset(delta, self.color_manager)
            self.zone_service.set_color(zone_id, new_color)

        zone = self.zone_service.get_zone(zone_id)
        
        # Only render if NOT pulsing
        if not self.pulse_active:
            self._submit_zone_update(zone)
        log.info("Zone parameter changed", zone=zone.config.display_name, param=self.current_param.name)


    def _submit_zone_update(self, zone: ZoneCombined):
        """Submit single zone update to FrameManager"""
        zone_colors = {zone.config.id: zone.state.color.with_brightness(zone.brightness)}
        frame = ZoneFrame(
            zone_colors=zone_colors,
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
            ttl=1.5
        )
        asyncio.create_task(self.frame_manager.submit_zone_frame(frame))

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
        log.info(f"Cycled param to {self.current_param.name}")

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
            self.pulse_task = None

    async def _stop_pulse_async(self):
        """Stop pulse animation asynchronously (for shutdown cleanup)"""
        self.pulse_active = False
        if self.pulse_task and not self.pulse_task.done():
            self.pulse_task.cancel()
            try:
                await self.pulse_task
            except asyncio.CancelledError:
                pass
            self.pulse_task = None

    async def _pulse_task(self):
        """
        Pulse animation for the currently selected zone.

        Submits ZoneFrame with PULSE priority directly to FrameManager.
        Follows zone selection changes dynamically.
        """
        cycle = 1.0
        steps = 40
        while self.pulse_active:
            for step in range(steps):
                if not self.pulse_active:
                    break

                # Get current zone EACH step (allows pulse to follow zone cycling)
                current_zone = self._get_current_zone()
                base = current_zone.brightness

                # Calculate brightness factor (0.2 to 1.0)
                scale = 0.2 + 0.8 * (math.sin(step / steps * 2 * math.pi - math.pi/2) + 1) / 2
                pulse_brightness = int(base * scale)

                # Create ZoneFrame with pulsed brightness
                zone_colors = {current_zone.config.id: current_zone.state.color.with_brightness(pulse_brightness)}
                zone_frame = ZoneFrame(
                    priority=FramePriority.PULSE,
                    source=FrameSource.PULSE,
                    zone_colors=zone_colors,
                    ttl=1.5
                )

                await self.frame_manager.submit_zone_frame(zone_frame)

                await asyncio.sleep(cycle / steps)

    # --- Helper methods ---

    def _get_current_zone(self) -> ZoneCombined:
        """Get currently selected zone from app state"""
        current_index = self.app_state_service.get_state().current_zone_index
        current_zone_id = self.zone_ids[current_index]
        return self.zone_service.get_zone(current_zone_id)
