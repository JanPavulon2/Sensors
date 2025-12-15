"""
Event system for LED Control Station

Event-driven architecture replacing callback pattern.
All hardware inputs (encoders, buttons) are published as events.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Generic, TypeVar
import time
from models.color import Color
from models.enums import EncoderSource, ButtonID, KeyboardSource, EventSource, ZoneID, ZoneRenderMode


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
    
    ZONE_STATE_CHANGED = auto()

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
        zone_id: ZoneID,
        color: Optional[Color] = None,
        brightness: Optional[int] = None,
        is_on: Optional[bool] = None,
        render_mode: Optional[ZoneRenderMode] = None,
    ):
        # Initialize parent Event with structured data
        super().__init__(
            type=EventType.ZONE_STATE_CHANGED,
            source=EventSource.ZONE_SERVICE,
            data={
                "zone_id": zone_id.name,
                "color": str(color) if color else None,
                "brightness": brightness,
                "is_on": is_on,
                "render_mode": render_mode.name if render_mode else None,
            },
            timestamp=time.time(),
        )
        # Store structured data for type-safe access
        self.zone_id = zone_id
        self.color = color
        self.brightness = brightness
        self.is_on = is_on
        self.render_mode = render_mode