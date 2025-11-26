"""
Color model - Unified color representation

Handles color in multiple formats (HUE, PRESET, RGB) and automatic conversions.
Uses ColorManager for preset data and utils.colors for conversion functions.
"""

from .enums import ColorMode
from dataclasses import dataclass
from typing import Optional, Tuple, TYPE_CHECKING
from utils.colors import hue_to_rgb, rgb_to_hue, find_closest_preset_name

if TYPE_CHECKING:
    from managers import ColorManager

@dataclass
class Color:
    """
    Unified color representation

    Encapsulates color in multiple formats and handles conversions.
    Always maintains optimal storage format and renders to RGB for hardware.

    Storage strategy:
    - HUE mode: Store hue (0-360), compute RGB on demand
    - PRESET mode: Store preset_name + cache RGB for whites
    - RGB mode: Store direct RGB (future)

    Examples:
        # Create from HUE
        color = Color.from_hue(120)  # Green

        # Create from preset
        color = Color.from_preset("warm_white", color_manager)

        # Always get RGB for rendering
        r, g, b = color.to_rgb()

        # Adjust hue
        color = color.adjust_hue(10)

        # Convert to preset mode (find closest)
        color = color.to_preset_mode(color_manager)
    """

    # Storage (only ONE of these is primary source)
    _hue: Optional[int] = None                    # 0-360 for HUE mode
    _preset_name: Optional[str] = None            # "warm_white", "red", etc. for PRESET mode
    _rgb: Optional[Tuple[int, int, int]] = None   # (r,g,b) cached or direct

    # Mode tracking
    mode: ColorMode = ColorMode.HUE

    # === CONSTRUCTORS ===

    @classmethod
    def from_hue(cls, hue: int) -> 'Color':
        """
        Create from HUE (0-360)

        Args:
            hue: Hue value in degrees (0-360)

        Returns:
            Color object in HUE mode
        """
        return cls(_hue=hue % 360, mode=ColorMode.HUE)

    @classmethod
    def from_preset(cls, preset_name: str, color_manager: 'ColorManager') -> 'Color':
        """
        Create from preset name

        Args:
            preset_name: Name from preset_order (e.g., "warm_white", "red")
            color_manager: ColorManager instance

        Returns:
            Color object in PRESET mode
        """
        if preset_name not in color_manager.preset_colors:
            raise ValueError(f"Unknown preset: {preset_name}. Available: {list(color_manager.preset_colors.keys())}")

        rgb = color_manager.get_preset_rgb(preset_name)

        # Cache RGB for white presets (they need exact RGB, not HUE conversion)
        if color_manager.is_white_preset(preset_name):
            return cls(_preset_name=preset_name, _rgb=rgb, mode=ColorMode.PRESET)
        else:
            # For saturated colors, also compute HUE for potential mode switching
            hue = rgb_to_hue(*rgb)
            return cls(_preset_name=preset_name, _hue=hue, _rgb=rgb, mode=ColorMode.PRESET)

    @classmethod
    def from_rgb(cls, r: int, g: int, b: int) -> 'Color':
        """
        Create from direct RGB (future use)

        Args:
            r, g, b: RGB values (0-255)

        Returns:
            Color object in RGB mode
        """
        return cls(_rgb=(r, g, b), mode=ColorMode.RGB)

    # === RENDERING (always returns RGB) ===

    def to_rgb(self) -> Tuple[int, int, int]:
        """
        Get RGB for rendering (source of truth for hardware)

        Priority:
        1. Cached RGB (for whites and presets)
        2. HUE → RGB conversion
        3. Direct RGB

        Returns:
            (r, g, b) tuple with values 0-255
        """
        if self._rgb is not None:
            return self._rgb

        if self._hue is not None:
            return hue_to_rgb(self._hue)

        raise ValueError("Color has no RGB or HUE data")

    def to_hue(self) -> int:
        """
        Get HUE representation (for adjustments)

        Returns:
            Hue value 0-360
        """
        if self._hue is not None:
            return self._hue

        if self._rgb is not None:
            return rgb_to_hue(*self._rgb)

        raise ValueError("Cannot convert to HUE")

    # === ADJUSTMENTS ===

    def adjust_hue(self, delta: int) -> 'Color':
        """
        Adjust hue by delta degrees (converts to HUE mode if needed)

        Args:
            delta: Hue change in degrees (can be negative)

        Returns:
            New Color object with adjusted hue
        """
        current_hue = self.to_hue()
        new_hue = (current_hue + delta) % 360
        return Color.from_hue(new_hue)

    def next_preset(self, delta: int, color_manager: 'ColorManager') -> 'Color':
        """
        Cycle to next/previous preset

        Args:
            delta: Step count (+1 = next, -1 = previous)
            color_manager: ColorManager instance

        Returns:
            New Color object with next preset
        """
        preset_order = color_manager.preset_order

        if self._preset_name:
            current_idx = preset_order.index(self._preset_name)
        else:
            # Find closest preset to current color
            current_idx = preset_order.index(find_closest_preset_name(self.to_rgb(), color_manager))

        new_idx = (current_idx + delta) % len(preset_order)
        return Color.from_preset(preset_order[new_idx], color_manager)

    # === MODE CONVERSIONS ===

    def to_preset_mode(self, color_manager: 'ColorManager') -> 'Color':
        """
        Convert to closest preset

        Args:
            color_manager: ColorManager instance

        Returns:
            New Color object in PRESET mode
        """
        rgb = self.to_rgb()
        closest_preset = find_closest_preset_name(rgb, color_manager)
        return Color.from_preset(closest_preset, color_manager)

    def to_hue_mode(self) -> 'Color':
        """
        Convert to HUE mode

        Returns:
            New Color object in HUE mode
        """
        hue = self.to_hue()
        return Color.from_hue(hue)

    # === SERIALIZATION ===

    def to_dict(self) -> dict:
        """
        Serialize for state.json

        Returns:
            Dict with minimal data (mode + hue OR preset_name)
        """
        if self.mode == ColorMode.HUE:
            return {
                "mode": "HUE",
                "hue": self._hue
            }
        elif self.mode == ColorMode.PRESET:
            return {
                "mode": "PRESET",
                "preset_name": self._preset_name
            }
        else:  # RGB
            return {
                "mode": "RGB",
                "rgb": self._rgb
            }

    @classmethod
    def from_dict(cls, data: dict, color_manager: 'ColorManager') -> 'Color':
        """
        Deserialize from state.json

        Args:
            data: Dict from to_dict()
            color_manager: ColorManager instance

        Returns:
            Color object
        """
        mode = data["mode"]

        if mode == "HUE":
            return cls.from_hue(data["hue"])
        elif mode == "PRESET":
            return cls.from_preset(data["preset_name"], color_manager)
        else:  # RGB
            return cls.from_rgb(*data["rgb"])

    # === BRIGHTNESS SCALING ===

    @staticmethod
    def apply_brightness(r: int, g: int, b: int, brightness: int) -> Tuple[int, int, int]:
        """
        Apply brightness scaling to RGB values.

        Clamps brightness to 0-100 range and scales RGB values proportionally.

        Args:
            r, g, b: Color values (0-255)
            brightness: Brightness percentage (0-100, will be clamped)

        Returns:
            (r, g, b) tuple scaled by brightness

        Example:
            r, g, b = Color.apply_brightness(255, 100, 0, 80)  # 80% brightness
        """
        brightness = max(0, min(100, brightness))
        return (
            int(r * brightness / 100),
            int(g * brightness / 100),
            int(b * brightness / 100),
        )

    def with_brightness(self, brightness: int) -> 'Color':
        """
        Return new Color with brightness applied (preserves color mode).

        Unlike apply_brightness() static method which works on RGB tuples,
        this instance method preserves the original color mode (HUE/PRESET).

        Args:
            brightness: Brightness percentage (0-100, will be clamped)

        Returns:
            New Color object with brightness applied and mode preserved

        Example:
            >>> red_hue = Color.from_hue(0)  # HUE mode
            >>> dimmed = red_hue.with_brightness(50)
            >>> dimmed.mode  # Still ColorMode.HUE (not RGB!)
            >>> dimmed.to_rgb()  # (127, 0, 0) - 50% brightness

            >>> warm = Color.from_preset("warm_white", color_manager)
            >>> dimmed = warm.with_brightness(80)
            >>> dimmed.mode  # Still ColorMode.PRESET
        """
        # Get base RGB values
        r, g, b = self.to_rgb()

        # Apply brightness scaling
        r_scaled, g_scaled, b_scaled = Color.apply_brightness(r, g, b, brightness)

        # Preserve original mode when creating scaled color
        if self.mode == ColorMode.HUE:
            # HUE mode: keep hue reference, cache scaled RGB
            return Color(
                _hue=self._hue,
                _rgb=(r_scaled, g_scaled, b_scaled),
                mode=ColorMode.HUE
            )
        elif self.mode == ColorMode.PRESET:
            # PRESET mode: keep preset name + hue, cache scaled RGB
            return Color(
                _preset_name=self._preset_name,
                _hue=self._hue,
                _rgb=(r_scaled, g_scaled, b_scaled),
                mode=ColorMode.PRESET
            )
        else:
            # RGB mode: just scale RGB
            return Color.from_rgb(r_scaled, g_scaled, b_scaled)

    @staticmethod
    def black() -> 'Color':
        return Color.from_rgb(0, 0, 0)
    
    @staticmethod
    def white() -> 'Color':
        return Color.from_rgb(255, 255, 255)
    
    @staticmethod
    def red() -> 'Color':
        return Color.from_rgb(255, 0, 0)
    
    @staticmethod
    def green() -> 'Color':
        return Color.from_rgb(0, 255, 0)
    
    @staticmethod
    def blue() -> 'Color':
        return Color.from_rgb(0, 0, 255)
    
    # === STRING REPRESENTATION ===

    def __str__(self) -> str:
        """String representation for debugging"""
        if self.mode == ColorMode.HUE:
            return f"Color(HUE={self._hue}°)"
        elif self.mode == ColorMode.PRESET:
            return f"Color(PRESET={self._preset_name})"
        else:
            return f"Color(RGB={self._rgb})"

    def __repr__(self) -> str:
        return self.__str__()
