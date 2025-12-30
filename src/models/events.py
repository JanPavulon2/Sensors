"""
Event system for LED Control Station

Event-driven architecture replacing callback pattern.
All hardware inputs (encoders, buttons) are published as events.
"""

from dataclasses import dataclass
import time
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Generic, TypeVar
from models.animation_params.animation_param_id import AnimationParamID
from models.color import Color
from models.domain.animation import AnimationState
from models.enums import EncoderSource, ButtonID, KeyboardSource, EventSource, ZoneID, ZoneRenderMode, AnimationID


class EventType(Enum):
    """Event types in the system"""
    # Hardware events (RPI)
    ENCODER_ROTATE = auto()
    ENCODER_CLICK = auto()
    BUTTON_PRESS = auto()

    # Keyboard eventss
    KEYBOARD_KEYPRESS = auto()

    # Future: Web API, MQTT, system events
    WEB_COMMAND = auto()
    MQTT_COMMAND = auto()
    SYSTEM_EVENT = auto()

    # Zone and animation events
    ZONE_STATE_CHANGED = auto()
    ANIMATION_STARTED = auto()
    ANIMATION_STOPPED = auto()
    ANIMATION_PARAMETER_CHANGED = auto()

TSource = TypeVar("TSource", bound=Enum)

@dataclass
class Event(Generic[TSource]):
    """
    Base event class

    All events inherit from this and must specify:
    - type: EventType (what kind of event)
    - source: Enum (where it came from: EncoderSource.SELECTOR, ButtonID.BTN1, etc.)
    - data: dict (event-specific payload)
    - timestamp: float (when it happened)
    """
    type: EventType
    source: TSource | None  # EncoderSource or ButtonID
    data: Dict[str, Any]
    timestamp: float

@dataclass
class EncoderRotateEvent(Event[EncoderSource]):
    """Encoder rotation event"""

    def __init__(self, source: EncoderSource, delta: int):
        """
        Args:
            source: EncoderSource.SELECTOR or EncoderSource.MODULATOR
            delta: -1 (CCW) or +1 (CW)
        """
        super().__init__(
            type=EventType.ENCODER_ROTATE,
            source=source,
            data={"delta": delta},
            timestamp=time.time()
        )

    @property
    def delta(self) -> int:
        """Rotation direction (-1 or +1)"""
        return self.data["delta"]

@dataclass
class EncoderClickEvent(Event[EncoderSource]):
    """Encoder button click event"""

    def __init__(self, source: EncoderSource):
        """
        Args:
            source: EncoderSource.SELECTOR or EncoderSource.MODULATOR
        """
        super().__init__(
            type=EventType.ENCODER_CLICK,
            source=source,
            data={},
            timestamp=time.time()
        )

@dataclass
class ButtonPressEvent(Event[ButtonID]):
    """Button press event"""

    def __init__(self, source: ButtonID):
        """
        Args:
            button_id: ButtonID.BTN1, ButtonID.BTN2, ButtonID.BTN3, or ButtonID.BTN4
        """
        super().__init__(
            type=EventType.BUTTON_PRESS,
            source=source,
            data={},
            timestamp=time.time()
        )

@dataclass
class KeyboardKeyPressEvent(Event[KeyboardSource]):
    """Keyboard key press event"""

    def __init__(self, key: str, modifiers: Optional[List[str]] = None, source: KeyboardSource = KeyboardSource.STDIN):
        """
        Args:
            key: The key that was pressed (e.g., 'a', 'Enter', etc.)
        """
        super().__init__(
            type=EventType.KEYBOARD_KEYPRESS,
            source=source,
            data={"key": key, "modifiers": modifiers or []},
            timestamp=time.time()
        )

    @property
    def key(self) -> str:
        """The key that was pressed"""
        return self.data["key"]
    
    @property
    def modifiers(self) -> List[str]:
        return self.data["modifiers"]
      
@dataclass
class ZoneStateChangedEvent(Event[EventSource]):
    """
    Zone state changed event - fired when zone color, brightness, or is_on changes.

    Unlike hardware events, this comes from the ZoneService (source=EventSource.ZONE_SERVICE)
    and carries structured zone state data in addition to the generic data dict.
    """
    zone_id: ZoneID
    color: Optional[Color] = None
    brightness: Optional[int] = None
    is_on: Optional[bool] = None
    render_mode: Optional[ZoneRenderMode] = None
        
    def __init__(
        self,
        *,
        zone_id: ZoneID,
        color: Optional[Color] = None,
        brightness: Optional[int] = None,
        is_on: Optional[bool] = None,
        render_mode: Optional[ZoneRenderMode] = None,
        animation: Optional[AnimationState] = None
    ):
        # Initialize parent Event with structured data
        super().__init__(
            type=EventType.ZONE_STATE_CHANGED,
            source=EventSource.ZONE_SERVICE,
            data={
                "zone_id": zone_id.name
            },
            timestamp=time.time(),
        )
        
        # Store structured data for type-safe access
        self.zone_id = zone_id
        self.color = color
        self.brightness = brightness
        self.is_on = is_on
        self.render_mode = render_mode
        self.animation = animation


@dataclass
class AnimationStartedEvent(Event[EventSource]):
    """Animation started event - fired when an animation begins on a zone"""
    zone_id: ZoneID
    animation_id: AnimationID
    parameters: Optional[Dict[AnimationParamID, Any]] = None

    def __init__(
        self,
        zone_id: ZoneID,
        animation_id: AnimationID,
        parameters: Optional[Dict[AnimationParamID, Any]] = None,
    ):
        # Convert enum keys to strings for serialization in data dict
        serialized_params = {}
        if parameters:
            serialized_params = {k.name if isinstance(k, AnimationParamID) else k: v for k, v in parameters.items()}

        super().__init__(
            type=EventType.ANIMATION_STARTED,
            source=EventSource.ANIMATION_ENGINE,
            data={
                "zone_id": zone_id.name,
                "animation_id": animation_id.name,
                "parameters": serialized_params,
            },
            timestamp=time.time(),
        )
        self.zone_id = zone_id
        self.animation_id = animation_id
        self.parameters = parameters or {}


@dataclass
class AnimationStoppedEvent(Event[EventSource]):
    """Animation stopped event - fired when an animation ends on a zone"""
    zone_id: ZoneID

    def __init__(self, zone_id: ZoneID):
        super().__init__(
            type=EventType.ANIMATION_STOPPED,
            source=EventSource.ANIMATION_ENGINE,
            data={"zone_id": zone_id.name},
            timestamp=time.time(),
        )
        self.zone_id = zone_id


@dataclass
class AnimationParameterChangedEvent(Event[EventSource]):
    """Animation parameter changed event - fired when an animation parameter is updated"""
    zone_id: ZoneID
    param_id: AnimationParamID
    value: Any

    def __init__(self, zone_id: ZoneID, param_id: AnimationParamID, value: Any):
        super().__init__(
            type=EventType.ANIMATION_PARAMETER_CHANGED,
            source=EventSource.ANIMATION_ENGINE,
            data={
                "zone_id": zone_id.name,
                "param_id": param_id.name,
                "value": value,
            },
            timestamp=time.time(),
        )
        
        self.zone_id = zone_id
        self.param_id = param_id
        self.value = value