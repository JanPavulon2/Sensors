from __future__ import annotations

from enum import Enum
import time
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Generic, TypeVar

from models.events.types import EventType
from models.events.sources import EventSource


TSource = TypeVar("TSource", bound=Enum)

@dataclass(init=False)
class Event(Generic[TSource]):
    """
    Base event class.

    - type: EventType
    - source: EventSource
    - timestamp: auto
    """

    type: EventType
    source: EventSource | None
    timestamp: float = field(default_factory=time.time)

    def __init__(self, *, type: EventType, source: EventSource | None):
        self.type = type
        self.source = source
        self.timestamp = time.time()
        
    def to_data(self) -> Dict[str, Any]:
        """
        Structured payload for EventBus / serializers.
        Compatible replacement for old `data` dict.
        """
        data = {}
        for k, v in self.__dict__.items():
            if k in ("type", "source", "timestamp"):
                continue
            data[k] = v
        return data
    
    # def to_data(self) -> Dict[str, Any]:
    #     """
    #     Serialize event payload (without metadata).
    #     """
    #     data = asdict(self)
    #     data.pop("type", None)
    #     data.pop("source", None)
    #     data.pop("timestamp", None)
    #     return data