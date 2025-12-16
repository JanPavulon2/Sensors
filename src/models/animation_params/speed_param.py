from __future__ import annotations

from models.animation_params.animation_param_id import AnimationParamID
from .int_range_param import IntRangeParam

class SpeedParam(IntRangeParam):
    key = AnimationParamID.SPEED

    def __init__(self, value: int | None = None):
        super().__init__(
            label="Speed",
            min_value=1,
            max_value=100,
            default=50,
            step=1,
            value=value,
        )
