"""Animation service - Provides animation definitions and parameter building"""

from typing import List, Dict, Optional, TYPE_CHECKING, Any
from models.animation_params.animation_param_id import AnimationParamID
from models.enums import AnimationID
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
        zone_animation_params: Dict[AnimationParamID, Any],
        zone: 'ZoneCombined'
    ) -> Dict[AnimationParamID, Any]:
        """Return zone's stored animation parameters as-is"""
        # Runtime behavior driven by animation classes, not config
        params = zone_animation_params.copy()

        # Add zone color if the animation might use it
        # (animations decide via their PARAMS definitions)
        if AnimationParamID.COLOR not in params:
            params[AnimationParamID.COLOR] = zone.state.color.to_hue()

        return params