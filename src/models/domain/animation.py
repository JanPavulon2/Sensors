"""
Animation domain models
=======================

Defines immutable config, mutable state, and combined runtime model
for all animations in the system.

This version fully uses AnimationID and ParamID enums until the
lowest runtime layer (AnimationEngine).
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from models.enums import ParamID, AnimationID, LogCategory
from models.domain.parameter import ParameterCombined
from utils.logger import  get_category_logger

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

    # ----------------------------------------------------------------------
    # PARAMETER ACCESS
    # ----------------------------------------------------------------------

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


    # ----------------------------------------------------------------------
    # PARAMETER PACKING FOR ENGINE
    # ----------------------------------------------------------------------

    def build_params_for_engine(self, current_zone: Optional['ZoneCombined'] = None) -> Dict[ParamID, Any]:
        """
        Build a dictionary of parameters for AnimationEngine.

        This method remains fully enum-typed — keys are still ParamID.
        Conversion to string (.name) happens inside the engine itself.

        Args:
            current_zone: Optional current ZoneCombined for color/hue references
        Returns:
            Dict[ParamID, Any]
        """
        
        from models.enums import AnimationID
        
        # Base parameters (all animations have speed)
        params: Dict[ParamID, Any] = {}
        
        # Every animation has speed
        if ParamID.ANIM_SPEED in self.parameters:
            params[ParamID.ANIM_SPEED] = self.get_param_value(ParamID.ANIM_SPEED)


        # Specific animation parameter handling
        if self.config.id == AnimationID.BREATHE:
            if ParamID.ANIM_INTENSITY in self.parameters:
                params[ParamID.ANIM_INTENSITY] = self.get_param_value(ParamID.ANIM_INTENSITY)

        elif self.config.id == AnimationID.COLOR_FADE:
            if current_zone:
                params[ParamID.ANIM_PRIMARY_COLOR_HUE] = current_zone.state.color.to_hue()

        elif self.config.id == AnimationID.SNAKE:
            if ParamID.ANIM_PRIMARY_COLOR_HUE in self.parameters:
                params[ParamID.ANIM_PRIMARY_COLOR_HUE] = self.get_param_value(ParamID.ANIM_PRIMARY_COLOR_HUE)
            elif current_zone:
                params[ParamID.ANIM_PRIMARY_COLOR_HUE] = current_zone.state.color.to_hue()

            if ParamID.ANIM_LENGTH in self.parameters:
                params[ParamID.ANIM_LENGTH] = self.get_param_value(ParamID.ANIM_LENGTH)

        elif self.config.id == AnimationID.COLOR_SNAKE:
            if ParamID.ANIM_PRIMARY_COLOR_HUE in self.parameters:
                params[ParamID.ANIM_PRIMARY_COLOR_HUE] = self.get_param_value(ParamID.ANIM_PRIMARY_COLOR_HUE)
            if ParamID.ANIM_LENGTH in self.parameters:
                params[ParamID.ANIM_LENGTH] = self.get_param_value(ParamID.ANIM_LENGTH)
            if ParamID.ANIM_HUE_OFFSET in self.parameters:
                params[ParamID.ANIM_HUE_OFFSET] = self.get_param_value(ParamID.ANIM_HUE_OFFSET)

        elif self.config.id == AnimationID.MATRIX:
            for pid in (ParamID.ANIM_PRIMARY_COLOR_HUE, ParamID.ANIM_LENGTH, ParamID.ANIM_INTENSITY):
                if pid in self.parameters:
                    params[pid] = self.get_param_value(pid)

        return params

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
