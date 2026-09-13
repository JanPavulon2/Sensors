"""
Colour channel ordering, shared by every addressable strip driver.
==================================================================
WS281x chips do not all latch their channels in the same order, so a frame's
red, green and blue have to be placed on the wire in the order the chip on the
strip expects. Extracted from ws281x_strip.py so that drivers which do not go
through rpi_ws281x - notably the SPI path used on the Raspberry Pi 5 - can
share one definition instead of restating it.
"""

from __future__ import annotations

from enum import StrEnum

# Maps a colour order name to the wire position of red, green and blue in that
# order. Consumers use it as: ordered[red_position] = red, and so on.
COLOR_ORDER_MAP = {
    "RGB": (0, 1, 2),
    "RBG": (0, 2, 1),
    "GRB": (1, 0, 2),
    "GBR": (1, 2, 0),
    "BRG": (2, 0, 1),
    "BGR": (2, 1, 0),
}


class ColorOrder(StrEnum):
    RGB = "RGB"
    RBG = "RBG"
    GRB = "GRB"
    GBR = "GBR"
    BRG = "BRG"
    BGR = "BGR"

    def lower(self) -> str:
        return self.value.lower()
