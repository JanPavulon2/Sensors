from __future__ import annotations

from models.animation_params.animation_param_id import AnimationParamID
from .int_range_param import IntRangeParam


class PrimaryColorHueParam(IntRangeParam):
    key = AnimationParamID.PRIMARY_COLOR_HUE

    def __init__(self):
        super().__init__(
            label="Primary Color Hue",
            min_value=0,
            max_value=359,
            default=0,
            step=10,
        )
