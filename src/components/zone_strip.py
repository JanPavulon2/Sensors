"""
Zone Strip Component

LED strip divided into addressable zones (e.g., top, right, bottom, left).
Each zone can have independent colors.
"""

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from rpi_ws281x import PixelStrip, Color

if TYPE_CHECKING:
    from models.zone import Zone


class ZoneStrip:
    """
    LED strip with zone-based control

    Args:
        gpio: GPIO pin number
        pixel_count: Number of addressable pixels
        zones: List of Zone objects with start_index, end_index, tag, etc.
        color_order: Color order constant from ws module
        brightness: LED brightness 0-255

    Example:
        from models.zone import Zone
        zones = [
            Zone(name="Top", tag="top", pixel_count=4, enabled=True, order=1, start_index=0, end_index=3),
            Zone(name="Right", tag="right", pixel_count=3, enabled=True, order=2, start_index=4, end_index=6)
        ]
        strip = ZoneStrip(gpio=18, pixel_count=14, zones=zones, color_order=ws.WS2811_STRIP_RBG)

        strip.set_zone_color("top", 255, 0, 0)  # Red
        strip.set_zone_color("right", 0, 255, 0)  # Green
    """

    def __init__(
        self,
        gpio: int,
        pixel_count: int,
        zones: List['Zone'],
        color_order: Optional[int] = None,
        brightness: int = 32
    ) -> None:
        """Initialize LED strip with zone configuration.

        Args:
            gpio: GPIO pin (e.g., 18 for PWM)
            pixel_count: Total number of LED pixels
            zones: List of Zone objects
            color_order: WS281x color constant (e.g., ws.WS2811_STRIP_BRG)
            brightness: Global brightness 0-255
        """
        from rpi_ws281x import ws

        if color_order is None:
            color_order = ws.WS2811_STRIP_RGB  # Default

        self.pixel_count: int = pixel_count

        # Build internal zone mapping from Zone objects
        self.zones: Dict[str, List[int]] = {
            zone.tag: [zone.start_index, zone.end_index]
            for zone in zones if zone.enabled
        }
        self.zone_colors: Dict[str, Tuple[int, int, int]] = {zone.tag: (0, 0, 0) for zone in zones if zone.enabled}

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

    def set_zone_color(self, zone_name: str, r: int, g: int, b: int) -> None:
        """Set color for specific zone.

        Args:
            zone_name: Name of zone (must exist in self.zones)
            r, g, b: RGB values (0-255)
        """
        if zone_name not in self.zones:
            return

        # Save color
        self.zone_colors[zone_name] = (r, g, b)

        # Apply to LEDs
        start, end = self.zones[zone_name]
        color = Color(r, g, b)

        for i in range(start, end + 1):
            if i < self.pixel_count:
                self.strip.setPixelColor(i, color)

        self.strip.show()

    def get_zone_color(self, zone_name: str) -> Optional[Tuple[int, int, int]]:
        """Get current color of zone.

        Returns:
            (r, g, b) tuple or None if zone doesn't exist
        """
        return self.zone_colors.get(zone_name)

    def set_pixel_color(self, zone_name: str, pixel_index: int, r: int, g: int, b: int) -> None:
        """Set color for a specific pixel within a zone.

        Args:
            zone_name: Name of zone (must exist in self.zones)
            pixel_index: Index of pixel within the zone (0-based)
            r, g, b: RGB values (0-255)
        """
        if zone_name not in self.zones:
            return

        start, end = self.zones[zone_name]
        zone_length = end - start + 1

        # Validate pixel index
        if pixel_index < 0 or pixel_index >= zone_length:
            return

        # Calculate absolute pixel position on strip
        absolute_position = start + pixel_index

        if absolute_position < self.pixel_count:
            color = Color(r, g, b)
            self.strip.setPixelColor(absolute_position, color)
            self.strip.show()

    def apply_all_zones(self) -> None:
        """Apply all zone colors to strip."""
        for zone_name, (r, g, b) in self.zone_colors.items():
            start, end = self.zones[zone_name]
            color = Color(r, g, b)
            for i in range(start, end + 1):
                if i < self.pixel_count:
                    self.strip.setPixelColor(i, color)
        self.strip.show()

    def clear(self) -> None:
        """Turn off all LEDs."""
        for i in range(self.pixel_count):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
        self.zone_colors = {name: (0, 0, 0) for name in self.zones}



