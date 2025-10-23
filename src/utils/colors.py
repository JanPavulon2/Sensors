"""
Color conversion utilities

Pure functions for color space conversions and color distance calculations.
Preset color data is loaded from config/colors.yaml via ColorManager.
"""

from typing import Tuple


def hue_to_rgb(hue: int) -> Tuple[int, int, int]:
    """
    Convert hue (0-360) to RGB (0-255)

    Simple HSV to RGB conversion with S=1, V=1 (full saturation and value).

    Args:
        hue: Hue value in degrees (0-360)

    Returns:
        (r, g, b) tuple with values 0-255

    Example:
        r, g, b = hue_to_rgb(0)    # Red
        r, g, b = hue_to_rgb(120)  # Green
        r, g, b = hue_to_rgb(240)  # Blue
    """
    hue = hue % 360

    if hue < 60:
        return (255, int(hue * 4.25), 0)
    elif hue < 120:
        return (int((120 - hue) * 4.25), 255, 0)
    elif hue < 180:
        return (0, 255, int((hue - 120) * 4.25))
    elif hue < 240:
        return (0, int((240 - hue) * 4.25), 255)
    elif hue < 300:
        return (int((hue - 240) * 4.25), 0, 255)
    else:
        return (255, 0, int((360 - hue) * 4.25))


def rgb_to_hue(r: int, g: int, b: int) -> int:
    """
    Convert RGB (0-255) to hue (0-360)

    Converts RGB color to hue angle. Returns 0 for grayscale/white colors.
    Note: Loses saturation information!

    Args:
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)

    Returns:
        Hue value in degrees (0-360)

    Example:
        hue = rgb_to_hue(255, 0, 0)      # 0 (Red)
        hue = rgb_to_hue(0, 255, 0)      # 120 (Green)
        hue = rgb_to_hue(0, 0, 255)      # 240 (Blue)
        hue = rgb_to_hue(255, 255, 255)  # 0 (White - no hue)
    """
    if r == g == b:
        return 0

    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    max_c = max(r_norm, g_norm, b_norm)
    min_c = min(r_norm, g_norm, b_norm)
    delta = max_c - min_c

    # Special handling for low saturation (white/gray colors)
    saturation = delta / max_c if max_c > 0 else 0
    if saturation < 0.2:
        # For white-ish colors, derive hue from RGB ratio
        # warm_white (255,200,150): yellowish -> ~30°
        # white (255,255,255): neutral -> 0°
        # cool_white (200,220,255): blueish -> ~210°
        if r > g and r > b:
            return 30  # Warm (reddish/yellow tint)
        elif b > r and b > g:
            return 210  # Cool (blue tint)
        else:
            return 0  # Neutral white

    if delta == 0:
        return 0

    if max_c == r_norm:
        hue = 60 * (((g_norm - b_norm) / delta) % 6)
    elif max_c == g_norm:
        hue = 60 * (((b_norm - r_norm) / delta) + 2)
    else:
        hue = 60 * (((r_norm - g_norm) / delta) + 4)

    return int(hue) % 360


def rgb_distance(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """
    Calculate Euclidean distance between two RGB colors

    Used for finding closest preset.

    Args:
        rgb1, rgb2: RGB tuples (0-255 each)

    Returns:
        Distance (0.0 - ~441.67 for max distance)

    Example:
        dist = rgb_distance((255, 0, 0), (255, 128, 0))
        # Returns distance between red and orange
    """
    r1, g1, b1 = rgb1
    r2, g2, b2 = rgb2
    return ((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2) ** 0.5


def find_closest_preset_name(rgb: Tuple[int, int, int], color_manager) -> str:
    """
    Find closest preset by RGB distance

    Args:
        rgb: Target RGB tuple
        color_manager: ColorManager instance

    Returns:
        Preset name (e.g., "red", "warm_white")

    Example:
        from managers.color_manager import ColorManager
        cm = ColorManager()
        closest = find_closest_preset_name((255, 100, 0), cm)
        # Returns "orange" or closest match
    """
    preset_colors = color_manager.preset_colors
    preset_order = color_manager.preset_order

    min_distance = float('inf')
    closest_preset = preset_order[0]  # Default to first

    for preset_name in preset_order:
        preset_rgb = preset_colors[preset_name]
        distance = rgb_distance(rgb, preset_rgb)
        if distance < min_distance:
            min_distance = distance
            closest_preset = preset_name

    return closest_preset


def hue_to_name(hue: int) -> str:
    """
    Convert hue to approximate color name (for logging)

    Args:
        hue: Hue value (0-360)

    Returns:
        Color name string

    Example:
        hue_to_name(0)    # "red"
        hue_to_name(120)  # "green"
        hue_to_name(240)  # "blue"
    """
    # Simple mapping
    if hue < 15 or hue >= 345:
        return "red"
    elif hue < 45:
        return "orange"
    elif hue < 75:
        return "yellow"
    elif hue < 105:
        return "lime"
    elif hue < 135:
        return "green"
    elif hue < 165:
        return "cyan"
    elif hue < 195:
        return "sky blue"
    elif hue < 225:
        return "blue"
    elif hue < 255:
        return "indigo"
    elif hue < 285:
        return "violet"
    elif hue < 315:
        return "magenta"
    else:
        return "pink"
