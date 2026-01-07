"""
Breathe Animation

Smooth fade in/out effect (breathing) for all zones synchronously.
"""

import math
import time
from typing import Any, Dict

from animations.base import BaseAnimation
from models.animation_params import AnimationParamID, SpeedParam, IntensityParam
from models.domain import ZoneCombined
from models.enums import FramePriority, FrameSource
from models.frame import SingleZoneFrame
from utils.logger import LogCategory, get_category_logger

log = get_category_logger(LogCategory.ANIMATION)


class BreatheAnimation(BaseAnimation):
    """
    Smooth sinusoidal brightness breathing animation.
    """

    # ---- USER PARAMETERS ----
    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(),        # 1–100
        AnimationParamID.INTENSITY: IntensityParam(),  # 0–100
    }

    # ---- ADMIN TUNING ----
    #_MIN_SCALE = 0.15          # minimal brightness scale (15%)
    _MIN_SCALE = 0.15          # minimal brightness scale (15%)
    _MAX_SCALE = 1.0           # max brightness
    _MIN_PERIOD = 0.8          # seconds
    _MAX_PERIOD = 8.0          # seconds
    _PHASE_OFFSET = -math.pi / 2

    def __init__(self, zone: ZoneCombined, params: Dict[AnimationParamID, Any]):
        super().__init__(zone, params)
        self._start_time = time.monotonic()

    async def step(self) -> SingleZoneFrame:
        # ---- USER PARAMS ----
        speed_param = self.get_param(AnimationParamID.SPEED, 50)          # 1–100
        intensity_param = self.get_param(AnimationParamID.INTENSITY, 0.5)  # 0.0–1.0

        # ---- TIME ----
        elapsed = time.monotonic() - self._start_time

        # speed → period
        period = max(
            self._MIN_PERIOD,
            self._MAX_PERIOD - (speed_param / 100.0) * (self._MAX_PERIOD - self._MIN_PERIOD),
        )

        # ---- PHASE 0..1 ----
        phase = (math.sin((elapsed / period) * 2 * math.pi + self._PHASE_OFFSET) + 1) / 2

        # ---- SCALE ----
        scale = self._MIN_SCALE + phase * (self._MAX_SCALE - self._MIN_SCALE)

        # ---- FINAL COLOR ----
        final_scale = scale * intensity_param
        color = self.base_color.with_brightness(int(final_scale * 100))

        # log.info(
        #     f"Animation frame: ",
        #     speed_param=speed_param,
        #     brightness_param=intensity_param,
        #     period=period,
        #     scale=scale,
        #     final_scale=final_scale,
        #     color=color,
        # )
        
        return SingleZoneFrame(
            zone_id=self.zone_id,
            color=color,
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=0.2,
        )