"""
Snake Animation

Single or multi-pixel snake travels through a zone.
Fully deterministic: position is derived from elapsed wall-clock time,
independent of frame rate or CPU speed.
"""

import time
from typing import List

from animations.base import BaseAnimation
from models.animation_params import AnimationParamID, LengthParam, SpeedParam, PrimaryColorHueParam
from models.color import Color
from models.frame import PixelFrame
from models.enums import FramePriority, FrameSource


class SnakeAnimation(BaseAnimation):
    """
    Pixel-level snake animation inside a single zone.

    Movement is time-based: speed parameter controls pixels-per-second.
    Rendering always reflects the current wall-clock position regardless
    of how often step() is called.

    Uses sub-pixel fractional positioning for smooth movement:
    - Leading pixel fades in with quadratic brightness as it enters
    - Body pixels use quadratic brightness falloff toward the tail
    - Minimum brightness threshold prevents WS281x flicker
    """

    # Speed range: 0 → MIN_PPS, 100 → MAX_PPS (pixels per second)
    _MIN_PPS = 2.0
    _MAX_PPS = 60.0

    # Below this brightness %, pixels are skipped to prevent WS281x flicker
    _MIN_VISIBLE_BRIGHTNESS = 2

    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(),
        AnimationParamID.PRIMARY_COLOR_HUE: PrimaryColorHueParam(),
        AnimationParamID.LENGTH: LengthParam(default=1, min_value=1, max_value=10, step=1,)
    }

    def __init__(self, zone, params):
        super().__init__(zone, params)
        self._start_time = time.monotonic()

    def _speed_to_pps(self, speed: int) -> float:
        """Convert speed parameter (0-100) to pixels per second."""
        normalized = speed / 100.0
        return self._MIN_PPS + normalized * (self._MAX_PPS - self._MIN_PPS)

    def _snake_pixels(self, position: float, base_color: Color, length: int) -> List[Color]:
        """Build pixel array with smooth sub-pixel brightness falloff.

        pixel_offset -1 is the leading pixel that fades in ahead of the head.
        pixel_offset 0..length are the body pixels with quadratic falloff.
        """
        pixel_count = self.pixel_count

        # Start with all pixels off
        pixels: List[Color] = [Color.black()] * pixel_count

        fractional_offset = position % 1.0
        head_index = int(position) % pixel_count

        # Draw snake: leading pixel (-1), body (0..length)
        for pixel_offset in range(-1, length + 1):
            pixel_index = (head_index - pixel_offset) % pixel_count

            if pixel_offset == -1:
                # Leading pixel fades in with quadratic curve as head enters
                brightness_percent = int(fractional_offset ** 2 * 100)
            else:
                # Body/tail: quadratic brightness falloff from head to tail
                distance_from_head = fractional_offset + pixel_offset
                normalized_distance = distance_from_head / length
                brightness_percent = int(max(0.0, 1.0 - normalized_distance) ** 2 * 100)

            # Skip dim pixels to prevent WS281x flicker
            if brightness_percent < self._MIN_VISIBLE_BRIGHTNESS:
                continue

            brightness = int(self.base_brightness * brightness_percent / 100)
            pixels[pixel_index] = base_color.with_brightness(brightness)

        return pixels

    async def step(self) -> PixelFrame | None:
        speed = self.get_param(AnimationParamID.SPEED, 50)
        hue = self.get_param(AnimationParamID.PRIMARY_COLOR_HUE, 0)
        length = self.get_param(AnimationParamID.LENGTH, 5)

        pixel_count = self.pixel_count
        if pixel_count <= 0:
            return None

        length = max(1, min(length, pixel_count))

        # Deterministic fractional position from elapsed time
        elapsed = time.monotonic() - self._start_time
        pixels_per_second = self._speed_to_pps(speed)
        position = (elapsed * pixels_per_second) % pixel_count

        # Base color for snake
        base_color = Color.from_hue(hue)

        # Build pixel array with smooth brightness falloff
        pixels = self._snake_pixels(position, base_color, length)

        return PixelFrame(
            zone_pixels={self.zone_id: pixels},
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=0.12,
            partial=False,
        )
