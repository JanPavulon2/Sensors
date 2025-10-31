"""Parameter domain models"""

from dataclasses import dataclass
from typing import Any, Optional
from models.enums import ParamID, ParameterType, LogCategory
from utils.logger import get_logger

log = get_logger()


@dataclass(frozen=True)
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


@dataclass
class ParameterState:
    """Mutable parameter state from JSON"""
    id: ParamID
    value: Any


@dataclass
class ParameterCombined:
    """Parameter with both config and state"""
    config: ParameterConfig
    state: ParameterState

    def __post_init__(self):
        if not self.config.validate(self.state.value):
            log.warning(LogCategory.STATE, f"Parameter {self.config.id.name} value {self.state.value} out of range, clamping")
            self.state.value = self.config.clamp(self.state.value)

    def adjust(self, delta: int) -> None:
        """Adjust parameter value by delta steps"""
        # Validate step is configured
        if self.config.step is None:
            raise ValueError(f"Parameter {self.config.id.name} has no step configured")

        old_value = self.state.value
        new_value = old_value + (delta * self.config.step)

        if self.config.wraps:
            # Wrapping requires min/max to be set
            if self.config.min is None or self.config.max is None:
                raise ValueError(f"Parameter {self.config.id.name} wraps but min/max not configured")

            range_size = (self.config.max - self.config.min) + 1
            new_value = self.config.min + ((new_value - self.config.min) % range_size)
        else:
            # Check if already at min/max boundary before adjusting
            if delta < 0 and self.config.min is not None and old_value <= self.config.min:
                return  # Already at minimum, skip adjustment
            if delta > 0 and self.config.max is not None and old_value >= self.config.max:
                return  # Already at maximum, skip adjustment

            new_value = self.config.clamp(new_value)

        # Skip if value didn't actually change
        if new_value == old_value:
            return

        self.state.value = new_value
        log.debug(LogCategory.STATE, f"Adjusted {self.config.id.name}: {old_value} → {new_value}")
