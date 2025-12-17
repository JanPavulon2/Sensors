
from __future__ import annotations
from enum import Enum
from typing import Any
from abc import ABC, abstractmethod

from models.animation_params.animation_param_id import AnimationParamID

class AnimationParam(ABC):
    """
    Stateless parameter definition (metadata + adjustment logic).
    No instance holds mutable state. Runtime values in BaseAnimation.params.
    """

    key: AnimationParamID
    label: str
    default: Any

    @abstractmethod
    def adjust(self, current: Any, delta: int) -> Any:
        """Adjust current → new_value (clamped)"""
        ...

    @abstractmethod
    def clamp(self, value: Any) -> Any:
        """Clamp to valid range"""
        ...