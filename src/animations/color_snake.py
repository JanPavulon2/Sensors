"""
Color Snake Animation

Multi-pixel rainbow snake moving across a single zone.
"""

import asyncio
import time
from typing import List

from animations.base import BaseAnimation
from models.color import Color
from models.frame import PixelFrame
from models.enums import FramePriority, FrameSource
from models.animation_params.animation_param_id import AnimationParamID
from models.animation_params.length_param import LengthParam
from models.animation_params.speed_param import SpeedParam
from models.animation_params.primary_color_hue_param import PrimaryColorHueParam


class ColorSnakeAnimation(BaseAnimation):
    """
    Color Snake animation - rainbow snake with hue gradient.

    A multi-pixel snake travels through the zone pixels.
    Each segment has a shifted hue, forming a rainbow tail.
    Base hue slowly rotates over time.

    Supported parameters:
    - SPEED: Snake movement speed
    - LENGTH: Snake length in pixels
    - PRIMARY_COLOR_HUE: Starting hue for the snake head
    """

    # ============================================================
    # Animation parameters (user-editable)
    # ============================================================

    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(),
        AnimationParamID.LENGTH: LengthParam(default=5, min_value=2, max_value=10),
        AnimationParamID.PRIMARY_COLOR_HUE: PrimaryColorHueParam(),
    }

    # ============================================================
    # Internal tuning constants (NOT user parameters)
    # ============================================================

    _HUE_STEP_PER_SEGMENT = 25        # hue offset between snake segments
    _HUE_DRIFT_PER_FRAME = 1          # how fast rainbow slowly rotates
    _MIN_DELAY = 0.01                 # fastest movement
    _MAX_DELAY = 0.10                 # slowest movement

    def __init__(self, zone, params):
        super().__init__(zone, params)

        self._position = 0
        self._base_hue = self.get_param(
            AnimationParamID.PRIMARY_COLOR_HUE, 0
        )

        self._pixel_count = self.pixel_count

    # ============================================================
    # Helpers
    # ============================================================

    def _calculate_delay(self) -> float:
        """Convert SPEED parameter to frame delay."""
        speed = self.get_param(AnimationParamID.SPEED, 50)
        return self._MAX_DELAY - (speed / 100) * (self._MAX_DELAY - self._MIN_DELAY)

    def _snake_pixels(self) -> List[Color]:
        """
        Build full pixel buffer for the zone.

        Returns:
            List[Color] of length = pixel_count
        """
        pixels = [Color.black()] * self._pixel_count

        length = self.get_param(AnimationParamID.LENGTH, 5)
        base_hue = self._base_hue

        for i in range(length):
            pos = (self._position - i) % self._pixel_count
            hue = (base_hue + i * self._HUE_STEP_PER_SEGMENT) % 360
            # pixels[pos] = Color.from_hue(hue, brightness=self.base_brightness)
            pixels[pos] = Color.from_hue(hue)

        return pixels

    # ============================================================
    # Animation step
    # ============================================================

    async def step(self) -> PixelFrame:
        """
        Generate a single animation frame.
        """
        pixels = self._snake_pixels()

        frame = PixelFrame(
            zone_pixels={self.zone_id: pixels},
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=0.12,
            partial=False,
        )

        # Advance snake
        self._position = (self._position + 1) % self._pixel_count
        self._base_hue = (self._base_hue + self._HUE_DRIFT_PER_FRAME) % 360

        await asyncio.sleep(self._calculate_delay())
        return frame
