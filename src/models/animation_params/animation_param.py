
from __future__ import annotations
from enum import Enum
from typing import Any
from abc import ABC, abstractmethod

from models.animation_params.animation_param_id import AnimationParamID
from models.enums import ParamID


    
class AnimationParam(ABC):
    """
    Base class for all animation parameters.

    Param = something user can edit (via encoder / UI / API).
    This class defines:
    - how param is identified
    - how it is validated
    - how it is adjusted
    """
    
    key: AnimationParamID
    label: str          
    default: Any
    
    def __init__(self, value: Any | None = None):
        self.value = value if value is not None else self.default

    @abstractmethod
    def adjust(self, delta: int) -> None:
        """Adjust value by encoder delta"""
        ...

    @abstractmethod
    def clamp(self, value: Any) -> Any:
        """Clamp value to valid range"""
        ...

    def set(self, value: Any) -> None:
        self.value = self.clamp(value)

    def get(self) -> Any:
        return self.value

    def to_engine(self) -> Any:
        """Value passed to animation engine"""
        return self.value