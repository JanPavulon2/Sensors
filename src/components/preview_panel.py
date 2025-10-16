"""
Preview Panel Component

CJMCU-2812-8 module - 8 RGB LEDs for previewing colors.
"""

from rpi_ws281x import PixelStrip, Color


class PreviewPanel:
    """
    Preview panel - 8 LED module for color preview

    Args:
        gpio: GPIO pin number
        count: Number of LEDs (default 8)
        color_order: Color order constant from ws module
        brightness: LED brightness 0-255

    Example:
        preview = PreviewPanel(gpio=19, color_order=ws.WS2811_STRIP_GRB)
        preview.set_color(255, 0, 0)  # Red
        preview.clear()
    """

    def __init__(self, gpio, count=8, color_order=None, brightness=32):
        from rpi_ws281x import ws

        if color_order is None:
            color_order = ws.WS2811_STRIP_GRB  # Default for CJMCU

        self.count = count
        self.strip = PixelStrip(
            count, gpio, 800000, 10, False, brightness, 1, color_order
        )
        self.strip.begin()

    def set_color(self, r, g, b):
        """
        Set all LEDs to same color

        Args:
            r, g, b: RGB values (0-255)
        """
        color = Color(r, g, b)
        for i in range(self.count):
            self.strip.setPixelColor(i, color)
        self.strip.show()

    def clear(self):
        """Turn off all LEDs"""
        for i in range(self.count):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
