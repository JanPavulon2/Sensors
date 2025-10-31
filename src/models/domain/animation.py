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

    def build_params_for_engine(self, current_zone: 'ZoneCombined' = None) -> Dict[str, Any]:
        """
        Build animation parameters for AnimationEngine

        Maps domain ParamIDs to engine parameter names and adds animation-specific
        parameters based on animation type.

        Args:
            current_zone: Optional current zone for color/hue references

        Returns:
            Dict of parameters for AnimationEngine.start()

        Example:
            >>> anim = animation_service.get_current()
            >>> params = anim.build_params_for_engine(current_zone)
            >>> await engine.start(anim.config.tag, **params)
        """
        from models.domain.zone import ZoneCombined
        from models.enums import AnimationID

        # Base parameters (all animations have speed)
        params = {"speed": self.get_param_value(ParamID.ANIM_SPEED)}

        # Animation-specific parameter building
        if self.config.id == AnimationID.BREATHE:
            # Breathe uses per-zone cached colors, only pass intensity
            if ParamID.ANIM_INTENSITY in self.parameters:
                params["intensity"] = self.get_param_value(ParamID.ANIM_INTENSITY)

        elif self.config.id == AnimationID.COLOR_FADE:
            # Color fade needs starting hue from current zone
            if current_zone:
                params["start_hue"] = current_zone.state.color.to_hue()

        elif self.config.id == AnimationID.SNAKE:
            # Snake can use hue or fallback to zone RGB
            if ParamID.ANIM_PRIMARY_COLOR_HUE in self.parameters:
                params["hue"] = self.get_param_value(ParamID.ANIM_PRIMARY_COLOR_HUE)
            elif current_zone:
                # Fallback: use zone color with brightness
                params["color"] = current_zone.get_rgb()

            if ParamID.ANIM_LENGTH in self.parameters:
                params["length"] = self.get_param_value(ParamID.ANIM_LENGTH)

        elif self.config.id == AnimationID.COLOR_SNAKE:
            # Color snake uses hue with offset
            if current_zone:
                params["start_hue"] = current_zone.state.color.to_hue()

            if ParamID.ANIM_LENGTH in self.parameters:
                params["length"] = self.get_param_value(ParamID.ANIM_LENGTH)
            if ParamID.ANIM_HUE_OFFSET in self.parameters:
                params["hue_offset"] = self.get_param_value(ParamID.ANIM_HUE_OFFSET)
            if ParamID.ANIM_PRIMARY_COLOR_HUE in self.parameters:
                params["hue"] = self.get_param_value(ParamID.ANIM_PRIMARY_COLOR_HUE)

        elif self.config.id == AnimationID.MATRIX:
            # Matrix uses hue, length, intensity
            if ParamID.ANIM_PRIMARY_COLOR_HUE in self.parameters:
                params["hue"] = self.get_param_value(ParamID.ANIM_PRIMARY_COLOR_HUE)
            if ParamID.ANIM_LENGTH in self.parameters:
                params["length"] = self.get_param_value(ParamID.ANIM_LENGTH)
            if ParamID.ANIM_INTENSITY in self.parameters:
                params["intensity"] = self.get_param_value(ParamID.ANIM_INTENSITY)

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
