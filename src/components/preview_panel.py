"""
Preview Panel Component - Hardware Abstraction Layer (Layer 1)

CJMCU-2812-8 module - 8 RGB LEDs for previewing colors and animations.
Hardware abstraction layer for WS2811 strip (GPIO 19, GRB color order).

GPIO registration is handled by HardwareManager for the entire AUX_5V strip.
PreviewPanel is a logical component within that physical strip.
"""

from typing import Tuple, List
from rpi_ws281x import PixelStrip, Color
from ..zone_layer.zone_strip import ZoneStrip

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
        gpio_manager: GPIOManager instance for pin registration
        count: Number of LEDs (default 8)
        color_order: Color order constant from ws module (default GRB)
        brightness: Global hardware brightness 0-255 (default 32)

    Example:
        >>> gpio_manager = GPIOManager()
        >>> preview = PreviewPanel(gpio=19, gpio_manager=gpio_manager)
        >>> preview.show_color((255, 0, 0))  # All LEDs red
        >>> preview.show_bar(75, 100, (0, 255, 0))  # 6 LEDs green (75% of 8)
        >>> preview.clear()
    """

    def __init__(
        self,
        zone_strip: ZoneStrip,
        count: int = 8,
        brightness: int = 32
    ):
        """
        Initialize PreviewPanel as logical view of PREVIEW zone in ZoneStrip.

        PREVIEW zone is part of the AUX_5V strip (GPIO 19).
        CJMCU-2812-8 physical device IS the PREVIEW zone (last 8 pixels).
        This component controls pixels within the shared ZoneStrip, not a separate one.

        Args:
            zone_strip: ZoneStrip instance for GPIO 19 (AUX_5V) containing both PIXEL and PREVIEW zones
            count: Number of LEDs in preview (default 8)
            brightness: Global brightness 0-255 (default 32)

        Note:
            PreviewPanel does NOT create its own PixelStrip.
            It renders to PREVIEW zone within the shared ZoneStrip on GPIO 19.
            Both PIXEL and PREVIEW zones share one PixelStrip instance (PWM channel 0).
        """
        self.count = count
        self.brightness = brightness
        self.zone_strip = zone_strip
        # self._pixel_strip = zone_strip.pixel_strip

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
            # self._pixel_strip.setPixelColor(physical_index, Color(r, g, b))

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
        if 0 <= pixel_index < self.count:
            color = Color(r, g, b)
            self._pixel_strip.setPixelColor(pixel_index, color)
            if show:
                self._pixel_strip.show()

    def show(self) -> None:
        """
        Push buffer to hardware (display changes made via set_pixel)

        Call this after setting individual pixels to make them visible.
        """
        self._pixel_strip.show()

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
            self._pixel_strip.setPixelColor(physical_index, Color(r, g, b))
        self._pixel_strip.show()

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
            self._pixel_strip.setPixelColor(i, Color(r, g, b))
        self._pixel_strip.show()

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
                self._pixel_strip.setPixelColor(physical_index, Color(*color))
            else:
                self._pixel_strip.setPixelColor(physical_index, Color(0, 0, 0))
        self._pixel_strip.show()

    def get_frame(self) -> List[Tuple[int, int, int]]:
        """
        Get current LED state as frame list

        Captures current RGB values for all LEDs in logical order (0-7).
        Automatically handles reversed panel mapping.

        Returns:
            List of RGB tuples [(r, g, b), ...] for each LED

        Example:
            >>> frame = preview.get_frame()
            >>> # frame = [(255, 0, 0), (0, 255, 0), ...]
        """
        frame = []
        for i in range(self.count):
            physical_index = self._reverse_index(i)
            color_int = self._pixel_strip.getPixelColor(physical_index)
            # Extract RGB from 32-bit color value (format: 0x00RRGGBB for RGB or varies by order)
            # For GRB order, getPixelColor returns packed GRB but we need RGB
            # rpi_ws281x uses internal 32-bit format, need to unpack correctly
            r = (color_int >> 16) & 0xFF
            g = (color_int >> 8) & 0xFF
            b = color_int & 0xFF
            frame.append((r, g, b))
        return frame

    def clear(self) -> None:
        """
        Turn off all LEDs immediately

        Sets all LEDs to black (0, 0, 0) and displays.
        """
        for i in range(self.count):
            self._pixel_strip.setPixelColor(i, Color(0, 0, 0))
        self._pixel_strip.show()

    # === High-Level Rendering Methods (Phase 2 Extensions) ===

    def render_solid(self, color: Tuple[int, int, int]) -> None:
        """
        Render solid color (all pixels same color).

        Shorthand for fill_with_color(), kept for API consistency with refactoring plan.

        Args:
            color: RGB tuple (r, g, b), each value 0-255

        Example:
            >>> preview.render_solid((255, 0, 0))  # All red
        """
        self.fill_with_color(color)

    def render_gradient(
        self, color: Tuple[int, int, int], intensity: float
    ) -> None:
        """
        Render color with intensity modulation (0.0-1.0).

        Scales RGB values by intensity factor. Useful for previewing brightness changes.

        Args:
            color: Base RGB color (r, g, b), each value 0-255
            intensity: Brightness multiplier, 0.0 (black) to 1.0 (full color)

        Example:
            >>> preview.render_gradient((255, 100, 0), 0.5)  # 50% brightness
            >>> preview.render_gradient((0, 255, 0), 0.75)   # 75% brightness
        """
        intensity = max(0.0, min(1.0, intensity))  # Clamp to 0.0-1.0
        r, g, b = color
        scaled_r = int(r * intensity)
        scaled_g = int(g * intensity)
        scaled_b = int(b * intensity)
        self.fill_with_color((scaled_r, scaled_g, scaled_b))

    def render_multi_color(self, colors: List[Tuple[int, int, int]]) -> None:
        """
        Render multiple colors (one per pixel, usually for zone preview).

        Each LED gets assigned a different color from the colors list.
        Useful for showing zone colors or multi-zone previews.

        Args:
            colors: List of RGB tuples, should be length 8 (truncated or padded as needed)

        Example:
            >>> zone_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
            >>> preview.render_multi_color(zone_colors)  # Partial fill, rest black
        """
        for i in range(self.count):
            if i < len(colors):
                r, g, b = colors[i]
                physical_index = self._reverse_index(i)
                self._pixel_strip.setPixelColor(physical_index, Color(r, g, b))
            else:
                physical_index = self._reverse_index(i)
                self._pixel_strip.setPixelColor(physical_index, Color(0, 0, 0))
        self._pixel_strip.show()

    def render_pattern(self, pattern: List[Tuple[int, int, int]]) -> None:
        """
        Render custom pattern (alias for show_frame for API clarity).

        Useful for custom animations or complex patterns.
        Pattern is truncated or padded to 8 pixels.

        Args:
            pattern: List of RGB tuples representing desired pattern

        Example:
            >>> chase = [(255, 0, 0), (0, 0, 0), (255, 0, 0), (0, 0, 0), ...]
            >>> preview.render_pattern(chase)
        """
        self.show_frame(pattern)
