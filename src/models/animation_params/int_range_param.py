from __future__ import annotations
from .animation_param import AnimationParam


class IntRangeParam(AnimationParam):
    """
    Integer parameter with min / max / step.
    """

    min_value: int
    max_value: int
    step: int

    def adjust(self, delta: int) -> None:
        new_value = self.value + delta * self.step
        self.value = self.clamp(new_value)

    def clamp(self, value: int) -> int:
        return max(self.min_value, min(self.max_value, int(value)))