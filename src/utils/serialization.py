"""
Serialization utilities - Central enum and model serialization for JSON API

Provides bidirectional conversion between:
- Enums ↔ Strings (ZoneID, AnimationID, AnimationParamID, ColorMode, etc.)
- Domain models ↔ Dicts (Zone, Animation, Color, etc.)

Single source of truth for frontend JSON API compatibility.
"""

from typing import TypeVar, Type, Any, Dict, Optional
from enum import Enum

from models.domain.animation import AnimationState
from models.enums import ZoneID, AnimationID, ColorMode, ZoneRenderMode
from models.color import Color
from models.animation_params import (
    AnimationParamID,
    AnimationParam,
    SpeedParam,
    BrightnessParam,
    HueParam,
    PrimaryColorHueParam,
    LengthParam,
    IntRangeParam,
)
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.GENERAL)

T = TypeVar('T', bound=Enum)


class Serializer:
    """Central enum and model serialization for JSON API"""

    # ========================================================================
    # ENUM SERIALIZATION
    # ========================================================================
    
    @staticmethod
    def to_str(value) -> Optional[str]:
        """
        Polymorphic conversion: handles both Enum and str types (for mixed-type scenarios)

        Args:
            value: Enum, str, or None

        Returns:
            String representation or None

        Use this for zone_colors dicts and other contexts where types may be mixed.
        For strict API serialization, use enum_to_str() instead.
        """
        if value is None:
            return None
        if isinstance(value, Enum):
            return value.name
        if isinstance(value, str):
            return value
        return str(value)


    @staticmethod
    def enum_to_str(value: Optional[Enum]) -> Optional[str]:
        """Convert any enum to string name"""
        return value.name if value else None

    @staticmethod
    def str_to_enum(value: str, enum_type: Type[T]) -> T:
        """Convert string to enum, raise ValueError if invalid"""
        try:
            return enum_type[value]
        except KeyError:
            raise ValueError(f"Invalid {enum_type.__name__}: {value}")

    # ========================================================================
    # ZONE SERIALIZATION
    # ========================================================================

    @staticmethod
    def zone_to_dict(zone) -> Dict[str, Any]:
        """
        Serialize zone to JSON-compatible dict

        Args:
            zone: ZoneCombined object

        Returns:
            Dict with id, display_name, pixel_count, enabled, state
        """
        return {
            "id": zone.config.id.name,
            "display_name": zone.config.display_name,
            "pixel_count": zone.config.pixel_count,
            "enabled": zone.config.enabled,
            "brightness": zone.brightness,
            "color": Serializer.color_to_dict(zone.state.color),
        }

        
    # ========================================================================
    # ZONE MODE SERIALIZATION
    # ========================================================================

    @staticmethod
    def zone_render_mode_to_str(mode: ZoneRenderMode) -> str:
        """Convert ZoneRenderMode enum to string"""
        return mode.name

    @staticmethod
    def str_to_zone_render_mode(value: str) -> ZoneRenderMode:
        """Convert string to ZoneRenderMode enum"""
        try:
            return ZoneRenderMode[value]
        except KeyError:
            raise ValueError(f"Invalid ZoneRenderMode: {value}")


    # ========================================================================
    # ANIMATION SERIALIZATION
    # ========================================================================

    @staticmethod
    def animation_state_to_dict(anim_state: AnimationState) -> Dict[str, Any]:
        """
        Serialize animation state to dict
        
        Args:
            anim_state: AnimationState object

        Returns:
            Dict with animation id, parameters with values
        """
        return {
            "id": anim_state.id,
            "parameters": [p.name for p in anim_state.parameters],
        }


    # ========================================================================
    # ANIMATION PARAMETER DICT CONVERSION
    # ========================================================================

    @staticmethod
    def animation_params_enum_to_str(animation_params: Dict[AnimationParamID, Any]) -> Dict[str, Any]:
        """
        Convert AnimationParamID enum keys to strings for JSON/API.

        Transforms: {AnimationParamID.SPEED: 50} → {"speed": 50}
        """
        return {param_id.value: value for param_id, value in animation_params.items()}

    @staticmethod
    def animation_params_str_to_enum(animation_params: Dict[str, Any]) -> Dict[AnimationParamID, Any]:
        """
        Convert string param names to AnimationParamID enums from JSON/API.

        Transforms: {"speed": 50} → {AnimationParamID.SPEED: 50}
        Skips unknown parameters with a warning.
        """
        result = {}
        for param_str, value in animation_params.items():
            try:
                # Convert string value to AnimationParamID enum (using enum value, not name)
                param_id = AnimationParamID(param_str)
                result[param_id] = value
            except ValueError:
                log.warn(f"Unknown animation parameter: {param_str}, skipping")
        return result

    # ========================================================================
    # COLOR SERIALIZATION
    # ========================================================================

    @staticmethod
    def color_to_dict(color: Color) -> Dict[str, Any]:
        """
        Serialize color to dict

        Args:
            color: Color object

        Returns:
            Dict with mode and mode-specific data
        """
        result: Dict[str, Any] = {"mode": color.mode.name}

        if color.mode == ColorMode.HUE:
            result["hue"] = color._hue
        elif color.mode == ColorMode.RGB:
            result["rgb"] = list(color.to_rgb())
        elif color.mode == ColorMode.PRESET:
            result["preset_name"] = color._preset_name

        return result

    @staticmethod
    def dict_to_color(data: Dict[str, Any], color_manager=None) -> Color:
        """
        Deserialize dict to Color

        Args:
            data: Dict with mode and mode-specific fields
            color_manager: ColorManager instance (required for PRESET mode)

        Returns:
            Color object
        """
        try:
            mode = ColorMode[data["mode"]]

            if mode == ColorMode.HUE:
                return Color.from_hue(data["hue"])
            elif mode == ColorMode.RGB:
                return Color.from_rgb(*data["rgb"])
            elif mode == ColorMode.PRESET:
                if color_manager is None:
                    raise ValueError("color_manager required for PRESET mode deserialization")
                return Color.from_preset(data["preset_name"], color_manager)

            raise ValueError(f"Unsupported color mode: {mode}")
        except (KeyError, TypeError, ValueError) as e:
            log.error(f"Failed to deserialize color: {e}")
            raise
