from __future__ import annotations

from models.animation_params.animation_param_id import AnimationParamID
from .int_range_param import IntRangeParam


class HueParam(IntRangeParam):
    key = AnimationParamID.HUE
    label = "Hue"

    min_value = 0
    max_value = 359
    step = 5
    default = 180