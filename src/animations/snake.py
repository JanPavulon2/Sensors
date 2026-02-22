"""
Snake Animation

Single or multi-pixel snake travels through a zone.
Fully deterministic: position is derived from elapsed wall-clock time,
independent of frame rate or CPU speed.
"""

import time
from typing import List

from animations.base import BaseAnimation
from models.animation_params import AnimationParamID, SpeedParam, PrimaryColorHueParam, IntRangeParam
from models.color import Color
from models.frame import PixelFrame
from models.enums import FramePriority, FrameSource


class SnakeAnimation(BaseAnimation):
    """
    Pixel-level snake animation inside a single zone.

    Movement is time-based: speed parameter controls pixels-per-second.
    Rendering always reflects the current wall-clock position regardless
    of how often step() is called.
    """

    # Speed range: 0 → MIN_PPS, 100 → MAX_PPS (pixels per second)
    _MIN_PPS = 2.0
    _MAX_PPS = 60.0

    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(),
        AnimationParamID.PRIMARY_COLOR_HUE: PrimaryColorHueParam(),
        AnimationParamID.LENGTH: IntRangeParam(
            label="Snake Length",
            min_value=1,
            max_value=10,
            default=5,
            step=1,
        ),
    }

    def __init__(self, zone, params):
        super().__init__(zone, params)
        self._start_time = time.monotonic()

    def _speed_to_pps(self, speed: int) -> float:
        """Convert speed parameter (0-100) to pixels per second."""
        t = speed / 100.0
        return self._MIN_PPS + t * (self._MAX_PPS - self._MIN_PPS)

    async def step(self) -> PixelFrame | None:
        speed = self.get_param(AnimationParamID.SPEED, 50)
        hue = self.get_param(AnimationParamID.PRIMARY_COLOR_HUE, 0)
        length = self.get_param(AnimationParamID.LENGTH, 5)

        pixel_count = self.pixel_count
        if pixel_count <= 0:
            return None

        length = max(1, min(length, pixel_count))

        # Deterministic position from elapsed time
        elapsed = time.monotonic() - self._start_time
        pps = self._speed_to_pps(speed)
        position = int(elapsed * pps) % pixel_count

        # Base color for snake
        base_color = Color.from_hue(hue)

        # Start with all pixels off
        pixels: List[Color] = [Color.black() for _ in range(pixel_count)]

        # Draw snake with fading tail
        for i in range(length):
            pos = (position - i) % pixel_count
            fade = max(0.0, 1.0 - i * 0.2)
            pixels[pos] = base_color.with_brightness(
                int(self.base_brightness * fade)
            )

        return PixelFrame(
            zone_pixels={self.zone_id: pixels},
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=0.12,
            partial=False,
        )
