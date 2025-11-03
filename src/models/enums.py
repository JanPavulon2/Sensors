"""
Enums for LED Controller state machine
"""

from enum import Enum, auto


class MainMode(Enum):
    """
    Two main operating modes (toggle with BTN4)

    STATIC: Zone editing mode
      - Encoder 1 rotate: Change zone
      - Encoder 2 rotate: Adjust parameter value
      - Encoder 2 click: Cycle parameter (COLOR → BRIGHTNESS)

    ANIMATION: Animation control mode
      - Encoder 1 rotate: Select animation
      - Encoder 1 click: Start/Stop animation
      - Encoder 2 rotate: Adjust parameter value
      - Encoder 2 click: Cycle parameter (SPEED → INTENSITY → ...)
    """
    STATIC = auto()      # Zone editing (default)
    ANIMATION = auto()   # Animation control


class PreviewMode(Enum):
    """Preview panel display modes"""
    COLOR_DISPLAY = auto()    # Show color on all 8 LEDs
    BAR_INDICATOR = auto()    # LED bar indicator (N of 8 LEDs lit)
    ANIMATION_PREVIEW = auto() # Mini animation preview

class ColorMode(Enum):
    """Color representation modes"""
    HUE = auto()       # Hue-based (0-360°, full saturation)
    PRESET = auto()    # Named preset from colors.yaml
    RGB = auto()       # Direct RGB (for future custom colors)


class EncoderSource(Enum):
    """Encoder identifiers for event sources"""
    SELECTOR = auto()   # Multi-purpose selector encoder (zones, animations, etc.)
    MODULATOR = auto()  # Parameter value modulator encoder


class ButtonID(Enum):
    """Button identifiers"""
    BTN1 = auto()  # Toggle edit mode
    BTN2 = auto()  # Quick lamp white mode
    BTN3 = auto()  # Power toggle
    BTN4 = auto()  # Toggle STATIC/ANIMATION mode


class ZoneID(Enum):
    """Zone identifiers"""
    FLOOR = auto()
    LEFT = auto()
    TOP = auto()
    RIGHT = auto()
    BOTTOM = auto()
    LAMP = auto()
    BACK = auto()
    DESK = auto()

class AnimationID(Enum):
    """Animation identifiers"""
    BREATHE = auto()
    COLOR_FADE = auto()
    SNAKE = auto()
    COLOR_SNAKE = auto()
    COLOR_CYCLE = auto()
    MATRIX = auto()

class ParameterType(Enum):
    """Parameter value types with validation rules"""
    COLOR = auto()
    PERCENTAGE = auto()
    RANGE_0_255 = auto()
    RANGE_CUSTOM = auto()
    BOOLEAN = auto()

class ParamID(Enum):
    """
    Parameter identifiers (unique across system)

    Naming convention: SCOPE_NAME
    - ZONE_* : Zone parameters (STATIC mode)
    - ANIM_* : Animation parameters (ANIMATION mode)
    - Generic : Reusable parameters (LENGTH, HUE_OFFSET, etc.)
    """

    # === ZONE PARAMETERS (STATIC mode) ===
    ZONE_COLOR_HUE = auto()    # Zone color adjustment via HUE (0-360°)
    ZONE_COLOR_PRESET = auto() # Zone color selection via named presets
    ZONE_BRIGHTNESS = auto()   # Zone brightness (0-100%)
    ZONE_REVERSED = auto()     # Reverse pixel order (bool) - for future

    # === ANIMATION PARAMETERS (ANIMATION mode) ===
    # Base parameters (shared by all animations)
    ANIM_SPEED = auto()                 # Animation speed (1-100%)
    ANIM_PRIMARY_COLOR_HUE = auto()     # Primary animation color hue (0-360°)

    # Additional parameters (optional, used by specific animations)
    ANIM_SECONDARY_COLOR_HUE = auto()   # Secondary animation color hue (0-360°)
    ANIM_TERTIARY_COLOR_HUE = auto()    # Tertiary animation color hue (0-360°)
    ANIM_INTENSITY = auto()             # Animation intensity (1-100%, for breathe/pulse)
    ANIM_LENGTH = auto()                # Animation length in pixels (e.g., snake length)
    ANIM_HUE_OFFSET = auto()            # Hue offset in degrees (e.g., rainbow spacing)



class LogLevel(Enum):
    """Log severity levels"""
    DEBUG = auto()
    INFO = auto()
    WARN = auto()
    ERROR = auto()


class LogCategory(Enum):
    """Log categories for grouping related events"""
    CONFIG = auto()      # Configuration loading, validation
    HARDWARE = auto()    # GPIO, encoders, buttons, LEDs
    STATE = auto()       # State changes, mode switches
    COLOR = auto()       # Color adjustments, mode changes
    ANIMATION = auto()   # Animation start/stop/params
    ZONE = auto()        # Zone selection, zone operations
    SYSTEM = auto()      # Startup, shutdown, errors
    TRANSITION = auto()  # LED state transitions
    EVENT = auto()       # Event bus events and handling