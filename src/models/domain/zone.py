"""Zone domain models"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from models.color import Color
from models.enums import ZoneID, ZoneRenderMode
from models.domain.animation import AnimationState
from utils.enum_helper import EnumHelper 

@dataclass(frozen=True)
class ZoneConfig:
    """Immutable zone configuration from YAML"""
    id: ZoneID
    display_name: str
    pixel_count: int
    enabled: bool
    reversed: bool
    order: int
    start_index: int
    end_index: int
    gpio: int = 18       # GPIO pin for this zone's LED strip (default: 18)

@dataclass
class ZoneState:
    """
    Mutable zone state from JSON with validation.

    Preserves all state for mode switching:
    - color: Used by STATIC mode, preserved when in ANIMATION
    - animation: Used by ANIMATION mode, preserved when in STATIC

    Validation rules:
    - brightness: 0-100 (percentage)
    - is_on: boolean
    - mode: STATIC or ANIMATION
    - color: valid Color instance
    - animation: valid AnimationState or None
    """
    id: ZoneID
    color: Color
    brightness: int
    is_on: bool
    mode: ZoneRenderMode = ZoneRenderMode.STATIC
    animation: Optional[AnimationState] = None

    def __post_init__(self) -> None:
        """Validate all fields after initialization"""
        self._validate_brightness(self.brightness)
        self._validate_is_on(self.is_on)
        self._validate_mode(self.mode)
        self._validate_color(self.color)
        self._validate_animation(self.animation)

    def __setattr__(self, name: str, value: Any) -> None:
        """Validate field values on any attribute assignment"""
        if name == 'brightness':
            self._validate_brightness(value)
        elif name == 'is_on':
            self._validate_is_on(value)
        elif name == 'mode':
            self._validate_mode(value)
        elif name == 'color':
            self._validate_color(value)
        elif name == 'animation':
            self._validate_animation(value)

        super().__setattr__(name, value)

    @staticmethod
    def _validate_brightness(value: Any) -> None:
        """Validate brightness is in range 0-100 (percentage)"""
        if not isinstance(value, (int, float)):
            raise TypeError(f"brightness must be int or float, got {type(value).__name__}")
        if not (0 <= value <= 100):
            raise ValueError(f"brightness must be 0-100 (percentage), got {value}")

    @staticmethod
    def _validate_is_on(value: Any) -> None:
        """Validate is_on is boolean"""
        if not isinstance(value, bool):
            raise TypeError(f"is_on must be bool, got {type(value).__name__}")

    @staticmethod
    def _validate_mode(value: Any) -> None:
        """Validate mode is valid ZoneRenderMode"""
        if not isinstance(value, ZoneRenderMode):
            raise TypeError(f"mode must be ZoneRenderMode, got {type(value).__name__}")

    @staticmethod
    def _validate_color(value: Any) -> None:
        """Validate color is valid Color instance"""
        if not isinstance(value, Color):
            raise TypeError(f"color must be Color instance, got {type(value).__name__}")

    @staticmethod
    def _validate_animation(value: Any) -> None:
        """Validate animation is None or valid AnimationState"""
        if value is not None and not isinstance(value, AnimationState):
            raise TypeError(f"animation must be None or AnimationState, got {type(value).__name__}")


@dataclass
class ZoneCombined:
    """Zone with config and state"""
    config: ZoneConfig
    state: ZoneState

    @property
    def id(self) -> ZoneID:
        """Get ZoneID enum"""
        return self.config.id
    
    @property
    def get_str_id(self) -> str:
        """Get string representation of ZoneID enum"""
        return EnumHelper.to_string(self.config.id)
    
    @property
    def brightness(self) -> int:
        """ Get current brightness from state """
        return self.state.brightness