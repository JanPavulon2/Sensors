"""
Animation Manager - Provides access to animation metadata

Simplification: Just parses animation definitions from YAML.
No base/additional parameter distinction - all animations have speed, color, plus specific params.
"""

from typing import Dict, List, Optional

from models.enums import ParamID, AnimationID
from models.domain.animation import AnimationConfig
from utils.serialization import Serializer
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.ANIMATION)


class AnimationManager:
    """
    Simple animation metadata manager

    Responsibilities:
    - Parse animation definitions from config
    - Provide access to animation metadata
    """

    def __init__(self, data: dict):
        """
        Initialize with parsed animation config

        Args:
            data: Dict with 'animations' key (map format)
                  {
                      'BREATHE': {
                          'name': 'Breathe',
                          'class': 'BreatheAnimation',
                          'description': '...',
                          'parameters': ['ANIM_INTENSITY']
                      },
                      ...
                  }
        """
        self.animations: Dict[AnimationID, AnimationConfig] = {}
        self._process_data(data)

    def _process_data(self, data: dict):
        """
        Process animation configuration data (map format)

        Args:
            data: Config dict with 'animations' section (map format)
        """
        animations_map = data.get('animations', {})

        # Map format: {BREATHE: {...}, SNAKE: {...}}
        for anim_id_str, anim_data in animations_map.items():
            # Skip disabled animations
            if not anim_data.get('enabled', True):
                continue

            try:
                animation_id = Serializer.str_to_enum(anim_id_str, AnimationID)

                # Parse parameters
                param_names = anim_data.get('parameters', [])
                params = []
                for param_name in param_names:
                    try:
                        params.append(Serializer.str_to_enum(param_name, ParamID))
                    except ValueError:
                        log.warn(f"Unknown parameter '{param_name}' in animation {anim_id_str}")

                # Create AnimationConfig
                self.animations[animation_id] = AnimationConfig(
                    id=animation_id,
                    display_name=anim_data.get('name', anim_id_str),
                    description=anim_data.get('description', ''),
                    parameters=params
                )

                log.debug(f"Loaded animation: {animation_id.name}")

            except ValueError:
                log.warn(f"Invalid animation ID in config: {anim_id_str}")

    def get_animation(self, anim_id: AnimationID) -> Optional[AnimationConfig]:
        """Get animation config by ID"""
        return self.animations.get(anim_id)

    def get_all_animations(self) -> List[AnimationConfig]:
        """Get all animations (unordered)"""
        return list(self.animations.values())
