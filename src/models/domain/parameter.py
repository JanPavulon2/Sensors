"""Parameter domain models"""

from dataclasses import dataclass
from typing import Any, Optional
from models.enums import ParamID, ParameterType, LogCategory
from utils.logger import get_logger

log = get_logger().for_category(LogCategory.CONFIG)


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
    """
    Combined parameter: Config (constraints) + State (value).

    Three-Layer Pattern:
    ====================
    The three-layer architecture separates concerns:

    - **Config** (ParameterConfig): Immutable metadata from YAML
      - Type, min, max, step, wrapping behavior
      - Loaded once at startup, never changes
      - Shared across all zones/animations using this parameter

    - **State** (ParameterState): Mutable runtime value from JSON
      - Current value only (minimal storage)
      - Persisted in state.json for resume-on-restart
      - Independent instance per zone/animation

    - **Combined** (ParameterCombined): Business logic and API
      - Validation, adjustment, convenience methods
      - Reconstructed at startup from config + state
      - Domain-friendly interface for controllers/services

    Why Three Layers?
    -----------------
    1. **Separation**: Config changes don't corrupt state files
       - Update min/max in parameters.yaml → state.json stays valid
       - State file is always minimal and compatible

    2. **Minimal State**: JSON stores only values, not metadata
       - Saves disk space and parsing time
       - Makes state files human-readable
       - Easy to upgrade parameters.yaml without breaking state

    3. **Rich API**: Combined provides domain-friendly interface
       - Callers don't juggle .config and .state
       - Validation is automatic (in setter)
       - Easy to add business logic (adjust, step, wrap, etc.)

    Convenience Properties:
    ----------------------
    Common properties proxied for ease of use:
    - param.value → param.state.value
    - param.id → param.config.id
    - param.type → param.config.type
    - param.min → param.config.min
    - param.max → param.config.max

    Example:
        >>> # Creating a parameter
        >>> config = ParameterConfig(
        ...     id=ParamID.ZONE_BRIGHTNESS,
        ...     type=ParameterType.PERCENTAGE,
        ...     min=0, max=100, step=10, wraps=False
        ... )
        >>> state = ParameterState(
        ...     id=ParamID.ZONE_BRIGHTNESS,
        ...     value=80
        ... )
        >>> param = ParameterCombined(config=config, state=state)

        >>> # Using convenience properties
        >>> param.value  # Get current value
        80
        >>> param.value = 90  # Set with validation
        >>> param.adjust(1)  # Adjust by steps (+10)
        >>> param.value
        100

        >>> # Access configuration
        >>> param.min
        0
        >>> param.max
        100
        >>> param.id
        <ParamID.ZONE_BRIGHTNESS: ...>

    Notes:
        All existing methods (validate, adjust, etc.) continue working.
        This class is reconstructed from config + state at each startup.
    """
    config: ParameterConfig
    state: ParameterState

    def __post_init__(self):
        if not self.config.validate(self.state.value):
            log.with_category(LogCategory.STATE).warn(f"Parameter {self.config.id.name} value {self.state.value} out of range, clamping")
            self.state.value = self.config.clamp(self.state.value)

    @property
    def value(self) -> Any:
        """Get current parameter value"""
        return self.state.value

    @value.setter
    def value(self, new_value: Any) -> None:
        """Set parameter value with validation

        Args:
            new_value: New value for the parameter

        Raises:
            ValueError: If value is outside configured min/max bounds
        """
        if not self.config.validate(new_value):
            raise ValueError(
                f"Value {new_value} out of range "
                f"[{self.config.min}, {self.config.max}]"
            )
        self.state.value = new_value

    @property
    def id(self) -> ParamID:
        """Get parameter ID (proxy to config)"""
        return self.config.id

    @property
    def type(self) -> ParameterType:
        """Get parameter type (proxy to config)"""
        return self.config.type

    @property
    def min(self) -> Optional[float]:
        """Get minimum allowed value (proxy to config)"""
        return self.config.min

    @property
    def max(self) -> Optional[float]:
        """Get maximum allowed value (proxy to config)"""
        return self.config.max

    def validate(self, value: Any) -> bool:
        """Check if value is within configured constraints (proxy to config)"""
        return self.config.validate(value)

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
        log.with_category(LogCategory.STATE).debug(f"Adjusted {self.config.id.name}: {old_value} → {new_value}")
