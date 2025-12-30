from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

from models.domain.zone import ZoneCombined


@dataclass
class AnimationSnapshotDTO:
    id: str
    parameters: Dict[str, Any]

    @classmethod
    def from_state(cls, animation_state):
        return cls(
            id=animation_state.id.name,
            parameters={
                param_id.name: value
                for param_id, value in animation_state.parameter_values.items()
            },
        )


@dataclass
class ZoneSnapshotDTO:
    id: str
    display_name: str
    pixel_count: int

    is_on: bool
    brightness: int
    color: dict
    render_mode: str

    animation: Optional[AnimationSnapshotDTO]

    @classmethod
    def from_zone(cls, zone: ZoneCombined) -> "ZoneSnapshotDTO":
        return cls(
            id=zone.config.id.name,
            display_name=zone.config.display_name,
            pixel_count=zone.config.pixel_count,

            is_on=zone.state.is_on,
            brightness=zone.state.brightness,
            color=zone.state.color.to_dict(),
            render_mode=zone.state.mode.name,

            animation=(
                AnimationSnapshotDTO.from_state(zone.state.animation)
                if zone.state.animation
                else None
            ),
        )

    def to_dict(self) -> dict:
        return asdict(self)