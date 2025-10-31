"""
Event system for LED Control Station

Event-driven architecture replacing callback pattern.
All hardware inputs (encoders, buttons) are published as events.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict
import time
from models.enums import EncoderSource, ButtonID


class EventType(Enum):
    """Event types in the system"""
    # Hardware events
    ENCODER_ROTATE = auto()
    ENCODER_CLICK = auto()
    BUTTON_PRESS = auto()

    # Future: Web API, MQTT, system events
    WEB_COMMAND = auto()
    MQTT_COMMAND = auto()
    SYSTEM_EVENT = auto()


@dataclass
class Event:
    """
    Base event class

    All events inherit from this and must specify:
    - type: EventType (what kind of event)
    - source: Enum (where it came from: EncoderSource.SELECTOR, ButtonID.BTN1, etc.)
    - data: dict (event-specific payload)
    - timestamp: float (when it happened)
    """
    type: EventType
    source: Enum  # EncoderSource or ButtonID
    data: Dict[str, Any]
    timestamp: float


@dataclass
class EncoderRotateEvent(Event):
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
class EncoderClickEvent(Event):
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
class ButtonPressEvent(Event):
    """Button press event"""

    def __init__(self, button_id: ButtonID):
        """
        Args:
            button_id: ButtonID.BTN1, ButtonID.BTN2, ButtonID.BTN3, or ButtonID.BTN4
        """
        super().__init__(
            type=EventType.BUTTON_PRESS,
            source=button_id,
            data={},
            timestamp=time.time()
        )
