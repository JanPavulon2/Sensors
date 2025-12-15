"""Parameter domain models"""

from dataclasses import dataclass
from typing import Any, Optional
from models.enums import ParamID, ParameterType, LogCategory
from utils.logger import get_logger

log = get_logger().for_category(LogCategory.CONFIG)


@dataclass(frozen=True)
class AnimationParam:
    id: ParamID
    display_name: str

    def cycle(self, current):
        raise NotImplementedError

    def adjust(self, current, delta):
        raise NotImplementedError
    
class IntRangeParam(AnimationParam):
    def __init__(self, id, min_v, max_v, step):
        self.min = min_v
        self.max = max_v
        self.step = step

    def adjust(self, current, delta):
        return max(self.min, min(self.max, current + delta * self.step))
    
class HueParam(AnimationParam):
    def adjust(self, current, delta):
        return (current + delta * 10) % 360
    
class EnumParam(AnimationParam):
    def __init__(self, id, values):
        self.values = values

    def cycle(self, current):
        idx = self.values.index(current)
        return self.values[(idx + 1) % len(self.values)]

@dataclass
class ParameterState:
    """Mutable parameter state from JSON"""
    id: ParamID
    value: Any

class ParameterConfig:
    """Immutable parameter configuration from YAML"""
    id: ParamID
    type: ParameterType
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[int] = None
    wraps: bool = False
    unit: Optional[str] = None
    description: str = ""

    def validate(self, value: Any) -> bool:
        """Check if value is within configured constraints"""
        if self.min is not None and value < self.min:
            return False
        if self.max is not None and value > self.max:
            return False
        return True

    def clamp(self, value: Any) -> Any:
        """Clamp value to min/max range"""
        if self.min is not None:
            value = max(self.min, value)
        if self.max is not None:
            value = min(self.max, value)
        return value



    