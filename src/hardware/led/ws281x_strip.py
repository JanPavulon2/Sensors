# hardware/led/ws281x_strip.py
"""
WS281xStrip - rpi_ws281x hardware driver
==========================================
Concrete implementation of IPhysicalStrip for WS281x chips.

Features:
- Color order remapping (RGB/GRB/BRG)
- Internal buffer (_buffer) as source of truth
- apply_frame() for atomic single-DMA push
- get_pixel() reads from _buffer (fast, no hardware query)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List

from rpi_ws281x import PixelStrip, Color as WS281xColor, ws

from hardware.led.strip_interface import IPhysicalStrip
from models.color import Color
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.HARDWARE)


# Color order channel mapping
COLOR_ORDER_MAP = {
    "RGB": (0, 1, 2),
    "RBG": (0, 2, 1),
    "GRB": (1, 0, 2),
    "GBR": (1, 2, 0),
    "BRG": (2, 0, 1),
    "BGR": (2, 1, 0),
}


@dataclass(frozen=True)
class WS281xConfig:
    """Configuration for WS281x LED strip."""
    gpio_pin: int
    led_count: int
    color_order: str = "GRB"  # WS2811/WS2812 typical
    frequency_hz: int = 800_000
    dma_channel: int = 10
    brightness: int = 255
    invert: bool = False
    channel: int = 0  # PWM channel (0 or 1)


class WS281xStrip(IPhysicalStrip):
    """
    WS281x hardware driver using rpi_ws281x library.

    - _buffer: List[Color] is canonical source of truth
    - All reads (get_pixel) use _buffer (no hardware query)
    - apply_frame() pushes entire buffer in single DMA transfer
    """

    def __init__(self, config: WS281xConfig) -> None:
        self.config = config

        # Validate color order
        if config.color_order.upper() not in COLOR_ORDER_MAP:
            raise ValueError(f"Unsupported color order: {config.color_order}")

        self._order_map = COLOR_ORDER_MAP[config.color_order.upper()]
        strip_type_const = self._decode_color_order(config.color_order)

        # Create PixelStrip (try full signature, fallback if binding differs)
        try:
            self._pixel_strip = PixelStrip(
                config.led_count,
                config.gpio_pin,
                config.frequency_hz,
                config.dma_channel,
                config.invert,
                config.brightness,
                config.channel,
                strip_type_const,
            )
        except TypeError:
            # Older rpi_ws281x version without strip_type param
            self._pixel_strip = PixelStrip(
                config.led_count,
                config.gpio_pin,
                config.frequency_hz,
                config.dma_channel,
                config.invert,
                config.brightness,
                config.channel,
            )

        # Initialize hardware
        self._pixel_strip.begin()

        # Local buffer (source of truth for get_pixel)
        self._buffer: List[Color] = [Color.black() for _ in range(config.led_count)]

        log.info(
            "WS281xStrip initialized",
            gpio=config.gpio_pin,
            count=config.led_count,
            order=config.color_order,
            dma=config.dma_channel,
            pwm=config.channel,
        )

    # ==================== IPhysicalStrip API ====================

    @property
    def led_count(self) -> int:
        return self.config.led_count

    def set_pixel(self, index: int, color: Color) -> None:
        """
        Set pixel in buffer (does not push to hardware).
        Call show() or apply_frame() to render.
        """
        if 0 <= index < self.config.led_count:
            self._buffer[index] = color
        else:
            log.debug("set_pixel: index out of range", index=index)

    def get_pixel(self, index: int) -> Color:
        """Read pixel from buffer (fast, no hardware query)."""
        if 0 <= index < self.config.led_count:
            return self._buffer[index]
        return Color.black()

    def apply_frame(self, pixels: List[Color]) -> None:
        """
        Atomic push of full frame to hardware (single DMA transfer).

        - Updates _buffer and hardware buffer in single loop
        - Handles color order remapping
        - Clears remaining pixels if frame shorter than led_count
        - Calls show() once at end (fast path)
        """
        length = min(len(pixels), self.config.led_count)
        r_i, g_i, b_i = self._order_map
        use_rgb_helper = hasattr(self._pixel_strip, "setPixelColorRGB")

        # Update buffer + hardware in single loop
        for i in range(length):
            col = pixels[i]

            # Tolerant: accept Color, tuple, or list
            if isinstance(col, Color):
                self._buffer[i] = col
                r, g, b = col.to_rgb()
            elif isinstance(col, (tuple, list)) and len(col) >= 3:
                r, g, b = int(col[0]), int(col[1]), int(col[2])
                self._buffer[i] = Color.from_rgb(r, g, b)
            else:
                log.warn("apply_frame: invalid pixel type", index=i, type=type(col))
                continue

            # Reorder channels according to color_order
            ordered = [0, 0, 0]
            ordered[r_i] = max(0, min(255, int(r)))
            ordered[g_i] = max(0, min(255, int(g)))
            ordered[b_i] = max(0, min(255, int(b)))

            # Push to hardware buffer
            try:
                if use_rgb_helper:
                    self._pixel_strip.setPixelColorRGB(i, ordered[0], ordered[1], ordered[2])
                else:
                    self._pixel_strip.setPixelColor(i, WS281xColor(ordered[0], ordered[1], ordered[2]))
            except Exception as ex:
                log.error("apply_frame: setPixel failed", index=i, error=str(ex))

        # Clear remaining pixels if frame shorter than strip
        if length < self.config.led_count:
            black = Color.black()
            for i in range(length, self.config.led_count):
                self._buffer[i] = black
                try:
                    if use_rgb_helper:
                        self._pixel_strip.setPixelColorRGB(i, 0, 0, 0)
                    else:
                        self._pixel_strip.setPixelColor(i, WS281xColor(0, 0, 0))
                except Exception:
                    pass

        # Single DMA push
        try:
            self._pixel_strip.show()
        except Exception as ex:
            log.error("apply_frame: show() failed", error=str(ex))

    def show(self) -> None:
        """Push buffer to hardware (assumes set_pixel already called)."""
        try:
            self._pixel_strip.show()
        except Exception as ex:
            log.error("show failed", error=str(ex))

    def clear(self) -> None:
        """Turn off all LEDs (black + show)."""
        black = Color.black()
        use_rgb_helper = hasattr(self._pixel_strip, "setPixelColorRGB")

        try:
            for i in range(self.config.led_count):
                self._buffer[i] = black
                if use_rgb_helper:
                    self._pixel_strip.setPixelColorRGB(i, 0, 0, 0)
                else:
                    self._pixel_strip.setPixelColor(i, WS281xColor(0, 0, 0))
            self._pixel_strip.show()
        except Exception as ex:
            log.error("clear failed", error=str(ex))

    def shutdown(self) -> None:
        """Graceful shutdown (clear + log)."""
        log.info(f"Shutting down WS281xStrip GPIO {self.config.gpio_pin}")
        try:
            self.clear()
        except Exception:
            pass

    # ==================== Helpers ====================

    @staticmethod
    def _decode_color_order(order: str) -> int:
        """Map color order string to rpi_ws281x constant."""
        mapping = {
            "RGB": ws.WS2811_STRIP_RGB,
            "RBG": ws.WS2811_STRIP_RBG,
            "GRB": ws.WS2811_STRIP_GRB,
            "GBR": ws.WS2811_STRIP_GBR,
            "BRG": ws.WS2811_STRIP_BRG,
            "BGR": ws.WS2811_STRIP_BGR,
        }
        return mapping.get(order.upper(), ws.WS2811_STRIP_GRB)
