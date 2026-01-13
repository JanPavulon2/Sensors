from __future__ import annotations
from .animation_param import AnimationParam


class IntRangeParam(AnimationParam):
    """Integer parameter with min/max/step - stateless definition."""

    def __init__(
        self,
        *,
        label: str,
        min_value: int,
        max_value: int,
        default: int,
        step: int = 1,
    ):
        self.label = label
        self.min = min_value
        self.max = max_value
        self.default = default
        self.step = step

    def adjust(self, current: int, delta: int) -> int:
        """Adjust current by delta*step, return clamped result"""
        new_value = current + delta * self.step
        return self.clamp(new_value)

    def clamp(self, value: int) -> int:
        """Clamp to [min, max]"""
        return max(self.min, min(self.max, int(value)))