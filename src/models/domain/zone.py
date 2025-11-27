"""Zone domain models"""

from dataclasses import dataclass
from models.color import Color
from models.enums import ParamID, ZoneID, ZoneRenderMode, AnimationID
from models.domain.parameter import ParameterCombined
from typing import Dict, Any, Optional
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

    @property
    def tag(self) -> str:
        """Tag = lowercase zone id name (e.g., 'lamp', 'strip')"""
        return self.id.name.lower()
    
    @property
    def total_leds(self) -> int:
        """Total physical LEDs (pixel_count * 3)"""
        return self.pixel_count * 3


@dataclass
class ZoneState:
    """
    Mutable zone state from JSON.

    Preserves all state for mode switching:
    - color: Used by STATIC mode, preserved when in ANIMATION
    - animation_id + animation_parameters: Used by ANIMATION mode, preserved when in STATIC
    """
    id: ZoneID
    color: Color
    mode: ZoneRenderMode = ZoneRenderMode.STATIC
    animation_id: Optional[AnimationID] = None
    animation_parameters: Optional[Dict[ParamID, Any]] = None
    

@dataclass
class ZoneCombined:
    """Zone with config, state, and parameters"""
    config: ZoneConfig
    state: ZoneState
    parameters: Dict[ParamID, ParameterCombined]

    def get_param_value(self, param_id: ParamID) -> Any:
        """Get current parameter value"""
        return self.parameters[param_id].state.value

    def set_param_value(self, param_id: ParamID, value: Any) -> None:
        """Set parameter value with validation"""
        param = self.parameters[param_id]
        if not param.config.validate(value):
            value = param.config.clamp(value)
        param.state.value = value

    def adjust_param(self, param_id: ParamID, delta: int) -> None:
        """Adjust parameter by delta steps"""
        self.parameters[param_id].adjust(delta)

    def calculate_indices(self, previous_end_index: int):
        """
        Calculate start/end indices based on previous zone's end index

        Args:
            previous_end_index: End index of the previous zone (-1 if this is first zone)
        """
        if not self.config.enabled:
            self.start_index = -1
            self.end_index = -1
            return

        self.start_index = previous_end_index + 1 if previous_end_index >= 0 else 0
        self.end_index = self.start_index + self.config.pixel_count - 1

    @property
    def id(self) -> ZoneID:
        """Get ZoneID enum"""
        return self.config.id
    
    def get_str_id(self) -> str:
        """Get string representation of ZoneID enum"""
        return EnumHelper.to_string(self.config.id)
    
    @property
    def brightness(self) -> int:
        """
        Get current brightness from parameters

        Brightness is stored in parameters, not state, since it's a true parameter
        with min/max/step configuration.
        """
        if ParamID.ZONE_BRIGHTNESS not in self.parameters:
            return 100  # Default if parameter not configured
        return self.get_param_value(ParamID.ZONE_BRIGHTNESS)

    def get_rgb(self) -> tuple[int, int, int]:
        """
        Get current RGB color with brightness applied

        Returns (0, 0, 0) if zone is disabled, otherwise returns color with brightness.
        """
        # Disabled zones are always black
        if not self.config.enabled:
            return (0, 0, 0)

        r, g, b = self.state.color.to_rgb()
        brightness_factor = self.brightness / 100.0
        return (
            int(r * brightness_factor),
            int(g * brightness_factor),
            int(b * brightness_factor)
        )
        
    def get_color(self) -> Color:
        """
        Get current color 

        Returns black if zone is disabled, otherwise returns color.
        """
        # Disabled zones are always black
        if not self.config.enabled:
            return Color.black()

        color = self.state.color
        return color