from __future__ import annotations
from enum import Enum
from rpi_ws281x import ws


class LEDChipType(Enum):
    WS2811_12V = "WS2811_12V"
    WS2812_5V = "WS2812_5V"
    WS2813_5V = "WS2813_5V"
    WS2815_12V = "WS2815_12V"


class ColorOrder(Enum):
    RGB = "RGB"
    RBG = "RBG"
    GRB = "GRB"
    GBR = "GBR"
    BRG = "BRG"
    BGR = "BGR"
    
    
    @property
    def ws_type(self) -> int:
        """
        Map the enum to rpi_ws281x `ws.WS2811_STRIP_*` type constants.
        """
        return {
            ColorOrder.RGB: ws.WS2811_STRIP_RGB,
            ColorOrder.RBG: ws.WS2811_STRIP_RBG,
            ColorOrder.GRB: ws.WS2811_STRIP_GRB,
            ColorOrder.GBR: ws.WS2811_STRIP_GBR,
            ColorOrder.BRG: ws.WS2811_STRIP_BRG,
            ColorOrder.BGR: ws.WS2811_STRIP_BGR,
        }[self]
      