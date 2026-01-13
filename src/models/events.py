"""
Event system - re-export from models.events folder for backward compatibility.

All events are defined in models/events/ folder:
- models/events/types.py - EventType enum
- models/events/base.py - Event base class
- models/events/sources.py - EventSource enums
- models/events/hardware.py - Hardware events (encoder, button, keyboard)
- models/events/zone_static_events.py - Zone static state events
- models/events/zone_runtime_events.py - Zone animation/render mode events

This file provides backward compatibility for imports from models.events
"""

# Re-export everything from models.events folder
from models.events import (
    # Type and base
    EventType,
    Event,
    EventSource,
    EncoderSource,
    KeyboardSource,
    # Hardware events
    EncoderRotateEvent,
    EncoderClickEvent,
    ButtonPressEvent,
    KeyboardKeyPressEvent,
    # Zone state events
    ZoneStaticStateChangedEvent,
    ZoneRenderModeChangedEvent,
    ZoneAnimationChangedEvent,
    AnimationStartedEvent,
    AnimationStoppedEvent,
    AnimationParameterChangedEvent,
)

__all__ = [
    # Type and base
    "EventType",
    "Event",
    "EventSource",
    "EncoderSource",
    "KeyboardSource",
    # Hardware
    "EncoderRotateEvent",
    "EncoderClickEvent",
    "ButtonPressEvent",
    "KeyboardKeyPressEvent",
    # Zone state
    "ZoneStaticStateChangedEvent",
    "ZoneRenderModeChangedEvent",
    "ZoneAnimationChangedEvent",
    "AnimationStartedEvent",
    "AnimationStoppedEvent",
    "AnimationParameterChangedEvent",
]
