"""Animation service - Provides animation definitions and parameter building"""

from typing import List, Dict, Optional, TYPE_CHECKING, Any
from models.enums import AnimationID, ParamID
from models.domain import AnimationConfig
from services.data_assembler import DataAssembler
from utils.logger import get_logger, LogCategory

if TYPE_CHECKING:
    from models.domain import ZoneCombined

log = get_logger().for_category(LogCategory.ANIMATION)


class AnimationService:
    """Provides access to animation definitions and builds engine parameters"""

    def __init__(self, assembler: DataAssembler):
        self.assembler = assembler
        self.animations: List[AnimationConfig] = assembler.build_animations()
        self._by_id = {anim.id: anim for anim in self.animations}

        log.info(f"AnimationService: {len(self.animations)} animations available")

    def get_animation(self, animation_id: AnimationID) -> AnimationConfig:
        """Get animation definition by ID"""
        return self._by_id[animation_id]

    def get_all(self) -> List[AnimationConfig]:
        """Get all animation definitions"""
        return self.animations

    def build_params_for_zone(
        self,
        anim_id: AnimationID,
        zone_animation_params: Dict[ParamID, Any],
        zone: 'ZoneCombined'
    ) -> Dict[ParamID, Any]:
        """
        Build parameter dict for animation engine.

        Takes zone's stored animation parameters and supplements with defaults
        (like zone color for animations that need it).

        Args:
            anim_id: Which animation
            zone_animation_params: Parameters from zone.state.animation.parameter_values
            zone: ZoneCombined for accessing color/brightness

        Returns:
            Dict[ParamID, value] ready for engine
        """
        anim_config = self.get_animation(anim_id)
        params: Dict[ParamID, Any] = {}

        # Use zone's stored params
        for param_id in anim_config.parameters:
            if param_id in zone_animation_params:
                params[param_id] = zone_animation_params[param_id]

        # Add zone color if animation supports it (all animations use hue)
        if ParamID.ANIM_PRIMARY_COLOR_HUE in anim_config.parameters:
            params[ParamID.ANIM_PRIMARY_COLOR_HUE] = zone.state.color.to_hue()

        return params

    
    def stop_all(self):
        """Compatibility no-op (V3 animations run via AnimationEngine)."""
        log.debug("AnimationService.stop_all(): no-op (V3 engine handles tasks)")