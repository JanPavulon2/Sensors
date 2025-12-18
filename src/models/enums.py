"""
Enums for LED Controller state machine
"""

from enum import Enum, auto


class ZoneRenderMode(Enum):
    """
    Per-zone operating modes (replaces global MainMode)

    Each zone independently operates in one of these modes:

    STATIC: Zone displays static color (zone editing mode)
    ANIMATION: Zone displays animation
    """
    STATIC = auto()
    ANIMATION = auto()


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

class KeyboardSource(Enum):
    EVDEV = auto(),
    STDIN = auto()

class EventSource(Enum):
    """Event source identifiers for application events"""
    ZONE_SERVICE = auto()  # Events from zone state changes
    APPLICATION = auto()   # Generic application events
    ANIMATION_ENGINE = auto()
    
class BuzzerID(Enum):
    """Buzzer identifiers"""
    ACTIVE = auto()   # 
    PASSIVE = auto()  # 

class EncoderID(Enum):
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
    CIRCLE = auto()
    LEFT = auto()
    TOP = auto()
    RIGHT = auto()
    BOTTOM = auto()
    LAMP = auto()
    GATE = auto()
    PIXEL = auto()        # 30-pixel custom LED strip on GPIO 19
    PIXEL2 = auto()        # 30-pixel custom LED strip on GPIO 19
    PREVIEW = auto()      # 8-pixel preview panel on GPIO 19
    BACK = auto()
    DESK = auto()


class LEDStripID(Enum):
    """LED Strip identifiers (by chip type and GPIO)"""
    MAIN_12V = auto()       # GPIO 18: WS2811 12V strip (FLOOR, LEFT, TOP, RIGHT, BOTTOM, LAMP)
    AUX_5V = auto()       # GPIO 19: WS2812 5V strip (PIXEL zone + PREVIEW zone)


class LEDStripType(Enum):
    """Typ fizycznego paska LED — używamy enumów, nie stringów."""
    WS2811_12V = "WS2811_12V"
    WS2812_5V = "WS2812_5V"
    WS2813 = "WS2813"
    APA102 = "APA102"
    SK6812 = "SK6812"

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

class ZoneEditTarget(Enum):
    COLOR_HUE = auto()
    COLOR_PRESET = auto()
    BRIGHTNESS = auto()

class LogLevel(Enum):
    """Log severity levels"""
    DEBUG = auto()
    INFO = auto()
    WARN = auto()
    ERROR = auto()


class GPIOPullMode(Enum):
    """GPIO pull-up/down resistor configuration"""
    PULL_UP = auto()     # Internal pull-up resistor (pin reads HIGH when open)
    PULL_DOWN = auto()   # Internal pull-down resistor (pin reads LOW when open)
    NO_PULL = auto()     # No pull resistor (floating)


class GPIOInitialState(Enum):
    """GPIO output pin initial state"""
    LOW = auto()         # Start LOW (0V)
    HIGH = auto()        # Start HIGH (3.3V)


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
    RENDER_ENGINE = auto()
    
    INDICATOR = auto()
    ANIM_CONTROLLER = auto()
    STATIC_CONTROLLER = auto()
    LIGHTING_CONTROLLER = auto()
    
    API = auto()
    WEBSOCKET = auto()
    
    SHUTDOWN = auto()
    LIFECYCLE = auto()
    TASK = auto()

    GENERAL = auto()    # Default general category
    
class FramePriority(Enum):
    """
    Frame priority levels (higher value = higher priority)

    Used by FrameManager to select which frame to render when multiple
    sources provide frames simultaneously.
    """
    IDLE = 0           # No active source (black screen fallback)
    MANUAL = 10        # Manual static color settings
    PULSE = 30         # Edit mode pulsing indicator
    ANIMATION = 20     # Running animations
    TRANSITION = 40    # Crossfades, mode switches (highest)
    DEBUG = 50         # Debug overlays (for future use)


class FrameSource(Enum):
    """
    Frame source identifiers for debugging and priority resolution

    Helps identify which subsystem generated a frame.
    """
    IDLE = auto()           # No source (idle state)
    STATIC = auto()         # Static color controller
    MANUAL = auto()
    PULSE = auto()          # Pulsing animation (edit mode)
    ANIMATION = auto()      # AnimationEngine
    TRANSITION = auto()     # TransitionService
    PREVIEW = auto()        # Preview panel controller
    DEBUG = auto()          # Debug overlay