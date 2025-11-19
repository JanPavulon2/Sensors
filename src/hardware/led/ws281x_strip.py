# hardware/led/ws281x_strip.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List

# rpi_ws281x binding
from rpi_ws281x import PixelStrip, Color as WS281xColor, ws

from hardware.led.strip_interface import IPhysicalStrip
from utils.logger import get_logger, LogCategory
from models.color import Color

log = get_logger().for_category(LogCategory.HARDWARE)


COLOR_ORDER_MAP = {
    "RGB": (0, 1, 2),
    "GRB": (1, 0, 2),
    "BRG": (2, 0, 1),
}


@dataclass(frozen=True)
class WS281xConfig:
    gpio_pin: int
    led_count: int
    color_order: str = "GRB"
    frequency_hz: int = 800_000
    dma_channel: int = 10
    brightness: int = 255
    invert: bool = False
    channel: int = 0  # PWM channel (0 or 1)


class WS281xStrip(IPhysicalStrip):
    """
    Concrete WS281x implementation using rpi_ws281x.

    - Controls one physical strip (one GPIO / one DMA channel / one PixelStrip instance).
    - All application code must use models.color.Color for pixel color data.
    - This class is the single place that talks to rpi_ws281x.
    """

    def __init__(self, config: WS281xConfig) -> None:
        self.config = config

        if config.color_order not in COLOR_ORDER_MAP:
            raise ValueError(f"Unsupported color order: {config.color_order}")

        self._order_map = COLOR_ORDER_MAP[config.color_order]

        # Resolve strip_type constant from color_order
        strip_type_const = self._decode_color_order(config.color_order)

        # PixelStrip constructor signature varies across versions.
        # Use explicit parameters and attempt to pass strip_type where supported.
        try:
            # Typical signature:
            # PixelStrip(num, pin, freq_hz, dma, invert, brightness, channel, strip_type)
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
            # Fallback for bindings with fewer args (older/newer)
            # Try without strip_type
            self._pixel_strip = PixelStrip(
                config.led_count,
                config.gpio_pin,
                config.frequency_hz,
                config.dma_channel,
                config.invert,
                config.brightness,
                config.channel,
            )

        # Begin the strip (initializes DMA / PWM)
        self._pixel_strip.begin()

        # Local buffer for higher-level Color objects
        self._buffer: List[Color] = [Color.from_rgb(0, 0, 0) for _ in range(config.led_count)]

        log.info(
            "WS281x strip initialized",
            gpio=config.gpio_pin,
            count=config.led_count,
            order=config.color_order,
            dma=config.dma_channel,
            channel=config.channel,
        )

    # ------------------------------------------------------------------
    # IPhysicalStrip-compatible API
    # ------------------------------------------------------------------
    @property
    def led_count(self) -> int:
        return self.config.led_count

    def begin(self) -> None:
        """PixelStrip was begun in ctor; this is kept for API compatibility."""
        # no-op, placed for explicitness
        return

    def set_pixel(self, index: int, color: Color) -> None:
        """
        Set a single logical pixel in the internal buffer.
        Does not push to hardware until apply_frame() or show() is called.
        """
        if 0 <= index < self.config.led_count:
            self._buffer[index] = color
        else:
            log.debug(f"set_pixel: index out of range {index}")

    def apply_frame(self, pixels: List[Color]) -> None:
        """
        Push an entire frame (list of Color) to the physical strip.

        - Will iterate up to led_count
        - Reorders color channels according to configured color_order
        - Uses setPixelColorRGB when available for clarity; otherwise uses WS281xColor wrapper
        """
        length = min(len(pixels), self.config.led_count)
        r_i, g_i, b_i = self._order_map

        # rpi_ws281x has two helper methods depending on binding version:
        use_rgb_helper = hasattr(self._pixel_strip, "setPixelColorRGB")

        for i in range(length):
            col = pixels[i]
            # Accept either our Color class or raw tuple
            if isinstance(col, Color):
                r, g, b = col.to_rgb()
            elif isinstance(col, tuple) or isinstance(col, list):
                r, g, b = int(col[0]), int(col[1]), int(col[2])
            else:
                # unknown type - skip
                log.warn(f"apply_frame: unexpected pixel type {type(col)} at idx {i}")
                continue

            # Reorder channels according to color_order
            ordered = [0, 0, 0]
            ordered[r_i] = int(max(0, min(255, r)))
            ordered[g_i] = int(max(0, min(255, g)))
            ordered[b_i] = int(max(0, min(255, b)))

            try:
                if use_rgb_helper:
                    # setPixelColorRGB expects r,g,b order (library handles underlying format)
                    self._pixel_strip.setPixelColorRGB(i, ordered[0], ordered[1], ordered[2])
                else:
                    # WS281xColor builds the packed color expected by setPixelColor
                    self._pixel_strip.setPixelColor(i, WS281xColor(ordered[0], ordered[1], ordered[2]))
            except Exception as ex:
                log.error("Failed to set pixel color", index=i, error=str(ex))

        # Push to hardware
        try:
            self._pixel_strip.show()
        except Exception as ex:
            log.error("Failed to show pixels", error=str(ex))

    def show(self) -> None:
        """Immediate hardware show (push contents of internal hardware buffer)."""
        try:
            self._pixel_strip.show()
        except Exception as ex:
            log.error("show() failed", error=str(ex))

    def clear(self) -> None:
        """Turn off all LEDs instantly and clear local buffer."""
        try:
            for i in range(self.config.led_count):
                # Use hardware clear
                if hasattr(self._pixel_strip, "setPixelColorRGB"):
                    self._pixel_strip.setPixelColorRGB(i, 0, 0, 0)
                else:
                    self._pixel_strip.setPixelColor(i, WS281xColor(0, 0, 0))
            self._pixel_strip.show()
        except Exception as ex:
            log.error("clear() failed", error=str(ex))
        finally:
            # Clear local buffer
            self._buffer = [Color.from_rgb(0, 0, 0) for _ in range(self.config.led_count)]

    def shutdown(self) -> None:
        """Graceful shutdown: turn off LEDs and log."""
        log.info(f"Shutting down WS281x strip on GPIO {self.config.gpio_pin}")
        try:
            self.clear()
        except Exception:
            # clear already logs errors
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _decode_color_order(order: str) -> int:
        """
        Convert color order string ('GRB'|'RGB'|'BRG') to rpi_ws281x ws constant.
        Default to WS2811_STRIP_GRB if unknown.
        """
        mapping = {
            "RGB": ws.WS2811_STRIP_RGB,
            "GRB": ws.WS2811_STRIP_GRB,
            "BRG": ws.WS2811_STRIP_BRG,
        }
        return mapping.get(order.upper(), ws.WS2811_STRIP_GRB)
