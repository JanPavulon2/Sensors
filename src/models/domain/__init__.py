"""Domain models - Config and state objects"""

from .animation import AnimationConfig, AnimationState
from .zone import ZoneConfig, ZoneState, ZoneCombined
from .application import ApplicationState
from .output_frame import OutputFrame

__all__ = [
    "AnimationConfig",
    "AnimationState",
    "ZoneConfig",
    "ZoneState",
    "ZoneCombined",
    "ApplicationState",
    
    "OutputFrame"
]
