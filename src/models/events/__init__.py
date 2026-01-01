"""
Event system for LED Control Station

Event-driven architecture with specific backend events and generic frontend snapshots.
"""

# Event type, base class, and sources
from models.events.types import EventType
from models.events.base import Event
from models.events.sources import EventSource, EncoderSource, KeyboardSource

# Hardware events
from models.events.hardware import (
    EncoderRotateEvent,
    EncoderClickEvent,
    ButtonPressEvent,
    KeyboardKeyPressEvent,
)

# Zone state events (specific, backend)
from models.events.zone_static_events import ZoneStaticStateChangedEvent
from models.events.zone_runtime_events import (
    ZoneRenderModeChangedEvent,
    ZoneAnimationChangedEvent,
    AnimationStartedEvent,
    AnimationStoppedEvent,
    AnimationParameterChangedEvent,
)

# Snapshot events (frontend/UI)
# from models.events.zone_snapshot_events import ZoneSnapshotUpdatedEvent

__all__ = [
    # Type, base, and sources
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
    # Snapshot
    # "ZoneSnapshotUpdatedEvent",
]
