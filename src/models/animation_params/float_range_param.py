from __future__ import annotations
from .animation_param import AnimationParam


class FloatRangeParam(AnimationParam):
    """Float parameter with min/max/step - stateless definition."""

    def __init__(
        self,
        *,
        label: str,
        min_value: float,
        max_value: float,
        default: float,
        step: float = 0.1,
    ):
        self.label = label
        self.min = min_value
        self.max = max_value
        self.default = default
        self.step = step

    def adjust(self, current: float, delta: int) -> float:
        """Adjust current by delta*step, return clamped result"""
        new_value = current + delta * self.step
        return self.clamp(new_value)

    def clamp(self, value: float) -> float:
        """Clamp to [min, max]"""
        return max(self.min, min(self.max, float(value)))
