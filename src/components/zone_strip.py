"""
Zone Strip Component - Hardware abstraction for WS281x LED strips

Manages LED strip divided into addressable zones with independent colors.
Uses zone identifiers (uppercase enum names like "LAMP", "TOP") for addressing.
"""

from typing import Dict, List, Tuple, Optional
from rpi_ws281x import PixelStrip, Color
from models.domain.zone import ZoneConfig


class ZoneStrip:
    """
    Hardware abstraction for WS281x LED strip with zone-based control.

    This class provides a simple interface for controlling LED zones without
    coupling to domain models (uses plain strings for zone IDs).

    Args:
        gpio: GPIO pin number (18=PWM0, 19=PCM)
        pixel_count: Total number of addressable pixels on strip
        zones: List of ZoneConfig objects (provides zone ID, start/end indices)
        color_order: WS281x color constant (e.g., ws.WS2811_STRIP_BRG)
        brightness: Global hardware brightness 0-255

    Example:
        zones = [...]  # List of ZoneConfig from domain layer
        strip = ZoneStrip(
            gpio=18,
            pixel_count=45,
            zones=zones,
            color_order=ws.WS2811_STRIP_BRG,
            brightness=255
        )

        # Single zone
        strip.set_zone_color("LAMP", 255, 0, 0)  # Red

        # Multiple zones (efficient)
        strip.set_multiple_zones({
            "LAMP": (255, 0, 0),
            "TOP": (0, 255, 0),
            "RIGHT": (0, 0, 255)
        })
    """

    def __init__(
        self,
        gpio: int,
        pixel_count: int,
        zones: List[ZoneConfig],
        color_order: Optional[int] = None,
        brightness: int = 255
    ) -> None:
        """
        Initialize LED strip with zone configuration.

        Args:
            gpio: GPIO pin number (18=PWM0, 19=PCM)
            pixel_count: Total number of addressable pixels
            zones: List of ZoneConfig objects from domain layer
            color_order: WS281x color constant (None = RGB default)
            brightness: Global hardware brightness (0-255, default 255 for max)

        Note:
            Hardware brightness is typically set to 255 (max). Software brightness
            control is handled by scaling RGB values in the domain layer.
        """
        from rpi_ws281x import ws

        if color_order is None:
            color_order = ws.WS2811_STRIP_RGB  # Default

        self.pixel_count: int = pixel_count

        # Build internal zone mapping: zone_id -> [start_index, end_index]
        # Uses lowercase zone tags ("lamp", "top") to match ZoneConfig.tag property
        self.zones: Dict[str, List[int]] = {
            zone.tag: [zone.start_index, zone.end_index]
            for zone in zones
            if zone.enabled
        }

        # Cache current color for each zone
        self.zone_colors: Dict[str, Tuple[int, int, int]] = {
            zone.tag: (0, 0, 0)
            for zone in zones
            if zone.enabled
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

    def _validate_zone(self, zone_id: str) -> bool:
        """
        Validate if zone exists.

        Args:
            zone_id: Zone identifier string

        Returns:
            True if zone exists, False otherwise
        """
        return zone_id in self.zones

    def set_zone_color(self, zone_id: str, r: int, g: int, b: int) -> None:
        """
        Set color for a single zone.

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

    def get_zone_color(self, zone_id: str) -> Optional[Tuple[int, int, int]]:
        """
        Get current cached color of zone.

        Args:
            zone_id: Zone identifier string

        Returns:
            (r, g, b) tuple or None if zone doesn't exist
        """
        return self.zone_colors.get(zone_id)

    def set_pixel_color(self, zone_id: str, pixel_index: int, r: int, g: int, b: int) -> None:
        """
        Set color for a specific pixel within a zone.

        Args:
            zone_id: Zone identifier string
            pixel_index: Pixel index within zone (0-based)
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
        """
        if not self._validate_zone(zone_id):
            return

        start, end = self.zones[zone_id]
        zone_length = end - start + 1

        # Validate pixel index
        if pixel_index < 0 or pixel_index >= zone_length:
            return

        # Calculate absolute pixel position on strip
        absolute_position = start + pixel_index
        if absolute_position >= self.pixel_count:
            return

        color = Color(r, g, b)
        self.strip.setPixelColor(absolute_position, color)
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

    def apply_all_zones(self) -> None:
        """
        Reapply all cached zone colors to hardware.

        Useful after hardware reset or when resuming from sleep.
        """
        self.set_multiple_zones(self.zone_colors)

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



