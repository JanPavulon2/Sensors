"""
WS281x LED Strip
Concrete implementation of IPhysicalStrip using rpi_ws281x.

This is the ONLY place in the app where we touch the WS281x driver.
Everything else uses IPhysicalStrip and is hardware-agnostic.
"""

from __future__ import annotations
from typing import List
from dataclasses import dataclass

from rpi_ws281x import PixelStrip, Color as WS281xColor

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
    color_order: str
    frequency_hz: int = 800_000
    dma_channel: int = 10
    brightness: int = 255
    
    
class WS281xStrip(IPhysicalStrip):
    """
    Concrete WS281x implementation.
    One instance controls exactly ONE physical LED strip on ONE GPIO/dma channel.
    """
    
    def __init__(self, config: WS281xConfig):
        self.config = config
                
        if config.color_order not in COLOR_ORDER_MAP:
            raise ValueError(f"Unsupported color order: {config.color_order}")

        self.order_map = COLOR_ORDER_MAP[config.color_order]

        self._pixel_strip = PixelStrip(
            config.led_count,
            config.gpio_pin,
            config.frequency_hz,
            config.dma_channel,
            invert=False,
            brightness=config.brightness,
            strip_type=None
        )
        
        self._pixel_strip.begin()
        self._buffer: List[Color] = [
            Color(_rgb=(0, 0, 0)) for _ in range(config.led_count)
        ]
        
        log.info(
            "WS281x strip initialized",
            gpio=config.gpio_pin,
            count=config.led_count,
            order=config.color_order,
            dma=config.dma_channel
        )
        
    # ------------------------------------------------------------
    # IPhysicalStrip interface
    # ------------------------------------------------------------

    @property
    def led_count(self) -> int:
        return self.config.led_count

    def begin(self) -> None:
        """Already initialized in __init__, left for API compatibility."""
        pass
    
    def set_pixel(self, index: int, color: Color) -> None:
        if index < 0 or index >= self.config.led_count:
            return

        self._buffer[index] = color
        
    def apply_frame(self, pixels: List[Color]) -> None:
        """
        Push entire RGB frame to LEDs.
        Called by FrameManager.
        """        
        length = min(len(pixels), self.config.led_count)
        r_i, g_i, b_i = self.order_map

        for i in range(length):
            col = pixels[i]
            ordered = [0, 0, 0]
            (r, g, b) = col.to_rgb()
            ordered[r_i] = r
            ordered[g_i] = g
            ordered[b_i] = b

            self._pixel_strip.setPixelColor(i, WS281xColor(*ordered))

        self._pixel_strip.show()
        
    def show(self) -> None:
        self._pixel_strip.show()

    def clear(self) -> None:
        """Turn off all LEDs instantly."""
        for i in range(self.config.led_count):
            self._pixel_strip.setPixelColor(i, WS281xColor(0, 0, 0))
        self._pixel_strip.show()

    def shutdown(self) -> None:
        """Graceful shutdown."""
        log.info(f"Shutting down WS281x strip on GPIO {self.config.gpio_pin}")
        self.clear()
        
    @staticmethod
    def _decode_color_order(order: str) -> int:
        # later implement properly
        from rpi_ws281x import ws
        return ws.WS2811_STRIP_GRB

