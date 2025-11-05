"""
Zone Strip Component - Hardware abstraction for WS281x LED strips

Manages LED strip divided into addressable zones with independent colors.
Each zone is addressed by string identifiers (e.g. "LAMP", "TOP").

Handles only low-level pixel operations and caching.
"""

from typing import Dict, List, Tuple, Optional
from rpi_ws281x import PixelStrip, Color
from models.domain.zone import ZoneConfig
from services.transition_service import TransitionService
from infrastructure import GPIOManager
from utils.enum_helper import EnumHelper


class ZoneStrip:
    """
    Hardware abstraction for WS281x LED strip with zone-based control.

    Provides direct hardware operations:
      - Set color for zones or individual pixels
      - Apply batches efficiently
      - Clear or restore LED state

    Accepts string zone identifiers (e.g. "LAMP"), not enums.

    Does NOT handle:
      - Brightness scaling
      - Color model conversions
      - Any domain logic

    Args:
        gpio: GPIO pin number (18=PWM0, 19=PCM)
        pixel_count: Total number of addressable pixels
        zones: List of ZoneConfig objects
        gpio_manager: GPIOManager for pin registration
        color_order: WS281x color constant (default RGB)
        brightness: Global hardware brightness (0–255)
    """

    def __init__(
        self,
        gpio: int,
        pixel_count: int,
        zones: List[ZoneConfig],
        gpio_manager: GPIOManager,
        color_order: Optional[int] = None,
        brightness: int = 255
    ) -> None:
        from rpi_ws281x import ws

        if color_order is None:
            color_order = ws.WS2811_STRIP_BRG  # Default for WS2811

        self.pixel_count: int = pixel_count

        # Register WS281x pin via GPIOManager
        gpio_manager.register_ws281x(
            pin=gpio,
            component=f"ZoneStrip(GPIO{gpio},{pixel_count}px)"
        )

        # Build internal mapping: "LAMP" → [start_index, end_index]
        self.zones: Dict[str, List[int]] = {
            EnumHelper.to_string(zone.id): [zone.start_index, zone.end_index]
            for zone in zones
        }

        # Reversed zones (for inverted physical layout)
        self.zone_reversed: Dict[str, bool] = {
            EnumHelper.to_string(zone.id): zone.reversed
            for zone in zones
        }

        # Cached colors (initialized to black)
        self.zone_colors: Dict[str, Tuple[int, int, int]] = {
            EnumHelper.to_string(zone.id): (0, 0, 0)
            for zone in zones
        }

        # PixelStrip constructor parameters:
        # - num: number of pixels
        # - pin: GPIO pin number (18 = PWM0)
        # - freq_hz: signal frequency in Hz (800000 = 800kHz for WS2811)
        # - dma: DMA channel (10 is safe default, 0-14 available)
        # - invert: False = normal signal, True = inverted (for level shifters)
        # - brightness: global brightness 0-255
        # - channel: PWM channel (0 or 1)
        # - strip_type: color order constant (ws.WS2811_STRIP_BRG for your hardware)
        self.strip: PixelStrip = PixelStrip(
            pixel_count,    # num: total LED count
            gpio,           # pin: GPIO number
            800000,         # freq_hz: 800kHz signal frequency
            10,             # dma: DMA channel 10
            False,          # invert: normal signal (not inverted)
            brightness,     # brightness: 0-255 global brightness
            0,              # channel: PWM channel 0
            color_order     # strip_type: ws.WS2811_STRIP_BRG
        )
        
        self.strip.begin()

        # Initialize transition service for smooth state changes
        # self.transition_service = TransitionService(self)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _resolve_zone(self, zone):
        """Accept either ZoneID enum or string tag."""
        from models.enums import ZoneID
        if isinstance(zone, ZoneID):
            return zone.name  # use tag-like string internally
        return zone

    def _validate_zone(self, zone_id: str) -> bool:
        """
        Validate if zone exists.

        Args:
            zone_id: Zone identifier string

        Returns:
            True if zone exists, False otherwise
        """
        return zone_id in self.zones

    def _get_physical_pixel_index(self, zone_id: str, logical_index: int) -> int:
        """
        Convert logical pixel index to physical pixel index, accounting for reversed zones.

        Args:
            zone_id: Zone identifier string
            logical_index: Logical pixel index within zone (0 = first pixel)

        Returns:
            Physical pixel index on the strip
        """
        start, end = self.zones[zone_id]

        if self.zone_reversed.get(zone_id, False):
            # Reversed: logical 0 maps to physical end, logical max maps to physical start
            return end - logical_index
        
        # Normal: logical 0 maps to physical start
        return start + logical_index

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def set_zone_color(self, zone_id: str, r: int, g: int, b: int) -> None:
        """
        Set uniform color for an entire zone.

        Args:
            zone_id: Zone identifier string (e.g., "LAMP", "TOP")
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)

        Note:
            Calls strip.show() immediately. For setting multiple zones,
            use set_multiple_zones() for better performance.
        """
        if not self._validate_zone(zone_id):
            return

        # Cache color
        self.zone_colors[zone_id] = (r, g, b)

        # Apply to all pixels in zone
        start, end = self.zones[zone_id]
        color = Color(r, g, b)
        
        for i in range(start, end + 1):
            if i < self.pixel_count:
                self.strip.setPixelColor(i, color)

        # Update hardware
        self.strip.show()

    def set_multiple_zones(self, zone_colors: Dict[str, Tuple[int, int, int]]) -> None:
        """
        Set colors for multiple zones at once (efficient - single strip.show()).

        Recommended for batch updates to avoid flickering from multiple show() calls.

        Args:
            zone_colors: Dict mapping zone_id to (r, g, b) tuple
        
        Example: {"LAMP": (255, 0, 0), "TOP": (0, 255, 0)}

        Note:
            Invalid zone IDs are silently skipped.
        """
        for zone_id, (r, g, b) in zone_colors.items():
            if not self._validate_zone(zone_id):
                continue

            # Cache color
            self.zone_colors[zone_id] = (r, g, b)

            # Apply to all pixels in zone
            start, end = self.zones[zone_id]
            color = Color(r, g, b)
            for i in range(start, end + 1):
                if i < self.pixel_count:
                    self.strip.setPixelColor(i, color)

        # Single hardware update for all zones
        self.strip.show()

    def set_pixel_color(self, zone_id: str, pixel_index: int, r: int, g: int, b: int, show: bool = True) -> None:
        """
        Set color of a specific pixel inside a zone.

        Args:
            zone_id: Zone identifier string
            pixel_index: Logical pixel index within zone (0-based, 0 = first pixel regardless of reversal)
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
            show: If True, immediately update strip (default). If False, wait for manual show() call.

        Note:
            Respects the zone's reversed flag. If reversed=True, logical index 0
            maps to the last physical pixel in the zone.
            Set show=False when updating many pixels, then call show() once after all updates.
        """
        if not self._validate_zone(zone_id):
            return

        start, end = self.zones[zone_id]
        zone_length = end - start + 1

        # Validate pixel index
        if pixel_index < 0 or pixel_index >= zone_length:
            return

        # Calculate physical pixel position, accounting for reversal
        physical_position = self._get_physical_pixel_index(zone_id, pixel_index)
        if physical_position >= self.pixel_count:
            return

        self.strip.setPixelColor(physical_position, Color(r, g, b))

        if show:
            self.strip.show()

    def set_pixel_color_absolute(self, pixel_index: int, r: int, g: int, b: int, show: bool = False) -> None:
        """
        Set color for a pixel by absolute strip index (used by TransitionService).

        Args:
            pixel_index: Absolute pixel index (0 to pixel_count-1)
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
            show: If True, immediately update strip

        Note:
            This is a low-level method for TransitionService.
            For zone-based control, use set_zone_color() or set_pixel_color().
        """
        if 0 <= pixel_index < self.pixel_count:
            color = Color(r, g, b)
            self.strip.setPixelColor(pixel_index, color)
            if show:
                self.strip.show()

    def show(self) -> None:
        """
        Update strip hardware - call after batch of set_pixel_color(show=False) calls
        """
        self.strip.show()

    def clear(self) -> None:
        """
        Turn off all LEDs and reset zone color cache.

        Sets all pixels to black (0, 0, 0) and updates hardware immediately.
        """
        for i in range(self.pixel_count):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()

        # Reset color cache
        self.zone_colors = {zone_id: (0, 0, 0) for zone_id in self.zones}

    # -----------------------------------------------------------------------
    # TransitionService Support Methods
    # -----------------------------------------------------------------------

    def get_frame(self) -> List[Tuple[int, int, int]]:
        """
        Capture current LED state as list of RGB tuples.

        Used by TransitionService for smooth transitions.

        Returns:
            List of (r, g, b) tuples for each pixel (index 0 to pixel_count-1)
        """
        frame = []
        for i in range(self.pixel_count):
            color: int = int(self.strip.getPixelColor(i)) # type: ignore
            # Extract RGB from 32-bit color value (format: 0xRRGGBB for RGB order)
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            frame.append((r, g, b))
            
        return frame

    def get_zone_color(self, zone_id: str) -> Optional[Tuple[int, int, int]]:
        """
        Get current cached color of zone.

        Args:
            zone_id: Zone identifier string

        Returns:
            (r, g, b) tuple or None if zone doesn't exist
        """
        return self.zone_colors.get(zone_id)

    def build_frame_from_zones(self, zone_colors: Dict[str, Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
        """Build pixel-level frame from given zone colors (for transitions)."""
        frame = [(0, 0, 0)] * self.pixel_count
        for zone_id, (r, g, b) in zone_colors.items():
            if zone_id not in self.zones:
                continue
            start, end = self.zones[zone_id]
            for i in range(start, end + 1):
                if i < self.pixel_count:
                    frame[i] = (r, g, b)
        return frame
