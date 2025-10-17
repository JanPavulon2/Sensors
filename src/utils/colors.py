"""
Color utility functions
"""

# Predefined colors - easy to access standard colors
# Format: name -> (r, g, b) tuple (0-255)
PRESET_COLORS = {
    # Basic colors
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),

    # Whites
    "white": (255, 255, 255),
    "warm_white": (255, 200, 150),  # Cozy warm white
    "cool_white": (200, 220, 255),  # Cool daylight white

    # Oranges
    "orange": (255, 128, 0),
    "amber": (255, 191, 0),

    # Purples
    "purple": (128, 0, 255),
    "violet": (180, 0, 255),
    "indigo": (75, 0, 130),

    # Pinks
    "pink": (255, 128, 192),
    "hot_pink": (255, 0, 128),

    # Natural tones
    "mint": (170, 255, 195),
    "lime": (128, 255, 0),
    "sky_blue": (135, 206, 235),
    "ocean": (0, 128, 255),
    "lavender": (200, 150, 255),

    # Off
    "off": (0, 0, 0),
}

# List of preset color names in a nice order for cycling
PRESET_ORDER = [
    "red",
    "orange",
    "amber",
    "yellow",
    "lime",
    "green",
    "mint",
    "cyan",
    "sky_blue",
    "ocean",
    "blue",
    "indigo",
    "violet",
    "purple",
    "magenta",
    "hot_pink",
    "pink",
    "warm_white",
    "white",
    "cool_white",
]


def get_preset_color(name):
    """
    Get RGB values for a preset color

    Args:
        name: Name of preset color (e.g., "red", "warm_white")

    Returns:
        (r, g, b) tuple or None if color doesn't exist

    Example:
        r, g, b = get_preset_color("warm_white")
        if rgb:
            strip.set_color(r, g, b)
    """
    return PRESET_COLORS.get(name)


def get_preset_by_index(index):
    """
    Get preset color by index in PRESET_ORDER

    Args:
        index: Index in preset list (wraps around)

    Returns:
        (name, (r, g, b)) tuple

    Example:
        name, (r, g, b) = get_preset_by_index(0)  # Returns ("red", (255, 0, 0))
    """
    index = index % len(PRESET_ORDER)
    name = PRESET_ORDER[index]
    return name, PRESET_COLORS[name]


def hue_to_rgb(hue):
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


def rgb_to_hue(r, g, b):
    """
    Convert RGB (0-255) to hue (0-360)

    Converts RGB color to hue angle. Returns 0 for grayscale/white colors.

    NOTE: For white/warm_white/cool_white presets, this returns 0 (neutral)
    since they have low saturation. Use rgb_to_hsv() if you need saturation info.

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
