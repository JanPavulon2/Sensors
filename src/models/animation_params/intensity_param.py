from __future__ import annotations

from models.animation_params.animation_param_id import AnimationParamID
from .float_range_param import FloatRangeParam


class IntensityParam(FloatRangeParam):
    """
    Intensity parameter - normalized 0.0 to 1.0 range.
    Backend value: 0-1 (float)
    Default: 0.5 (50%)
    """
    key = AnimationParamID.INTENSITY

    def __init__(self):
        super().__init__(
            label="Intensity",
            min_value=0.0,
            max_value=1.0,
            default=0.5,
            step=0.1,
        )
