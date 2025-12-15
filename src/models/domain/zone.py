"""Zone domain models"""

from dataclasses import dataclass, field
from models.color import Color
from models.enums import ParamID, ZoneID, ZoneRenderMode
from models.domain.animation import AnimationState
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

@dataclass
class ZoneState:
    """
    Mutable zone state from JSON.

    Preserves all state for mode switching:
    - color: Used by STATIC mode, preserved when in ANIMATION
    - animation: Used by ANIMATION mode, preserved when in STATIC
    """
    id: ZoneID
    color: Color
    brightness: int
    is_on: bool
    mode: ZoneRenderMode = ZoneRenderMode.STATIC
    animation: Optional[AnimationState] = None
    

@dataclass
class ZoneCombined:
    """Zone with config, state, and parameters"""
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