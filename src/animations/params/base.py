
from __future__ import annotations
from dataclasses import dataclass, fields
from typing import Any, Dict, List


@dataclass
class AnimationParamSpec:
    name: str
    min: int
    max: int
    step: int = 1
    wrap: bool = False


class AnimationParams:
    """
    Base class for animation parameter sets.
    """

    @classmethod
    def specs(cls) -> Dict[str, AnimationParamSpec]:
        """
        Must be overridden by subclasses.
        Returns mapping: field_name -> spec
        """
        raise NotImplementedError

    def list_fields(self) -> List[str]:
        return list(self.specs().keys())

    def adjust(self, field: str, delta: int) -> None:
        spec = self.specs()[field]
        value = getattr(self, field)

        new_value = value + delta * spec.step

        if spec.wrap:
            range_size = spec.max - spec.min + 1
            new_value = ((new_value - spec.min) % range_size) + spec.min
        else:
            new_value = max(spec.min, min(spec.max, new_value))

        setattr(self, field, new_value)
