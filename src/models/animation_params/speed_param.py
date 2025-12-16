from __future__ import annotations

from models.animation_params.animation_param_id import AnimationParamID
from .int_range_param import IntRangeParam


class SpeedParam(IntRangeParam):
    key = AnimationParamID.SPEED
    label = "Speed"

    min_value = 1
    max_value = 100
    step = 0
    default = 50