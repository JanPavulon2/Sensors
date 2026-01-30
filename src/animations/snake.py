"""
Snake Animation

Single or multi-pixel snake travels through all zones sequentially.
"""

import time
from typing import List

from animations.base import BaseAnimation
from models.animation_params import AnimationParamID, SpeedParam, PrimaryColorHueParam, IntRangeParam
from models.color import Color
from models.frame import PixelFrame
from models.enums import FramePriority, FrameSource
from utils.colors import hue_to_rgb
from utils.logger import get_category_logger, LogCategory

log = get_category_logger(LogCategory.ANIMATION)



class SnakeAnimation(BaseAnimation):
    """
    Pixel-level snake animation inside a single zone.
    """

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

        self._position = 0
        self._last_step_time = time.monotonic()

    async def step(self) -> PixelFrame | None:
        speed = self.get_param(AnimationParamID.SPEED, 50)
        hue = self.get_param(AnimationParamID.PRIMARY_COLOR_HUE, 0)
        length = self.get_param(AnimationParamID.LENGTH, 5)

        pixel_count = self.pixel_count
        if pixel_count <= 0:
            return None

        length = max(1, min(length, pixel_count))

        # speed → delay
        min_delay = 0.01
        max_delay = 0.1
        delay = max_delay - (speed / 100.0) * (max_delay - min_delay)

        now = time.monotonic()
        if now - self._last_step_time < delay:
            return None

        self._last_step_time = now

        # Base color for snake
        base_color = Color.from_hue(hue)

        # Start with all pixels off
        pixels: List[Color] = [Color.black() for _ in range(pixel_count)]

        # Draw snake
        for i in range(length):
            pos = (self._position - i) % pixel_count
            fade = max(0.0, 1.0 - i * 0.2)

            pixels[pos] = base_color.with_brightness(
                int(self.base_brightness * fade)
            )

        self._position = (self._position + 1) % pixel_count

        return PixelFrame(
            zone_pixels={self.zone_id: pixels},
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=delay * 2,
            partial=False,
        )
        