"""
Animation domain models

Defines immutable animation configuration and mutable animation state.
"""

from dataclasses import dataclass, field
from typing import Any, Dict
from models.animation_params.animation_param_id import AnimationParamID
from models.enums import AnimationID


@dataclass(frozen=True)
class AnimationConfig:
    """Immutable animation configuration from YAML"""
    id: AnimationID
    display_name: str
    description: str
    parameters: list[AnimationParamID]


@dataclass
class AnimationState:
    """Mutable animation state from JSON (stored per-zone)"""
    id: AnimationID
    parameters: Dict[AnimationParamID, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id.name,
            "parameters": {
                k.name: v
                for k, v in self.parameters.items()
            }
        }
