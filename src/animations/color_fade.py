"""
Color Fade Animation

Smooth transition through hue spectrum (rainbow effect).
Cycles through the full 360° HSV hue spectrum smoothly on each zone independently.
"""

import time
from typing import Any, Dict

from animations.base import BaseAnimation
from models.animation_params.animation_param_id import AnimationParamID
from models.animation_params.speed_param import SpeedParam
from models.domain import ZoneCombined
from models.enums import FramePriority, FrameSource
from models.frame import SingleZoneFrame
from models.color import Color
from utils.logger import LogCategory, get_category_logger

log = get_category_logger(LogCategory.ANIMATION)


class ColorFadeAnimation(BaseAnimation):
    """
    Color fade animation: Smooth hue rotation through rainbow spectrum.

    Cycles through the full 360° hue spectrum smoothly.
    Brightness is preserved from zone's current setting.

    Supported parameters:
    - SPEED: Animation speed (1-100, default 50)
      - Speed 1 = ~20 seconds per full cycle
      - Speed 100 = ~2 seconds per full cycle
    """

    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(),
    }

    def __init__(self, zone: ZoneCombined, params: Dict[AnimationParamID, Any]):
        super().__init__(zone, params)
        self._start_time = time.monotonic()

    async def step(self) -> SingleZoneFrame:
        """Generate one animation frame"""
        speed = self.get_param(AnimationParamID.SPEED, 50)

        # Calculate cycle period (inverse of speed)
        # speed: 1-100 → period: 20-2 seconds per full 360° rotation
        period = max(2.0, 20.0 - (speed / 100) * 18.0)
        elapsed = time.monotonic() - self._start_time

        # Current hue based on elapsed time
        current_hue = int((elapsed / period) * 360) % 360

        # Create color with current hue
        color = Color.from_hue(current_hue)

        # Return frame for this zone with animation priority
        return SingleZoneFrame(
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            zone_id=self.zone_id,
            color=color,
            partial=True
        )
