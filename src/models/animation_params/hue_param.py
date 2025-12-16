from __future__ import annotations

from models.animation_params.animation_param_id import AnimationParamID
from .int_range_param import IntRangeParam

class HueParam(IntRangeParam):
    key = AnimationParamID.HUE

    def __init__(self, value: int | None = None):
        super().__init__(
            label="Hue",
            min_value=0,
            max_value=359,
            default=0,
            step=5,
            value=value,
        )
