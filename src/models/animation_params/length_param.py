from __future__ import annotations

from models.animation_params.animation_param_id import AnimationParamID
from .int_range_param import IntRangeParam


class LengthParam(IntRangeParam):
    key = AnimationParamID.LENGTH

    def __init__(self, value: int | None = None):
        super().__init__(
            label="Length",
            min_value=1,
            max_value=300,
            default=100,
            step=1,
            value=value,
        )
