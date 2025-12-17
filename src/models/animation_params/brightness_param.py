from __future__ import annotations

from models.animation_params.animation_param_id import AnimationParamID
from .int_range_param import IntRangeParam


class BrightnessParam(IntRangeParam):
    key = AnimationParamID.BRIGHTNESS

    def __init__(self):
        super().__init__(
            label="Brightness",
            min_value=0,
            max_value=100,
            default=100,
            step=1,
        )
