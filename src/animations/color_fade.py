"""
Color Fade Animation

Smooth transition through hue spectrum (rainbow effect).
Cycles through the full 360° HSV hue spectrum smoothly on each zone independently.
"""

import time
from typing import Any, Dict

from animations.base import BaseAnimation
from models.animation_params import AnimationParamID, SpeedParam
from models.color import Color
from models.domain import ZoneCombined
from models.enums import FramePriority, FrameSource
from models.frame import SingleZoneFrame
from utils.logger import LogCategory, get_category_logger

log = get_category_logger(LogCategory.ANIMATION)


class ColorFadeAnimation(BaseAnimation):
    """
    Smooth hue rotation through the full HSV spectrum.
    """

    # ---- USER PARAMETERS ----
    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(),  # 1–100
    }

    # ---- ADMIN TUNING ----
    _MIN_PERIOD = 2.0     # seconds per full cycle
    _MAX_PERIOD = 20.0
    _HUE_RANGE = 360

    def __init__(self, zone: ZoneCombined, params: Dict[AnimationParamID, Any]):
        super().__init__(zone, params)
        self._start_time = time.monotonic()

    async def step(self) -> SingleZoneFrame:
        speed = self.get_param(AnimationParamID.SPEED, 50)
        elapsed = time.monotonic() - self._start_time

        period = max(
            self._MIN_PERIOD,
            self._MAX_PERIOD - (speed / 100.0) * (self._MAX_PERIOD - self._MIN_PERIOD),
        )

        phase = (elapsed / period) % 1.0
        hue = int(phase * self._HUE_RANGE)

        color = Color.from_hue(hue)

        return SingleZoneFrame(
            zone_id=self.zone_id,
            color=color,
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            partial=True,
        )