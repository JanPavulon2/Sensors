from __future__ import annotations
from .animation_param import AnimationParam


class IntRangeParam(AnimationParam):
    """
    Integer parameter with min / max / step.
    """
    
    def __init__(
        self,
        *,
        label: str,
        min_value: int,
        max_value: int,
        default: int,
        step: int = 1,
        value: int | None = None,
    ):
        self.label = label
        self.min = min_value
        self.max = max_value
        self.default = default
        self.step = step

        super().__init__(value=value)
        
    def adjust(self, delta: int) -> None:
        new_value = self.value + delta * self.step
        self.value = self.clamp(new_value)

    def clamp(self, value: int) -> int:
        return max(self.min, min(self.max, int(value)))