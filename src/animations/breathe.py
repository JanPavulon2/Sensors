"""
Breathe Animation

Smooth fade in/out effect (breathing) for all zones synchronously.
"""

import math
import time
from typing import Any, Dict

from animations.base import BaseAnimation
from models.animation_params.animation_param_id import AnimationParamID
from models.animation_params.brightness_param import BrightnessParam
from models.animation_params.speed_param import SpeedParam
from models.domain import ZoneCombined
from models.enums import FramePriority, FrameSource
from models.frame import SingleZoneFrame
from utils.logger import LogCategory, get_category_logger

log = get_category_logger(LogCategory.ANIMATION)


class BreatheAnimation(BaseAnimation):
    """
    Breathe animation: Smooth sinusoidal brightness modulation using zone base color.

    Supported parameters:
    - SPEED: Animation speed (1-100, default 50)
    - BRIGHTNESS: Max brightness scaling (0-100, default 100)
    """

    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(),
        AnimationParamID.BRIGHTNESS: BrightnessParam(),
    }

    def __init__(self, zone: ZoneCombined, params: Dict[AnimationParamID, Any]):
        super().__init__(zone, params)
        self._start_time = time.monotonic()

    async def step(self) -> SingleZoneFrame:
        """Generate one animation frame"""
        speed = self.get_param(AnimationParamID.SPEED, 50)
        brightness_percent = self.get_param(AnimationParamID.BRIGHTNESS, 100)

        # Calculate breathing cycle period (inverse of speed)
        # speed: 1-100 → period: 8.0-0.8 seconds
        period = max(0.8, 8.0 - (speed / 100) * 7.0)
        elapsed = time.monotonic() - self._start_time
        t = elapsed / period

        # Breathing curve: sine wave that oscillates 0..1
        # Add -π/2 phase shift so we start at minimum brightness
        phase = (math.sin(t * 2 * math.pi - math.pi / 2) + 1) / 2

        # Scale to 15%-100% so LED never fully turns off
        scale = 0.15 + phase * 0.85

        # Calculate final brightness
        base_brightness = self.base_brightness
        final_brightness = int(base_brightness * (brightness_percent / 100.0) * scale)

        # Apply brightness to base zone color
        color = self.base_color.with_brightness(final_brightness)

        return SingleZoneFrame(
            zone_id=self.zone_id,
            color=color,
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=0.12,  # Frame lifetime: ~120ms at 60 FPS
        )