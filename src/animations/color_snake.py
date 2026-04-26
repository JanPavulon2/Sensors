"""
Color Snake Animation

Multi-pixel rainbow snake moving across a single zone.
Fully deterministic: position and hue drift are derived from elapsed
wall-clock time, independent of frame rate or CPU speed.
"""

import time
from typing import List

from animations.base import BaseAnimation
from models.animation_params import AnimationParamID, LengthParam, SpeedParam, PrimaryColorHueParam
from models.color import Color
from models.frame import PixelFrame
from models.enums import FramePriority, FrameSource


class ColorSnakeAnimation(BaseAnimation):
    """
    Color Snake animation - rainbow snake with hue gradient.

    A multi-pixel snake travels through the zone pixels.
    Each segment has a shifted hue, forming a rainbow tail.
    Base hue slowly drifts over time.

    Movement is time-based: speed parameter controls pixels-per-second.
    Rendering always reflects the current wall-clock position regardless
    of how often step() is called.

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
        AnimationParamID.LENGTH: LengthParam(default=7, min_value=3, max_value=15),
        AnimationParamID.PRIMARY_COLOR_HUE: PrimaryColorHueParam(),
    }

    def __init__(self, zone, params):
        super().__init__(zone, params)
        self._start_time = time.monotonic()
        self._initial_hue = self.get_param(AnimationParamID.PRIMARY_COLOR_HUE, 0)
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

    async def step(self) -> PixelFrame:
        """
        Generate a single animation frame.
        """
        pixels = self._snake_pixels()

        return PixelFrame(
            zone_pixels={self.zone_id: pixels},
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=0.12,
            partial=False,
        )
