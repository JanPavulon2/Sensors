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
    
    
class ZoneSetBrightnessRequest(BaseModel):
    """Request to update zone brightness"""
    brightness: int = Field(
        ge=0,
        le=100,
        description="New brightness 0-100%"
    )

class ZoneSetIsOnRequest(BaseModel):
    """Request to change zone's power on/off state"""
    is_on: bool = Field(
        description="Zone power on / power off state"
    )

class ZoneSetColorRequest(BaseModel):
    color: ColorRequest
    
class ZoneSetRenderModeRequest(BaseModel):
    """Request to change zone render mode"""
    render_mode: Literal["STATIC", "ANIMATION"] = Field(
        description="New render mode: STATIC (solid color) or ANIMATION (animated)"
    )

class ZoneSetAnimationRequest(BaseModel):
    """Request to change zone animation"""
    animation_id: AnimationID = Field(
        description="Zone's animation ID"
    )
    
    
    
class ZoneSetAnimationParamRequest(BaseModel):
    """Request to change zone animation's parameter value"""
    value: Any



    
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
    OFF = "OFF"                # Zone powered off




class ColorResponse(BaseModel):
    """Color in a response - complete color information"""
    mode: ColorModeEnum = Field(description="Current color mode")
    hue: Optional[int] = Field(None, description="Hue value if applicable")
    rgb: Optional[list[int]] = Field(None, description="RGB representation [r, g, b]")
    preset_name: Optional[str] = Field(None, description="Preset name if in PRESET mode")
    brightness: Optional[int] = Field(None, description="Brightness component")
    saturation: Optional[int] = Field(None, description="Saturation component")


class ZoneStateResponse(BaseModel):
    """Zone state - what's currently being displayed on the zone"""
    color: ColorResponse = Field(description="Current color")
    brightness: float = Field(
        ge=0,
        le=255,
        description="Zone brightness level 0-255"
    )
    is_on: bool = Field(description="Zone powered on/off state")
    render_mode: ZoneRenderModeEnum = Field(
        description="What zone is displaying: STATIC (color), ANIMATION (animated), or OFF (powered off)"
    )
    animation_id: Optional[str] = Field(
        None,
        description="Running animation ID if render_mode=ANIMATION, else null"
    )


class ZoneResponse(BaseModel):
    """Complete zone information - configuration + current state"""
    id: str = Field(description="Zone ID (e.g., 'FLOOR', 'LAMP')")
    name: str = Field(description="Display name (e.g., 'Floor Strip')")
    pixel_count: int = Field(ge=1, description="Number of addressable pixels in zone")
    state: ZoneStateResponse = Field(description="Current zone state")
    gpio: int = Field(description="GPIO pin number controlling this zone's LED strip")
    layout: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional layout info (coordinates, rotation, physical arrangement)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "FLOOR",
                "name": "Floor Strip",
                "pixel_count": 45,
                "state": {
                    "color": {
                        "mode": "HUE",
                        "hue": 240,
                        "brightness": None,
                        "rgb": [0, 0, 255],
                        "preset": None,
                        "saturation": None
                    },
                    "brightness": 200,
                    "is_on": True,
                    "render_mode": "STATIC",
                    "animation_id": None
                },
                "gpio": 18,
                "layout": None
            }
        }


class ZoneListResponse(BaseModel):
    """List of all zones"""
    zones: list[ZoneResponse]
    count: int = Field(description="Total number of zones")

class ZoneUpdateRequest(BaseModel):
    """Request to update entire zone (flexible update)"""
    color: Optional[ColorRequest] = Field(None, description="New color (optional)")
    brightness: Optional[float] = Field(
        None,
        ge=0,
        le=255,
        description="New brightness (optional)"
    )
    enabled: Optional[bool] = Field(None, description="Enable/disable zone (optional)")
    render_mode: Optional[ZoneRenderModeEnum] = Field(
        None,
        description="Change render mode (optional)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "color": {
                    "mode": "HUE",
                    "hue": 240
                },
                "brightness": 200,
                "enabled": True,
                "render_mode": "STATIC"
            }
        }
