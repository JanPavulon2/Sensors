"""Hardware input events (encoder, buttons, keyboard)"""

from dataclasses import dataclass
from typing import List, Optional

from models.events.base import Event
from models.events.types import EventType
from models.events.sources import EventSource, EncoderSource, KeyboardSource
from models.enums import ButtonID

@dataclass(init=False)
class EncoderRotateEvent(Event[EncoderSource]):
    """Encoder rotation event"""
    source: EncoderSource
    delta: int

    def __init__(self, source: EncoderSource, delta: int):
        """
        Args:
            source: EncoderSource.SELECTOR or EncoderSource.MODULATOR
            delta: -1 (CCW) or +1 (CW)
        """
        super().__init__(
            type=EventType.ENCODER_ROTATE,
            source=source,
        )
        self.delta = delta


@dataclass(init=False)
class EncoderClickEvent(Event):
    """Encoder button click event"""
    source: EncoderSource

    def __init__(self, source: EncoderSource):
        """
        Args:
            source: EncoderSource.SELECTOR or EncoderSource.MODULATOR
        """
        super().__init__(
            type=EventType.ENCODER_CLICK,
            source=EventSource.HARDWARE,
        )
        self.source = source


@dataclass(init=False)
class ButtonPressEvent(Event):
    """Button press event"""
    source: ButtonID

    def __init__(self, button_id: ButtonID):
        """
        Args:
            button_id: ButtonID.BTN1, ButtonID.BTN2, ButtonID.BTN3, or ButtonID.BTN4
        """
        super().__init__(
            type=EventType.BUTTON_PRESS,
            source=EventSource.HARDWARE,
        )
        self.source = button_id


@dataclass(init=False)
class KeyboardKeyPressEvent(Event):
    """Keyboard key press event"""
    key: str
    modifiers: List[str]
    source: KeyboardSource

    def __init__(self, key: str, modifiers: Optional[List[str]] = None, source: KeyboardSource = KeyboardSource.STDIN):
        """
        Args:
            key: The key that was pressed (e.g., 'a', 'Enter', etc.)
            modifiers: List of modifier keys (e.g., ['ctrl', 'shift'])
            source: KeyboardSource (where input came from)
        """
        super().__init__(
            type=EventType.KEYBOARD_KEYPRESS,
            source=EventSource.HARDWARE,
        )
        self.key = key
        self.modifiers = modifiers or []
        self.source = source
