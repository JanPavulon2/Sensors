# hardware/led/strip_interface.py
"""
IPhysicalStrip Protocol
========================
Hardware abstraction for LED strips.
Minimal contract for any physical driver (WS281x, APA102, etc).
"""

from __future__ import annotations
from typing import Protocol, List
from models.color import Color


class IPhysicalStrip(Protocol):
    """
    Protocol defining minimal LED strip hardware interface.

    All implementations must provide:
    - led_count: total pixels
    - set_pixel: buffer single pixel (no immediate show)
    - get_pixel: read buffered pixel state
    - apply_frame: atomic push of full frame (single DMA)
    - show: flush buffer to hardware
    - clear: turn off all LEDs
    """

    @property
    def led_count(self) -> int:
        """Total number of addressable pixels."""
        ...

    def set_pixel(self, index: int, color: Color) -> None:
        """
        Set pixel color in buffer (does not push to hardware).
        Call show() or apply_frame() to render.
        """
        ...

    def get_pixel(self, index: int) -> Color:
        """Read buffered pixel color (for transitions)."""
        ...
        
    def get_frame(self) -> List[Color]:
        """Read buffered pixel frame (for transitions)."""
        ...
        
    def apply_frame(self, pixels: List[Color]) -> None:
        """
        Atomic push of entire frame to hardware (single DMA transfer).
        Preferred over multiple set_pixel + show for performance.
        """
        ...

    def show(self) -> None:
        """Push buffered pixels to hardware (DMA transfer)."""
        ...

    def clear(self) -> None:
        """Turn off all LEDs (set to black + show)."""
        ...
