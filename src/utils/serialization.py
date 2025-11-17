"""
Serialization utilities - Central enum and model serialization for JSON API

Provides bidirectional conversion between:
- Enums ↔ Strings (ZoneID, AnimationID, ParamID, ColorMode, etc.)
- Domain models ↔ Dicts (Zone, Animation, Color, etc.)

Single source of truth for frontend JSON API compatibility.
"""

from typing import TypeVar, Type, Any, Dict, Optional
from enum import Enum

from models.enums import ZoneID, AnimationID, ParamID, ColorMode, MainMode, ZoneMode
from models.color import Color
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.GENERAL)

T = TypeVar('T', bound=Enum)


class Serializer:
    """Central enum and model serialization for JSON API"""

    # ========================================================================
    # ENUM SERIALIZATION
    # ========================================================================

    @staticmethod
    def enum_to_str(value: Optional[Enum]) -> Optional[str]:
        """Convert any enum to string name"""
        return value.name if value else None

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
    def str_to_enum(value: str, enum_type: Type[T]) -> T:
        """Convert string to enum, raise ValueError if invalid"""
        try:
            return enum_type[value]
        except KeyError:
            raise ValueError(f"Invalid {enum_type.__name__}: {value}")

    # ========================================================================
    # PARAMETER DICT CONVERSION
    # ========================================================================

    @staticmethod
    def params_enum_to_str(params: Dict[ParamID, Any]) -> Dict[str, Any]:
        """Convert ParamID enum keys to strings for JSON/API"""
        return {k.name: v for k, v in params.items()}

    @staticmethod
    def params_str_to_enum(params: Dict[str, Any]) -> Dict[ParamID, Any]:
        """Convert string param names to ParamID enums from JSON/API"""
        return {ParamID[k]: v for k, v in params.items()}

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
            result["rgb"] = list(color._rgb)
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

    # ========================================================================
    # ANIMATION SERIALIZATION
    # ========================================================================

    @staticmethod
    def animation_to_dict(anim) -> Dict[str, Any]:
        """
        Serialize animation to dict

        Args:
            anim: AnimationCombined object

        Returns:
            Dict with id, display_name, description, enabled, parameters
        """
        return {
            "id": anim.config.id.name,
            "display_name": anim.config.display_name,
            "description": anim.config.description,
            "enabled": anim.state.enabled,
            "parameters": Serializer.params_enum_to_str(anim.get_all_params()),
        }

    # ========================================================================
    # APPLICATION STATE SERIALIZATION
    # ========================================================================

    @staticmethod
    def main_mode_to_str(mode: MainMode) -> str:
        """Convert MainMode enum to string"""
        return mode.name

    @staticmethod
    def str_to_main_mode(value: str) -> MainMode:
        """Convert string to MainMode enum"""
        return MainMode[value]

    @staticmethod
    def zone_mode_to_str(mode: ZoneMode) -> str:
        """Convert ZoneMode enum to string"""
        return mode.name

    @staticmethod
    def str_to_zone_mode(value: str) -> ZoneMode:
        """Convert string to ZoneMode enum"""
        try:
            return ZoneMode[value]
        except KeyError:
            raise ValueError(f"Invalid ZoneMode: {value}")
