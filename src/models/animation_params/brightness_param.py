from __future__ import annotations

from models.animation_params.animation_param_id import AnimationParamID
from .int_range_param import IntRangeParam


class BrightnessParam(IntRangeParam):
    key = AnimationParamID.BRIGHTNESS
    label = "Brightness"

    min_value = 0
    max_value = 100
    step = 10
    default = 100
    