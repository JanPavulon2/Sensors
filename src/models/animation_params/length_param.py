from __future__ import annotations

from models.animation_params.animation_param_id import AnimationParamID
from .int_range_param import IntRangeParam


class LengthParam(IntRangeParam):
    key = AnimationParamID.LENGTH

    def __init__(self, 
        *,
        min_value: int,
        max_value: int,
        default: int,
        step: int = 1
    ):
        super().__init__(
            label="Length",
            min_value=min_value,
            max_value=max_value,
            default=default,
            step=step,
        )
