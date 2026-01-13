from enum import Enum, auto


class EventType(Enum):
    # Hardware
    ENCODER_ROTATE = auto()
    ENCODER_CLICK = auto()
    BUTTON_PRESS = auto()
    KEYBOARD_KEYPRESS = auto()

    # Zone / static
    ZONE_STATIC_STATE_CHANGED = auto()
    ZONE_ANIMATION_PARAM_CHANGED = auto()
    ZONE_RENDER_MODE_CHANGED = auto()

    # Animation
    ZONE_ANIMATION_CHANGED = auto()
    ANIMATION_STARTED = auto()
    ANIMATION_STOPPED = auto()
    ANIMATION_PARAMETER_CHANGED = auto()

    # Snapshot (UI)
    ZONE_SNAPSHOT_UPDATED = auto()

    # Future: Web API, MQTT, system events
    WEB_COMMAND = auto()
    MQTT_COMMAND = auto()
    SYSTEM_EVENT = auto()

