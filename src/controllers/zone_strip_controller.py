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

from typing import Dict, Tuple, TYPE_CHECKING
import asyncio
from components import ZoneStrip
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
    # Rendering
    # -----------------------------------------------------------------------

    def submit_all_zones_frame(self, zones_colors: Dict[ZoneID, Tuple[Color, int]]) -> None:
        """
        Submit zones colors to FrameManager.

        Each zone gets (Color, brightness) and is converted to RGB with brightness applied.
        """
        asyncio.create_task(self._submit_all_zones_frame(zones_colors))

    async def _submit_all_zones_frame(self, zone_colors: Dict[ZoneID, Tuple[Color, int]]) -> None:
        """Convert zones to RGB frame and submit to FrameManager."""
        rgb_colors = {}
        for zone_id, (color, brightness) in zone_colors.items():
            r, g, b = color.to_rgb()
            r, g, b = Color.apply_brightness(r, g, b, brightness)
            rgb_colors[zone_id] = (r, g, b)

        frame = ZoneFrame(
            zone_colors=rgb_colors,
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
            ttl=1.0
        )
        
        await self.frame_manager.submit_zone_frame(frame)

    def render_zone(self, zone_id: ZoneID, color: Color, brightness: int) -> None:
        """
        Render single zone with color and brightness

        Args:
            zone_id: ZoneID enum value representing the zone
            color: Color object (HUE, PRESET, RGB, or WHITE mode)
            brightness: Brightness percentage (0-100)

        Example:
            color = Color.from_hue(240)  # Blue
            controller.render_zone(ZoneID.LAMP, color, brightness=75)
        """
        r, g, b = color.to_rgb()

        # Apply brightness scaling
        r = int(r * brightness / 100)
        g = int(g * brightness / 100)
        b = int(b * brightness / 100)

        self.zone_strip.set_zone_color(zone_id, r, g, b)
        log.debug(f"Rendered zone {zone_id.name}: RGB({r},{g},{b}) @ {brightness}%")

    def render_zone_combined(self, zone: ZoneCombined) -> None:
        """
        Render a zone directly from ZoneCombined domain object.
        """
        self.render_zone(zone.config.id, zone.state.color, zone.brightness)

    def render_all_zones(self, zone_states: Dict[ZoneID, Tuple[Color, int]]) -> None:
        """
        Render all zones at once (batch update)

        More efficient than calling render_zone() multiple times
        because it only calls show() once at the end.

        Args:
            zone_states: Dict mapping ZoneID to (Color, brightness) tuples

        Example:
            states = {
                ZoneID.LAMP: (Color.from_hue(0), 100),
                ZoneID.TOP: (Color.from_hue(120), 80),
                ZoneID.STRIP: (Color.from_hue(240), 60)
            }
            controller.render_all_zones(states)
        """
        # Build dict with ZoneID enums and RGB colors
        colors_dict: Dict[ZoneID, Tuple[int, int, int]] = {}

        for zone_id, (color, brightness) in zone_states.items():
            r, g, b = color.to_rgb()

            colors_dict[zone_id] = (
            # Apply brightness scaling
                int(r * brightness / 100),
                int(g * brightness / 100),
                int(b * brightness / 100)
            )

        # Set all zones at once (efficient - single show() call)
        self.zone_strip.set_multiple_zones(colors_dict)
        log.debug(f"Rendered {len(zone_states)} zones (batch)")

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
        Restore all zones to saved state (power on)

        Same as render_all_zones() but semantically represents
        restoring from power-off state.

        Args:
            zone_states: Dict mapping ZoneID to (Color, brightness) tuples
        """
        # self.render_all_zones(zone_states)
        log.info("Power ON - restored all zones")

    def power_off(self) -> None:
        """
        Turn off all zones (power off)

        Same as clear_all() but semantically represents
        entering power-off state.
        """
        self.clear_all()
        log.info("Power OFF - cleared all zones")

    # -----------------------------------------------------------------------
    # Brightness-only updates
    # -----------------------------------------------------------------------

    def update_brightness(self, zone_id: ZoneID, color: Color, brightness: int) -> None:
        """
        Update zone brightness (keeps same color)

        Convenience method for brightness-only updates.

        Args:
            zone_id: Zone identifier enum
            color: Current zone color
            brightness: New brightness percentage (0-100)
        """
        self.render_zone(zone_id, color, brightness)

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
        await self.transition_service.fade_out(config)
        log.info(f"Faded out all zones ({config.duration_ms}ms)", LogCategory=LogCategory.TRANSITION)

    async def fade_in_all(self, target_frame, config) -> None:
        """
        Fade in all zones from black to target frame

        Args:
            target_frame: List of RGB tuples (one per pixel)
            config: TransitionConfig
        """
        await self.transition_service.fade_in(target_frame, config)
        log.info(f"Faded in all zones ({config.duration_ms}ms)", LogCategory=LogCategory.TRANSITION)

    async def startup_fade_in(self, zone_service, config) -> None:
        """
        Fade in from black to current zone states (app startup)

        Builds target frame from zone service WITHOUT rendering to strip,
        then performs smooth fade-in transition. No flash.

        Args:
            zone_service: ZoneService instance to read zone colors from
            config: TransitionConfig for fade timing
        """
        from utils.enum_helper import EnumHelper

        # Build target frame from zone states (no rendering yet)
        color_map = {
            z.config.id: z.get_rgb()
            for z in zone_service.get_all()
        }
        target_frame = self.zone_strip.build_frame_from_zones(color_map)

        # Fade in from black
        await self.transition_service.fade_in(target_frame, config)
        log.info(f"Startup fade-in complete ({config.duration_ms}ms)", LogCategory=LogCategory.TRANSITION)
