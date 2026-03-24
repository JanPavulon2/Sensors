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

    # Below this brightness (%) pixels are invisible on WS281x and cause flicker
    _MIN_VISIBLE_BRIGHTNESS = 2
    
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
        normalized_speed = speed / 100.0
        return self._MIN_PPS + normalized_speed * (self._MAX_PPS - self._MIN_PPS)


    def _snake_pixels(self, position: float, base_hue: float, length: int) -> List[Color]:
        """
        Build full pixel buffer with smooth brightness on both head and tail.

        The snake spans from a leading pixel (the one the head is entering)
        through the body to a fading tail. Both edges use smooth brightness
        transitions so the snake appears to swim continuously.

        Pixel layout relative to head_index (the last fully-entered pixel):
          pixel_offset = -1  →  leading pixel (head entering, fades IN)
          pixel_offset =  0  →  head pixel (brightest body pixel)
          pixel_offset =  N  →  Nth body pixel behind head (fading out)

        Leading pixel brightness = fractional_offset² (0 at entry, 100% when fully entered).
        Body/tail brightness = quadratic falloff from head to tail tip.
        """
        pixels = [Color.black()] * self._pixel_count

        fractional_offset = position % 1.0
        head_index = int(position) % self._pixel_count

        for pixel_offset in range(-1, length):
            pixel_index = (head_index - pixel_offset) % self._pixel_count

            if pixel_offset == -1:
                # Leading pixel: the head is entering this pixel.
                # fractional_offset = how far the head has moved into it (0→1).
                brightness_percent = int(fractional_offset ** 2 * 100)
                hue_distance = 0.0
            else:
                # Body and tail: standard quadratic falloff from head.
                distance_from_head = fractional_offset + pixel_offset
                normalized_distance = distance_from_head / length
                brightness_percent = int(max(0.0, 1.0 - normalized_distance) ** 2 * 100)
                hue_distance = distance_from_head

            if brightness_percent < self._MIN_VISIBLE_BRIGHTNESS:
                continue

            hue = int((base_hue + hue_distance * self._HUE_STEP_PER_SEGMENT) % 360)
            pixels[pixel_index] = Color.from_hue(hue).with_brightness(brightness_percent)

        return pixels

    async def step(self) -> PixelFrame:
        """Generate a single animation frame from wall-clock time."""
        speed = self.get_param(AnimationParamID.SPEED, 50)
        length = self.get_param(AnimationParamID.LENGTH, 5)

        elapsed = time.monotonic() - self._start_time
        pixels_per_second = self._speed_to_pps(speed)

        # Fractional position for smooth sub-pixel movement
        position = (elapsed * pixels_per_second) % self._pixel_count
        base_hue = (self._initial_hue + elapsed * self._HUE_DRIFT_PER_SECOND) % 360

        pixels = self._snake_pixels(position, base_hue, length)

        return PixelFrame(
            zone_pixels={self.zone_id: pixels},
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=0.12,
            partial=False,
        )
