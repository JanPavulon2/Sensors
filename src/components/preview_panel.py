"""
Preview Panel Component

CJMCU-2812-8 module - 8 RGB LEDs for previewing colors and animations.
Hardware abstraction layer for WS2811 strip (GPIO 19, GRB color order).
"""

from typing import Tuple, List
from rpi_ws281x import PixelStrip, Color


class PreviewPanel:
    """
    Preview panel hardware abstraction - 8 LED module

    Provides low-level hardware control for CJMCU-2812-8 preview panel.
    All methods that modify LEDs call strip.show() to display immediately.

    Hardware:
        - 8 RGB LEDs (WS2811/WS2812 compatible)
        - GPIO 19
        - GRB color order
        - Independent from main strip

    Args:
        gpio: GPIO pin number
        count: Number of LEDs (default 8)
        color_order: Color order constant from ws module (default GRB)
        brightness: Global hardware brightness 0-255 (default 32)

    Example:
        >>> preview = PreviewPanel(gpio=19)
        >>> preview.show_color((255, 0, 0))  # All LEDs red
        >>> preview.show_bar(75, 100, (0, 255, 0))  # 6 LEDs green (75% of 8)
        >>> preview.clear()
    """

    def __init__(self, gpio: int, count: int = 8, color_order=None, brightness: int = 32):
        from rpi_ws281x import ws

        if color_order is None:
            color_order = ws.WS2811_STRIP_GRB  # CJMCU-2812-8 uses GRB

        self.count = count
        self.brightness = brightness

        # Private WS2811 strip - use public methods instead of direct access
        self._strip = PixelStrip(
            count, gpio, 800000, 10, False, brightness, 1, color_order
        )
        self._strip.begin()

    def _reverse_index(self, index: int) -> int:
        """
        Reverse LED index for upside-down panel

        Physical panel is mounted upside down, so LED 0 should map to position 7, etc.

        Args:
            index: Logical index (0-7)

        Returns:
            Physical index (7-0)
        """
        return self.count - 1 - index

    def set_pixel(self, index: int, r: int, g: int, b: int) -> None:
        """
        Set individual LED color in buffer (not displayed until show() called)

        Use this for manual pixel-level control. For batch updates, prefer show_frame().

        Args:
            index: Logical LED index (0-7), automatically reversed for upside-down panel
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
        """
        if 0 <= index < self.count:
            physical_index = self._reverse_index(index)
            self._strip.setPixelColor(physical_index, Color(r, g, b))

    def show(self) -> None:
        """
        Push buffer to hardware (display changes made via set_pixel)

        Call this after setting individual pixels to make them visible.
        """
        self._strip.show()

    def show_frame(self, frame: List[Tuple[int, int, int]]) -> None:
        """
        Display complete frame (all LEDs at once)

        Efficient method for animations - sets all LEDs then displays once.
        Frame is truncated or padded to match LED count (8).
        LEDs are automatically reversed for upside-down panel.

        Args:
            frame: List of RGB tuples [(r, g, b), ...], length should be 8

        Example:
            >>> frame = [(255, 0, 0), (0, 255, 0), (0, 0, 255), ...] # 8 colors
            >>> preview.show_frame(frame)
        """
        for i, (r, g, b) in enumerate(frame[:self.count]):
            physical_index = self._reverse_index(i)
            self._strip.setPixelColor(physical_index, Color(r, g, b))
        self._strip.show()

    def fill_with_color(self, rgb: Tuple[int, int, int]) -> None:
        """
        Fill all LEDs with single color and display immediately

        Args:
            rgb: RGB tuple (r, g, b) where each value is 0-255

        Example:
            >>> preview.fill_with_color((255, 100, 0))  # Orange on all LEDs
        """
        r, g, b = rgb
        for i in range(self.count):
            self._strip.setPixelColor(i, Color(r, g, b))
        self._strip.show()

    def show_bar(self, value: int, max_value: int = 100,
                 color: Tuple[int, int, int] = (255, 255, 255)) -> None:
        """
        Display bar indicator proportional to value (0 to 8 LEDs lit)

        Maps value/max_value ratio to LED count (0-8).
        Bar fills from bottom to top (reversed panel means top LEDs light first).
        Useful for showing percentages, levels, or progress.

        Args:
            value: Current value
            max_value: Maximum value for normalization (default 100)
            color: RGB color for lit LEDs (default white)

        Example:
            >>> preview.show_bar(50, 100, (0, 255, 0))  # 4 LEDs green (50%)
            >>> preview.show_bar(75, 100)  # 6 LEDs white (75%)
        """
        filled = int((value / max_value) * self.count)
        filled = max(0, min(self.count, filled))  # Clamp to 0-8

        for i in range(self.count):
            physical_index = self._reverse_index(i)
            if i < filled:
                self._strip.setPixelColor(physical_index, Color(*color))
            else:
                self._strip.setPixelColor(physical_index, Color(0, 0, 0))
        self._strip.show()

    def clear(self) -> None:
        """
        Turn off all LEDs immediately

        Sets all LEDs to black (0, 0, 0) and displays.
        """
        for i in range(self.count):
            self._strip.setPixelColor(i, Color(0, 0, 0))
        self._strip.show()
