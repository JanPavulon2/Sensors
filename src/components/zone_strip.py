"""
Zone Strip Component

LED strip divided into addressable zones (e.g., top, right, bottom, left).
Each zone can have independent colors.
"""

from rpi_ws281x import PixelStrip, Color


class ZoneStrip:
    """
    LED strip with zone-based control

    Args:
        gpio: GPIO pin number
        pixel_count: Number of addressable pixels
        zones: Dict of zone definitions, e.g.:
               {"top": [0, 3], "right": [4, 6], "bottom": [7, 10], "left": [11, 13]}
        color_order: Color order constant from ws module
        brightness: LED brightness 0-255

    Example:
        zones = {"top": [0, 3], "right": [4, 6]}
        strip = ZoneStrip(gpio=18, pixel_count=14, zones=zones, color_order=ws.WS2811_STRIP_RBG)

        strip.set_zone_color("top", 255, 0, 0)  # Red
        strip.set_zone_color("right", 0, 255, 0)  # Green
    """

    def __init__(self, gpio, pixel_count, zones, color_order=None, brightness=32):
        from rpi_ws281x import ws

        if color_order is None:
            color_order = ws.WS2811_STRIP_RGB  # Default

        self.pixel_count = pixel_count
        self.zones = zones
        self.zone_colors = {name: (0, 0, 0) for name in zones}

        self.strip = PixelStrip(
            pixel_count, gpio, 800000, 10, False, brightness, 0, color_order
        )
        self.strip.begin()

    def set_zone_color(self, zone_name, r, g, b):
        """
        Set color for specific zone

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

    def get_zone_color(self, zone_name):
        """
        Get current color of zone

        Returns:
            (r, g, b) tuple or None if zone doesn't exist
        """
        return self.zone_colors.get(zone_name)

    def apply_all_zones(self):
        """Apply all zone colors to strip"""
        for zone_name, (r, g, b) in self.zone_colors.items():
            start, end = self.zones[zone_name]
            color = Color(r, g, b)
            for i in range(start, end + 1):
                if i < self.pixel_count:
                    self.strip.setPixelColor(i, color)
        self.strip.show()

    def clear(self):
        """Turn off all LEDs"""
        for i in range(self.pixel_count):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
        self.zone_colors = {name: (0, 0, 0) for name in self.zones}
