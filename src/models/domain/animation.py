"""
Animation domain models

Defines immutable animation configuration and mutable animation state.
"""

from dataclasses import dataclass, field
from typing import Any, Dict
from models.enums import ParamID, AnimationID


@dataclass(frozen=True)
class AnimationConfig:
    """Immutable animation configuration from YAML"""
    id: AnimationID
    display_name: str
    description: str
    parameters: list[ParamID]


@dataclass
class AnimationState:
    """Mutable animation state from JSON (stored per-zone)"""
    id: AnimationID
    parameter_values: Dict[ParamID, Any] = field(default_factory=dict)
