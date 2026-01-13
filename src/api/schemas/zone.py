"""
Zone schemas - Pydantic models for zone-related requests/responses
Includes: Color, ZoneState, ZoneRenderMode, and complete Zone information
"""

from pydantic import BaseModel, Field, model_validator, validator
from typing import Optional, Dict, Any, Literal, Tuple
from enum import Enum

from models.animation_params.animation_param_id import AnimationParamID
from models.enums import AnimationID, ZoneRenderMode


class ColorRequest(BaseModel):
    """Color specification in a request - flexible to support all color modes"""
    mode: Literal["RGB", "HUE", "PRESET"]
    
    # HUE mode
    hue: Optional[int] = Field(
        None,
        ge=0,
        le=360,
        description="Hue value 0-360 (used in HUE and HSV modes)"
    )

    # RGB mode
    rgb: Optional[list[int]] = Field(
        None,
        description="RGB values [r, g, b] each 0-255 (RGB mode)"
    )

    # PRESET mode
    preset_name: Optional[str] = Field(
        None,
        description="Preset name like 'RED', 'WARM_WHITE', 'COOL_WHITE' (PRESET mode)"
    )

    @model_validator(mode="after")
    def validate_color(self):
        if self.mode == "HUE" and self.hue is None:
            raise ValueError("hue is required for HUE mode")
        if self.mode == "RGB" and self.rgb is None:
            raise ValueError("rgb is required for RGB mode")
        if self.mode == "PRESET" and self.preset_name is None:
            raise ValueError("preset_name is required for PRESET mode")
        return self
    
    
class SetZoneBrightnessRequest(BaseModel):
    """Request to update zone brightness"""
    brightness: int = Field(
        ge=0,
        le=100,
        description="New brightness 0-100%"
    )

class SetZoneIsOnRequest(BaseModel):
    """Request to change zone's power on/off state"""
    is_on: bool = Field(
        description="Zone power on / power off state"
    )

class SetZoneColorRequest(BaseModel):
    color: ColorRequest
    
class SetZoneRenderModeRequest(BaseModel):
    """Request to change zone render mode"""
    render_mode: Literal["STATIC", "ANIMATION"] = Field(
        description="New render mode: STATIC (solid color) or ANIMATION (animated)"
    )

class SetZoneAnimationRequest(BaseModel):
    """Request to change zone animation"""
    animation_id: AnimationID = Field(
        description="Zone's animation ID"
    )
    
class SetZoneAnimationParamRequest(BaseModel):
    """Request to change zone animation's parameter value"""
    param_id: AnimationParamID
    value: Any

class SetZoneAnimationParamsRequest(BaseModel):
    """Request to update multiple animation parameters at once"""
    parameters: Dict[AnimationParamID, Any] = Field(
        description="Dictionary of parameter names and their values. Keys are parameter IDs (e.g., 'speed', 'intensity')"
    )


class ColorModeEnum(str, Enum):
    """Color mode enumeration - matches domain ColorMode"""
    RGB = "RGB"
    HSV = "HSV"
    HUE = "HUE"
    PRESET = "PRESET"

class ZoneRenderModeEnum(str, Enum):
    """Zone render mode - what the zone is currently displaying"""
    STATIC = "STATIC"          # Static color (no animation)
    ANIMATION = "ANIMATION"    # Running animation
