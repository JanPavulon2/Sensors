"""Animation domain models"""

from dataclasses import dataclass
from typing import Any, Dict
from models.enums import ParamID, AnimationID, LogCategory
from models.domain.parameter import ParameterCombined
from utils.logger import get_logger, get_category_logger

log = get_category_logger(LogCategory.ANIMATION)


@dataclass(frozen=True)
class AnimationConfig:
    """Immutable animation configuration from YAML"""
    id: AnimationID
    tag: str
    display_name: str
    description: str
    parameters: list[ParamID]


@dataclass
class AnimationState:
    """Mutable animation state from JSON"""
    id: AnimationID
    enabled: bool
    parameter_values: Dict[ParamID, Any]


@dataclass
class AnimationCombined:
    """Animation with config, state, and parameters"""
    config: AnimationConfig
    state: AnimationState
    parameters: Dict[ParamID, ParameterCombined]

    def get_param_value(self, param_id: ParamID) -> Any:
        """Get current parameter value"""
        return self.parameters[param_id].state.value

    def set_param_value(self, param_id: ParamID, value: Any) -> None:
        """Set parameter value with validation"""
        param = self.parameters[param_id]
        if not param.config.validate(value):
            log("Invalid value {value} for {param_id.name}, clamping")
            value = param.config.clamp(value)
        param.state.value = value

    def adjust_param(self, param_id: ParamID, delta: int) -> None:
        """Adjust parameter by delta steps"""
        self.parameters[param_id].adjust(delta)

    def start(self) -> bool:
        """Enable animation, returns True if state changed"""
        if not self.state.enabled:
            self.state.enabled = True
            log.info(f"Started animation: {self.config.display_name}")
            return True
        return False

    def stop(self) -> bool:
        """Disable animation, returns True if state changed"""
        if self.state.enabled:
            self.state.enabled = False
            log.info(f"Stopped animation: {self.config.display_name}")
            return True
        return False
