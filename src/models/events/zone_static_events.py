from dataclasses import dataclass
from typing import Optional

from models.events.base import Event
from models.events.types import EventType
from models.enums import ZoneID
from models.events.sources import EventSource
from models.color import Color

@dataclass(init=False)
class ZoneStaticStateChangedEvent(Event):
    """
    Fired when STATIC-related zone state changes:
    - color
    - brightness
    - is_on
    """

    zone_id: ZoneID
    color: Optional[Color] = None
    brightness: Optional[int] = None
    is_on: Optional[bool] = None

    def __init__(
        self,
        *,
        zone_id: ZoneID,
        color: Optional[Color] = None,
        brightness: Optional[int] = None,
        is_on: Optional[bool] = None,
    ):
        super().__init__(
            type=EventType.ZONE_STATIC_STATE_CHANGED,
            source=EventSource.ZONE_SERVICE,
        )
        
        self.zone_id = zone_id
        self.color = color
        self.brightness = brightness
        self.is_on = is_on
