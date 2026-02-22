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

    # Speed range: 0 → MIN_PPS, 100 → MAX_PPS (pixels per second)
    _MIN_PPS = 2.0
    _MAX_PPS = 60.0

    # Hue tuning constants
    _HUE_STEP_PER_SEGMENT = 25        # hue offset between snake segments
    _HUE_DRIFT_PER_SECOND = 30.0      # degrees per second of rainbow rotation

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

    def _speed_to_pps(self, speed: int) -> float:
        """Convert speed parameter (0-100) to pixels per second."""
        t = speed / 100.0
        return self._MIN_PPS + t * (self._MAX_PPS - self._MIN_PPS)

    def _snake_pixels(self, position: int, base_hue: float) -> List[Color]:
        """Build full pixel buffer for the zone."""
        pixels = [Color.black()] * self._pixel_count

        length = self.get_param(AnimationParamID.LENGTH, 5)

        for i in range(length):
            pos = (position - i) % self._pixel_count
            hue = (base_hue + i * self._HUE_STEP_PER_SEGMENT) % 360
            pixels[pos] = Color.from_hue(hue)

        return pixels

    async def step(self) -> PixelFrame:
        """Generate a single animation frame from wall-clock time."""
        speed = self.get_param(AnimationParamID.SPEED, 50)

        elapsed = time.monotonic() - self._start_time
        pps = self._speed_to_pps(speed)

        # Deterministic position and hue from elapsed time
        position = int(elapsed * pps) % self._pixel_count
        base_hue = (self._initial_hue + elapsed * self._HUE_DRIFT_PER_SECOND) % 360

        pixels = self._snake_pixels(position, base_hue)

        return PixelFrame(
            zone_pixels={self.zone_id: pixels},
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=0.12,
            partial=False,
        )
