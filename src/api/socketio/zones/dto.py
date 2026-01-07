from dataclasses import dataclass
from typing import Any, Dict, Optional

from models.domain.zone import ZoneCombined


@dataclass
class AnimationStateSnapshotDTO:
    id: str
    parameters: Dict[str, Any]

    @classmethod
    def from_state(cls, animation_state):
        return cls(
            id=animation_state.id.name,
            parameters={
                param_id.name.lower(): value
                for param_id, value in animation_state.parameters.items()
            }
        )


@dataclass
class ZoneSnapshotDTO:
    id: str
    display_name: str
    pixel_count: int

    # state
    is_on: bool
    brightness: int
    color: dict
    render_mode: str

    animation: Optional[AnimationStateSnapshotDTO]
    
    @classmethod
    def from_zone(cls, zone: ZoneCombined) -> "ZoneSnapshotDTO":
        color_dict = zone.state.color.to_dict()
        # Always include RGB values for frontend, regardless of storage mode
        r, g, b = zone.state.color.to_rgb()
        color_dict["rgb"] = [r, g, b]

        return cls(
            id=zone.config.id.name,
            display_name=zone.config.display_name,
            pixel_count=zone.config.pixel_count,

            is_on=zone.state.is_on,
            brightness=zone.state.brightness,
            color=color_dict,
            render_mode=zone.state.mode.name,

            animation=(
                AnimationStateSnapshotDTO.from_state(zone.state.animation)
                if zone.state.animation
                else None
            )
        )
        