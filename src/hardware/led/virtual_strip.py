from __future__ import annotations
from typing import  List
from models.color import Color
from hardware.led.strip_interface import IPhysicalStrip

class VirtualStrip(IPhysicalStrip):
    
    def __init__(
        self, 
        pixel_count: int,
        brightness: int = 255
    ):
        self.pixel_count = pixel_count
        self._buffer = [Color.black() for _ in range(self.pixel_count)]
        
    @property
    def led_count(self) -> int:
        return self.pixel_count


    def set_pixel(self, index: int, color: Color) -> None:
        if 0 <= index < self.led_count:
            self._buffer[index] = color

    def get_pixel(self, index: int) -> Color:
        if 0 <= index < self.led_count:
            return self._buffer[index]
        return Color.black()
                 
    def get_frame(self) -> List[Color]:
        return self._buffer

    def apply_frame(self, pixels: List[Color]) -> None:
        self._buffer = pixels[:self.led_count]

    def show(self) -> None:
        pass

    def clear(self) -> None:
        self._buffer = [Color.black() for _ in range(self.led_count)]
