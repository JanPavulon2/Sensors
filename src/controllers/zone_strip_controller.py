"""
Zone Strip Controller - Layer 2

Orchestrates rendering operations on the main LED strip.
Provides high-level interface for zone rendering using domain types (ZoneID, Color).
Now unified: submits ZoneFrames to FrameManager instead of directly updating hardware.

Responsibilities:
    - Render individual zones with color and brightness
    - Render all zones at once (batch update)
    - Power on/off all zones
    - Clear all LEDs
    - Translate domain types (ZoneID) to hardware types (string tags)
    - Submit zone state to FrameManager as ZoneFrames

Does NOT:
    - Decide WHICH zone to show (that's LEDController L3)
    - Manage state (that's Services)
    - Handle user input (that's ControlPanelController L2)
"""

from typing import Dict, Tuple, List, TYPE_CHECKING
import asyncio
from zone_layer.zone_strip import ZoneStrip
from models import Color
from models.domain import ZoneCombined
from models.enums import ZoneID, FramePriority, FrameSource
from models.frame import ZoneFrame
from utils.logger import get_logger, LogCategory
from utils.enum_helper import EnumHelper
from services.transition_service import TransitionService

if TYPE_CHECKING:
    from engine.frame_manager import FrameManager

log = get_logger().for_category(LogCategory.ZONE)


class ZoneStripController:
    """
    High-level controller for the main LED strip.

    Responsibilities:
      - Render zones based on domain data (ZoneCombined, Color)
      - Apply brightness scaling
      - Batch updates for efficiency
      - Provide clear/power control operations

    Args:
        zone_strip: ZoneStrip hardware component (L1)
    """

    def __init__(
        self,
        zone_strip: ZoneStrip,
        transition_service: TransitionService,
        frame_manager: 'FrameManager'
    ):
        """
        Initialize ZoneStripController

        Args:
            zone_strip: ZoneStrip hardware component (L1)
            transition_service: TransitionService instance for this strip
            frame_manager: FrameManager for unified rendering engine
        """
        self.zone_strip = zone_strip
        self.transition_service = transition_service
        self.frame_manager = frame_manager
        log.info("ZoneStripController initialized")

    # -----------------------------------------------------------------------
    # Rendering (PURE FRAME-BASED - All rendering through FrameManager)
    # -----------------------------------------------------------------------

    def submit_all_zones_frame(self, zones_colors: Dict[ZoneID, Tuple[Color, int]], priority: FramePriority = FramePriority.MANUAL) -> None:
        """
        Submit zones colors to FrameManager (UNIFIED RENDERING PATH - FIRE AND FORGET).

        Each zone gets (Color, brightness) and is converted to RGB with brightness applied.
        This is the ONLY rendering method - all LED updates go through FrameManager.

        Async task runs in background. Caller does not wait for completion.

        Args:
            zones_colors: Dict of ZoneID → (Color, brightness) tuples
            priority: Frame priority level (default MANUAL=10 for static, PULSE=20 for pulsing)

        Example:
            zone_colors = {ZoneID.FLOOR: (Color.red(), 75), ZoneID.LEFT: (Color.blue(), 100)}
            strip_controller.submit_all_zones_frame(zone_colors, priority=FramePriority.PULSE)
        """
        asyncio.create_task(self._submit_all_zones_frame(zones_colors, priority))

    async def _submit_all_zones_frame(self, zone_colors: Dict[ZoneID, Tuple[Color, int]], priority: FramePriority = FramePriority.MANUAL) -> None:
        """
        Async implementation: Apply brightness to Color objects and submit to FrameManager.

        Applies brightness scaling while preserving color mode (HUE/PRESET).
        Wraps in ZoneFrame and submits to FrameManager priority queue for 60 FPS render loop.

        Args:
            zone_colors: Zone ID → (Color, brightness) mapping
            priority: Frame priority level for queue selection
        """
        brightness_applied = {}
        for zone_id, (color, brightness) in zone_colors.items():
            # ✅ FIXED: Use with_brightness() to preserve color mode
            brightness_applied[zone_id] = color.with_brightness(brightness)

        frame = ZoneFrame(
            zone_colors=brightness_applied,
            priority=priority,
            source=FrameSource.STATIC,
            ttl=1.5
        )

        await self.frame_manager.submit_zone_frame(frame)

    def render_zone_combined(self, zone: ZoneCombined) -> None:
        """
        Render a single zone from ZoneCombined domain object (SYNC - FIRE AND FORGET).

        Submits zone color+brightness through FrameManager priority queue.
        Async task runs in background - caller doesn't wait.
        Used by LampWhiteModeController for immediate zone updates.

        Args:
            zone: ZoneCombined with id, color, and brightness

        Example:
            lamp = zone_service.get_zone(ZoneID.LAMP)
            strip_controller.render_zone_combined(lamp)  # No await needed
        """
        self.submit_all_zones_frame({zone.config.id: (zone.state.color, zone.brightness)})
        log.debug(f"Rendered zone {zone.config.id.name} (brightness={zone.brightness})")

    # -----------------------------------------------------------------------
    # Power & Clear
    # -----------------------------------------------------------------------

    def clear_all(self) -> None:
        """
        Turn off all LEDs (set all to black)
        """
        self.zone_strip.clear()
        log.debug("Cleared all zones")

    def power_on(self, zone_states: Dict[ZoneID, Tuple[Color, int]]) -> None:
        """
        Restore all zones to saved state (power on).

        Use submit_all_zones_frame() for normal operation.

        Args:
            zone_states: Dict mapping ZoneID to (Color, brightness) tuples
        """
        log.info("Power ON - use submit_all_zones_frame() to render zones")

    def power_off(self) -> None:
        """
        Turn off all zones (power off).

        Same as clear_all() but semantically represents entering power-off state.
        """
        self.clear_all()
        log.info("Power OFF - cleared all zones")

    # -----------------------------------------------------------------------
    # Transitions
    # -----------------------------------------------------------------------

    async def fade_out_all(self, config) -> None:
        """
        Fade out all zones to black

        Args:
            config: TransitionConfig (duration_ms, steps, ease_function)
        """
        current_frame = self.zone_strip.get_frame()
        
        #await self.transition_service.fade_out(current_frame, config)
        # await self.transition_service.fade_out(config)
        log.info(f"Faded out all zones ({config.duration_ms}ms)", LogCategory=LogCategory.TRANSITION)

    async def fade_in_all(self, target_frame, config) -> None:
        """
        Fade in all zones from black to target frame

        Args:
            target_frame: List of RGB tuples (one per pixel)
            config: TransitionConfig
        """
        # await self.transition_service.fade_in(target_frame, config)
        log.info(f"Faded in all zones ({config.duration_ms}ms)", LogCategory=LogCategory.TRANSITION)

    async def startup_fade_in(self, zones: List[ZoneCombined], config) -> None:
        """
        Fade in from black to current zone states (app startup)

        Builds target frame from zone list WITHOUT rendering to strip,
        then performs smooth fade-in transition. No flash.

        Args:
            zones: List of ZoneCombined objects with current color and brightness
            config: TransitionConfig for fade timing
        """
        # Build target frame from zone states with brightness applied
        color_map = {
            z.config.id: z.state.color.with_brightness(z.brightness)
            for z in zones
        }
        target_frame = self.zone_strip.build_frame_from_zones(color_map)

        # Fade in from black
        await self.transition_service.fade_in(target_frame, config)
        log.with_category(LogCategory.TRANSITION).info(f"Startup fade-in complete ({config.duration_ms}ms)")
