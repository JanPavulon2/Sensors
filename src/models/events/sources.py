from enum import Enum, auto

class EncoderSource(Enum):
    """Encoder identifiers for event sources"""
    SELECTOR = auto()   # Multi-purpose selector encoder (zones, animations, etc.)
    MODULATOR = auto()  # Parameter value modulator encoder

class KeyboardSource(Enum):
    EVDEV = auto(),
    STDIN = auto()

class EventSource(Enum):
    """Event source identifiers for application events"""
    HARDWARE = auto()           # Hardware inputs (encoder, buttons, keyboard)
    ZONE_SERVICE = auto()       # Events from zone state changes
    APPLICATION = auto()        # Generic application events
    ANIMATION_ENGINE = auto()   # Animation engine events
    SNAPSHOT_PUBLISHER = auto() # UI/frontend snapshot events
    