from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
from models.enums import ZoneID
from models.color import Color
from zone_layer.zone_pixel_mapper import ZonePixelMapper
from hardware.led.strip_interface import IPhysicalStrip

class ZoneStrip:
    """
    Logical multi-zone wrapper over one physical strip.
    """

    def __init__(self, hardware: IPhysicalStrip, mapper: ZonePixelMapper) -> None:
        self.hw = hardware
        self.mapper = mapper

    def set_zone_color(self, zone_id: ZoneID, color: Color, show: bool = True) -> None:
        for i in self.mapper.get_indices(zone_id):
            self.hw.set_pixel(i, color)
        if show:
            self.hw.show()

    def set_zone_pixels(self, zone_id: ZoneID, colors: List[Color], show: bool = True) -> None:
        """
        colors: logical list ordered according to zone logical orientation
        """
        indices = self.mapper.get_indices(zone_id)
        for phys, col in zip(indices, colors):
            self.hw.set_pixel(phys, col)
        if show:
            self.hw.show()

    def clear(self, show: bool = True) -> None:
        self.hw.clear()
        if show:
            self.hw.show()
