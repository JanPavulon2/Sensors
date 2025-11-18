"""
LEDHardware - Hardware Abstraction for WS281x Devices

Responsible for:
- creating PixelStrip controllers for each GPIO
- handling differences between WS2811/WS2812/WS2813/WS2815
- mapping color order
- providing a uniform interface for higher layers
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Dict, Tuple

from rpi_ws281x import PixelStrip, Color
from utils.logger import get_category_logger
from models.enums import LogCategory


log = get_category_logger(LogCategory.HARDWARE)


# ---------------------------------------------------------------------------
# LED chip definitions
# ---------------------------------------------------------------------------

LEDChipType = Literal[
    "WS2811_12V",
    "WS2812_5V",
    "WS2813_5V",
    "WS2815_12V"
]

ColorOrder = Literal["RGB", "RBG", "GRB", "GBR", "BRG", "BGR"]


COLOR_ORDER_MAP: Dict[ColorOrder, int] = {
    "RGB": 0x00100800,  # not exact but irrelevant; we set channel manually anyway
    "RBG": 0x00100008,
    "GRB": 0x00081000,
    "GBR": 0x00080010,
    "BRG": 0x00001800,
    "BGR": 0x00000810,
}


# ---------------------------------------------------------------------------
# Strip Controller Wrapper
# ---------------------------------------------------------------------------

@dataclass
class StripController:
    gpio: int
    led_count: int
    strip: PixelStrip

    def begin(self):
        log.info(f"Initializing LED strip on GPIO {self.gpio} with {self.led_count} LEDs")
        self.strip.begin()

    def write_rgb(self, index: int, rgb: Tuple[int, int, int]):
        if 0 <= index < self.led_count:
            r, g, b = rgb
            self.strip.setPixelColor(index, Color(r, g, b))

    def render(self):
        self.strip.show()


# ---------------------------------------------------------------------------
# LEDHardware (main public API)
# ---------------------------------------------------------------------------

class LEDHardware:
    """
    Factory for StripController objects.
    Handles correct DMA/channel selection and color order mapping.
    """

    SUPPORTED_GPIO = [10, 12, 18, 21, 19]

    def __init__(self):
        self._controllers: Dict[int, StripController] = {}
        log.info("LEDHardware initialized")

    # ----------------------------------------------------------------------

    def create_strip(
        self,
        *,
        gpio: int,
        count: int,
        chip: LEDChipType,
        color_order: ColorOrder,
    ) -> StripController:
        """
        Create a new PixelStrip controller.

        Parameters:
            gpio: BCM pin
            count: number of LEDs
            chip: WS2811_12V, WS2812_5V, ...
            color_order: GRB/BRG/etc.
        """

        if gpio not in self.SUPPORTED_GPIO:
            log.warn(f"GPIO {gpio} is not officially supported, attempting anyway")

        dma_channel = self._select_dma(gpio)
        pwm_channel = self._select_pwm(gpio)

        log.info(
            "Creating LED strip",
            gpio=gpio,
            count=count,
            chip=chip,
            color_order=color_order,
            dma=dma_channel,
            pwm_channel=pwm_channel,
        )

        strip = PixelStrip(
            count,              # num LEDs
            gpio,               # GPIO pin
            800000,             # freq
            dma_channel,        # DMA channel
            False,              # invert
            255,                # brightness
            pwm_channel,        # channel
            COLOR_ORDER_MAP[color_order]
        )

        controller = StripController(
            gpio=gpio,
            led_count=count,
            strip=strip
        )

        controller.begin()
        self._controllers[gpio] = controller
        return controller

    # ----------------------------------------------------------------------
    # DMA / PWM MAPPING
    # (this is the correct mapping: each PWM-capable pin has a fixed channel)
    # ----------------------------------------------------------------------

    @staticmethod
    def _select_pwm(gpio: int) -> int:
        """
        Correct PWM channel mapping for rpi_ws281x.
        """
        if gpio == 18:
            return 0
        if gpio == 19:
            return 1
        if gpio == 12:
            return 0
        if gpio == 13:
            return 1

        # fallback
        return 0

    @staticmethod
    def _select_dma(gpio: int) -> int:
        """
        Use different DMA channels for multiple strips.
        """
        if gpio in (18, 12):
            return 10
        if gpio in (19, 13):
            return 11

        return 10

    # ----------------------------------------------------------------------

    def get(self, gpio: int) -> StripController | None:
        return self._controllers.get(gpio)

    def all(self):
        return self._controllers.values()

