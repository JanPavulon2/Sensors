"""
Rainbow Animation

Full rainbow spectrum spread across all zone pixels, scrolling over time.
Fully deterministic: hue offset is derived from elapsed wall-clock time,
independent of frame rate or CPU speed.
"""

import time
from typing import List

from animations.base import BaseAnimation
from models.animation_params import AnimationParamID, SpeedParam
from models.color import Color
from models.frame import PixelFrame
from models.enums import FramePriority, FrameSource


class RainbowAnimation(BaseAnimation):
    """
    Rainbow animation - full hue spectrum scrolling across the zone.

    The entire 360-degree hue range is mapped across all pixels,
    creating a continuous rainbow. The rainbow drifts over time,
    controlled by the speed parameter.

    Supported parameters:
    - SPEED: How fast the rainbow scrolls across pixels
    """

    # Speed range: 0 → MIN_DPS, 100 → MAX_DPS (degrees per second of hue drift)
    _MIN_DPS = 10.0
    _MAX_DPS = 180.0

    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(),
    }

    def __init__(self, zone, params):
        super().__init__(zone, params)
        self._start_time = time.monotonic()
        self._pixel_count = self.pixel_count

    def _speed_to_dps(self, speed: int) -> float:
        """Convert speed parameter (0-100) to degrees per second of hue drift."""
        t = speed / 100.0
        return self._MIN_DPS + t * (self._MAX_DPS - self._MIN_DPS)

    async def step(self) -> PixelFrame | None:
        if self._pixel_count <= 0:
            return None

        speed = self.get_param(AnimationParamID.SPEED, 50)
        elapsed = time.monotonic() - self._start_time
        hue_offset = (elapsed * self._speed_to_dps(speed)) % 360

        pixels: List[Color] = []
        for i in range(self._pixel_count):
            hue = (hue_offset + (i / self._pixel_count) * 360) % 360
            pixels.append(Color.from_hue(hue))

        return PixelFrame(
            zone_pixels={self.zone_id: pixels},
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=0.12,
            partial=False,
        )
