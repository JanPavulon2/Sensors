"""
Zone schemas - Pydantic models for zone-related requests/responses
Includes: Color, ZoneState, ZoneRenderMode, and complete Zone information
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from enum import Enum

from models.animation_params.animation_param_id import AnimationParamID
from models.enums import AnimationID, ZoneRenderMode


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

class ZoneSetRenderModeRequest(BaseModel):
    """Request to change zone render mode"""
    render_mode: ZoneRenderMode = Field(
        description="New render mode: STATIC (solid color) or ANIMATION (animated)"
    )

class ZoneSetAnimationRequest(BaseModel):
    """Request to change zone animation"""
    id: AnimationID = Field(
        description="Zone's animation ID"
    )
    parameters: Dict[AnimationParamID, Any]
    
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


class ColorRequest(BaseModel):
    """Color specification in a request - flexible to support all color modes"""
    mode: ColorModeEnum = Field(description="Color mode (RGB, HSV, HUE, or PRESET)")

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

    # Optional brightness/saturation (for HSV mode)
    brightness: Optional[int] = Field(
        None,
        ge=0,
        le=255,
        description="Brightness 0-255 (used in multiple modes)"
    )
    saturation: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Saturation 0-100 (HSV mode)"
    )

    @validator('rgb')
    def validate_rgb(cls, v):
        if v is not None:
            if len(v) != 3 or not all(0 <= val <= 255 for val in v):
                raise ValueError('RGB must be [r, g, b] with values 0-255')
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "mode": "HUE",
                    "hue": 240,
                    "description": "Pure blue hue"
                },
                {
                    "mode": "RGB",
                    "rgb": [255, 0, 0],
                    "description": "Pure red RGB"
                },
                {
                    "mode": "PRESET",
                    "preset": "WARM_WHITE",
                    "description": "Named warm white preset"
                }
            ]
        }


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


class ZoneColorUpdateRequest(BaseModel):
    """Request to update zone color"""
    color: ColorRequest = Field(description="New color")

    class Config:
        json_schema_extra = {
            "example": {
                "color": {
                    "mode": "HUE",
                    "hue": 240
                }
            }
        }








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
