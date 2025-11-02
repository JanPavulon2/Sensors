"""
Animation Manager - Processes animation definitions

Processes animation metadata from ConfigManager (does NOT load files).
Single responsibility: Parse and provide access to animation metadata.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from models.enums import ParamID, AnimationID
from utils.enum_helper import EnumHelper


@dataclass
class AnimationInfo:
    """
    Animation metadata from config

    Attributes:
        id: AnimationID enum (e.g., AnimationID.BREATHE, AnimationID.COLOR_SNAKE)
        tag: String tag for file/class lookup (e.g., "breathe", "color_snake")
        display_name: Human-readable name (e.g., "Breathe", "Color Snake")
        description: Brief description of animation
        enabled: Whether animation is available for selection
        order: Display order in animation list
        parameters: List of ParamID this animation uses (in addition to base params)
        base_parameters: List of ParamID from animation_base_parameters (ANIM_SPEED, etc.)

    Example:
        AnimationInfo(
            id=AnimationID.COLOR_SNAKE,
            tag="color_snake",
            display_name="Color Snake",
            description="Multi-pixel rainbow snake",
            enabled=True,
            order=4,
            parameters=[ParamID.ANIM_LENGTH, ParamID.ANIM_HUE_OFFSET],
            base_parameters=[ParamID.ANIM_SPEED, ParamID.ANIM_PRIMARY_COLOR_HUE]
        )
    """
    id: AnimationID
    tag: str
    display_name: str
    description: str
    enabled: bool
    order: int
    parameters: List[ParamID]  # Additional params beyond base
    base_parameters: List[ParamID]  # Base params like ANIM_SPEED

    def get_all_parameters(self) -> List[ParamID]:
        """
        Get all parameters (base + specific)

        Returns:
            List of all ParamIDs for this animation
        """
        return self.base_parameters + self.parameters

    def __str__(self):
        """String representation for debugging"""
        param_names = [p.name for p in self.get_all_parameters()]
        return f"[{self.id.name:12}] {self.display_name:15} | tag:{self.tag:15} | params: {', '.join(param_names)}"


class AnimationManager:
    """
    Animation metadata manager (data processor only)

    Responsibilities:
    - Parse animation definitions
    - Build AnimationInfo objects
    - Provide animation metadata access

    Does NOT load files - receives data from ConfigManager.

    Example:
        # Created by ConfigManager
        anim_mgr = AnimationManager(data)

        # Access animations
        info = anim_mgr.get_animation("color_snake")
        print(info.display_name)  # "Color Snake"
        print(info.get_all_parameters())  # [ANIM_SPEED, ANIM_COLOR_1, LENGTH, HUE_OFFSET]
    """

    def __init__(self, data: dict):
        """
        Initialize AnimationManager with parsed config data

        Args:
            data: Config dict with 'animation_base_parameters', 'animations' keys
                  Example: {
                      'animation_base_parameters': {
                          'ANIM_SPEED': {'type': 'PERCENTAGE', ...}
                      },
                      'animations': [
                          {'id': 'BREATHE', 'name': 'Breathe', 'tag': 'breathe', ...}
                      ]
                  }
        """
        self.animations: Dict[AnimationID, AnimationInfo] = {}
        self.base_parameters: List[ParamID] = []
        self._process_data(data)

    def _process_data(self, data: dict):
        """
        Process animation configuration data

        Args:
            data: Config dict with 'animation_base_parameters' and 'animations' sections

        Raises:
            ValueError: If unknown ParamID or AnimationID referenced
        """
        # Parse base parameters (all animations have these)
        base_params_section = data.get('animation_base_parameters', {})
        self.base_parameters = []
        for param_name in base_params_section.keys():
            try:
                self.base_parameters.append(ParamID[param_name])
            except KeyError:
                raise ValueError(f"Unknown ParamID in animation_base_parameters: {param_name}")

        # Parse animation definitions (list format)
        animations_list = data.get('animations', [])
        for anim_data in animations_list:
            # Parse animation ID (enum)
            anim_id_str = anim_data.get('id', 'UNKNOWN')
            anim_id = EnumHelper.to_enum(AnimationID, anim_id_str)

            # Skip disabled animations
            if not anim_data.get('enabled', True):
                continue

            # Parse additional parameters
            additional_params = []
            for param_name in anim_data.get('parameters', []):
                try:
                    additional_params.append(ParamID[param_name])
                except KeyError:
                    raise ValueError(f"Unknown ParamID in animation '{anim_id_str}': {param_name}")

            # Create AnimationInfo
            self.animations[anim_id] = AnimationInfo(
                id=anim_id,
                tag=anim_data.get('tag', anim_id_str.lower()),
                display_name=anim_data.get('name', anim_id_str.title()),
                description=anim_data.get('description', ''),
                enabled=True,  # Already filtered above
                order=anim_data.get('order', 0),
                parameters=additional_params,
                base_parameters=self.base_parameters.copy()
            )

    def get_animation(self, id: AnimationID) -> Optional[AnimationInfo]:
        """
        Get animation info by AnimationID

        Args:
            id: AnimationID enum (e.g., AnimationID.BREATHE, AnimationID.COLOR_SNAKE)

        Returns:
            AnimationInfo or None if not found
        """
        return self.animations.get(id)

    def get_all_animations(self) -> List[AnimationInfo]:
        """
        Get all animation infos sorted by order

        Returns:
            List of AnimationInfo objects sorted by display order
        """
        return sorted(self.animations.values(), key=lambda a: a.order)

    def get_animation_ids(self) -> List[AnimationID]:
        """
        Get list of animation IDs sorted by order

        Returns:
            List of AnimationID enums: [AnimationID.BREATHE, AnimationID.SNAKE, ...]
        """
        return [info.id for info in self.get_all_animations()]

    def get_animation_names(self) -> List[str]:
        """
        Get list of display names in order

        Returns:
            List of display names: ["Breathe", "Snake", "Color Cycle", ...]
        """
        return [info.display_name for info in self.get_all_animations()]

    def animation_has_parameter(self, id: AnimationID, param_id: ParamID) -> bool:
        """
        Check if animation uses specific parameter

        Args:
            id: AnimationID enum
            param_id: ParamID to check

        Returns:
            True if animation uses this parameter
        """
        anim = self.get_animation(id)
        if not anim:
            return False
        return param_id in anim.get_all_parameters()

    def print_summary(self):
        """Print animation summary for debugging"""
        print("=" * 80)
        print("ANIMATIONS CONFIGURATION")
        print("=" * 80)
        print(f"Base parameters (all animations): {[p.name for p in self.base_parameters]}")
        print("-" * 80)

        for anim in self.animations.values():
            print(anim)
            if anim.description:
                print(f"{'':14} {anim.description}")

        print("-" * 80)
        print(f"Total animations: {len(self.animations)}")
        print("=" * 80)
