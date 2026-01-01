from dataclasses import dataclass
from typing import Any, Dict

from models.events.base import Event
from models.events.types import EventType
from models.events.sources import EventSource
from models.enums import (
    ZoneID,
    ZoneRenderMode,
    AnimationID,
)
from models.animation_params.animation_param_id import AnimationParamID


@dataclass(init=False)
class ZoneRenderModeChangedEvent(Event):
    zone_id: ZoneID
    old: ZoneRenderMode
    new: ZoneRenderMode

    def __init__(self, zone_id: ZoneID, old: ZoneRenderMode, new: ZoneRenderMode):
        super().__init__(
            type=EventType.ZONE_RENDER_MODE_CHANGED,
            source=EventSource.ZONE_SERVICE,
        )
        self.zone_id = zone_id
        self.old = old
        self.new = new


@dataclass(init=False)
class ZoneAnimationChangedEvent(Event):
    zone_id: ZoneID
    animation_id: AnimationID
    params: Dict[AnimationParamID, Any]

    def __init__(
        self,
        zone_id: ZoneID,
        animation_id: AnimationID,
        params: Dict[AnimationParamID, Any],
    ):
        super().__init__(
            type=EventType.ZONE_ANIMATION_CHANGED,
            source=EventSource.ZONE_SERVICE,
        )
        self.zone_id = zone_id
        self.animation_id = animation_id
        self.params = params


@dataclass(init=False)
class AnimationStartedEvent(Event):
    zone_id: ZoneID
    animation_id: AnimationID

    def __init__(self, zone_id: ZoneID, animation_id: AnimationID):
        super().__init__(
            type=EventType.ANIMATION_STARTED,
            source=EventSource.ANIMATION_ENGINE,
        )
        self.zone_id = zone_id
        self.animation_id = animation_id


@dataclass(init=False)
class AnimationStoppedEvent(Event):
    zone_id: ZoneID

    def __init__(self, zone_id: ZoneID):
        super().__init__(
            type=EventType.ANIMATION_STOPPED,
            source=EventSource.ANIMATION_ENGINE,
        )
        self.zone_id = zone_id


@dataclass(init=False)
class AnimationParameterChangedEvent(Event):
    zone_id: ZoneID
    param_id: AnimationParamID
    value: Any

    def __init__(self, zone_id: ZoneID, param_id: AnimationParamID, value: Any):
        super().__init__(
            type=EventType.ANIMATION_PARAMETER_CHANGED,
            source=EventSource.ANIMATION_ENGINE,
        )
        self.zone_id = zone_id
        self.param_id = param_id
        self.value = value
