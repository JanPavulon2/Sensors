"""
Parameter system - Type definitions and parameter registry

Defines parameter types, validation, and metadata for all system parameters.
Parameters are loaded from config.yaml (zone_parameters, animation_base_parameters, additional_animation_parameters).
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, List, Any, Dict
from models.enums import ParamID
import yaml
from pathlib import Path


class ParameterType(Enum):
    """Parameter value types with validation rules"""
    COLOR = auto()           # Color parameter (HUE or PRESET mode)
    PERCENTAGE = auto()      # 0-100% (displayed with %, stored as 0-100)
    RANGE_0_255 = auto()     # 0-255 integer range (legacy brightness)
    RANGE_CUSTOM = auto()    # Custom min/max range
    BOOLEAN = auto()         # True/False toggle


@dataclass
class Parameter:
    """
    Parameter definition with type, constraints, and display metadata

    Attributes:
        id: ParamID enum identifying this parameter
        type: ParameterType (COLOR, PERCENTAGE, etc.)
        default: Default value
        min_val: Minimum value (for range types)
        max_val: Maximum value (for range types)
        step: Increment/decrement step size
        wraps: If True, wraps around at boundaries (e.g., hue 360→0)
        unit: Display unit string ("°", "%", "px", None)
        color_modes: List of color modes if type=COLOR (["HUE", "PRESET"])
        description: Human-readable description

    Examples:
        # HUE color parameter
        Parameter(
            id=ParamID.ZONE_COLOR,
            type=ParameterType.COLOR,
            color_modes=["HUE", "PRESET"],
            default=0,
            description="Zone color"
        )

        # Percentage parameter
        Parameter(
            id=ParamID.ZONE_BRIGHTNESS,
            type=ParameterType.PERCENTAGE,
            default=100,
            min_val=0,
            max_val=100,
            step=5,
            wraps=False,
            unit="%",
            description="Zone brightness"
        )

        # Custom range parameter
        Parameter(
            id=ParamID.LENGTH,
            type=ParameterType.RANGE_CUSTOM,
            default=5,
            min_val=2,
            max_val=20,
            step=1,
            wraps=False,
            unit="px",
            description="Snake length in pixels"
        )
    """
    id: ParamID
    type: ParameterType
    default: Any
    min_val: Optional[int] = None
    max_val: Optional[int] = None
    step: Optional[int] = None
    wraps: bool = False
    unit: Optional[str] = None
    color_modes: Optional[List[str]] = None
    description: str = ""

    def validate(self, value: Any) -> bool:
        """
        Validate value against parameter constraints

        Args:
            value: Value to validate

        Returns:
            True if valid, False otherwise
        """
        if self.type == ParameterType.BOOLEAN:
            return isinstance(value, bool)

        if self.type == ParameterType.COLOR:
            # Color values are validated by Color class
            return True

        # Range types
        if not isinstance(value, (int, float)):
            return False

        if self.min_val is not None and value < self.min_val:
            return False

        if self.max_val is not None and value > self.max_val:
            return False

        return True

    def clamp(self, value: int) -> int:
        """
        Clamp value to valid range (or wrap if wraps=True)

        Args:
            value: Input value

        Returns:
            Clamped/wrapped value
        """
        if self.min_val is None or self.max_val is None:
            return value

        if self.wraps:
            # Wrap around (e.g., hue 360 → 0)
            range_size = self.max_val - self.min_val + 1
            return self.min_val + ((value - self.min_val) % range_size)
        else:
            # Clamp to bounds
            return max(self.min_val, min(self.max_val, value))

    def adjust(self, current: int, delta: int) -> int:
        """
        Adjust value by delta steps

        Args:
            current: Current value
            delta: Number of steps (+/-)

        Returns:
            New value (clamped/wrapped)
        """
        step_size = self.step or 1
        new_value = current + (delta * step_size)
        return self.clamp(new_value)

    def format_value(self, value: Any) -> str:
        """
        Format value for display

        Args:
            value: Value to format

        Returns:
            Formatted string (e.g., "50%", "120°", "5px")
        """
        if self.type == ParameterType.BOOLEAN:
            return "ON" if value else "OFF"

        if self.type == ParameterType.COLOR:
            # Color formatting handled by Color class
            return str(value)

        # Numeric types
        if self.unit:
            return f"{value}{self.unit}"
        else:
            return str(value)
