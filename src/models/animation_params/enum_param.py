from __future__ import annotations
from typing import List, Any
from .animation_param import AnimationParam


class EnumParam(AnimationParam):
    """
    Parameter cycling through predefined values.
    """

    values: List[Any]

    def adjust(self, delta: int) -> None:
        idx = self.values.index(self.value)
        idx = (idx + delta) % len(self.values)
        self.value = self.values[idx]

    def clamp(self, value: Any) -> Any:
        if value not in self.values:
            return self.default
        return value