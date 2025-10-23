"""
Animation Manager - Processes animation definitions

Processes animation metadata from ConfigManager (does NOT load files).
Single responsibility: Parse and provide access to animation metadata.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from models.enums import ParamID


@dataclass
class AnimationInfo:
    """
    Animation metadata from config

    Attributes:
        tag: Technical identifier (e.g., "breathe", "color_snake")
        display_name: Human-readable name (e.g., "Breathe", "Color Snake")
        description: Brief description of animation
        parameters: List of ParamID this animation uses (in addition to base params)
        base_parameters: List of ParamID from animation_base_parameters (ANIM_SPEED, ANIM_COLOR_1)

    Example:
        AnimationInfo(
            tag="color_snake",
            display_name="Color Snake",
            description="Multi-pixel rainbow snake",
            parameters=[ParamID.LENGTH, ParamID.HUE_OFFSET],
            base_parameters=[ParamID.ANIM_SPEED, ParamID.ANIM_COLOR_1]
        )
    """
    tag: str
    display_name: str
    description: str
    parameters: List[ParamID]  # Additional params beyond base
    base_parameters: List[ParamID]  # Always: ANIM_SPEED, ANIM_COLOR_1

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
        return f"[{self.tag:12}] {self.display_name:15} | params: {', '.join(param_names)}"


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
                      'animations': {
                          'breathe': {'display_name': 'Breathe', 'parameters': [...]}
                      }
                  }
        """
        self.animations: Dict[str, AnimationInfo] = {}
        self.base_parameters: List[ParamID] = []
        self._process_data(data)

    def _process_data(self, data: dict):
        """
        Process animation configuration data

        Args:
            data: Config dict with 'animation_base_parameters' and 'animations' sections

        Raises:
            ValueError: If unknown ParamID referenced
        """
        # Parse base parameters (all animations have these)
        base_params_section = data.get('animation_base_parameters', {})
        self.base_parameters = []
        for param_name in base_params_section.keys():
            try:
                self.base_parameters.append(ParamID[param_name])
            except KeyError:
                raise ValueError(f"Unknown ParamID in animation_base_parameters: {param_name}")

        # Parse animation definitions
        animations_section = data.get('animations', {})
        for anim_tag, anim_data in animations_section.items():
            # Parse additional parameters
            additional_params = []
            for param_name in anim_data.get('parameters', []):
                try:
                    additional_params.append(ParamID[param_name])
                except KeyError:
                    raise ValueError(f"Unknown ParamID in animation '{anim_tag}': {param_name}")

            # Create AnimationInfo
            self.animations[anim_tag] = AnimationInfo(
                tag=anim_tag,
                display_name=anim_data.get('display_name', anim_tag.title()),
                description=anim_data.get('description', ''),
                parameters=additional_params,
                base_parameters=self.base_parameters.copy()
            )

    def get_animation(self, tag: str) -> Optional[AnimationInfo]:
        """
        Get animation info by tag

        Args:
            tag: Animation tag (e.g., "breathe", "color_snake")

        Returns:
            AnimationInfo or None if not found
        """
        return self.animations.get(tag)

    def get_all_animations(self) -> List[AnimationInfo]:
        """
        Get all animation infos in definition order

        Returns:
            List of AnimationInfo objects
        """
        return list(self.animations.values())

    def get_animation_tags(self) -> List[str]:
        """
        Get list of animation tags

        Returns:
            List of animation tags: ["breathe", "color_fade", "snake", "color_snake"]
        """
        return list(self.animations.keys())

    def get_animation_names(self) -> List[str]:
        """
        Get list of display names

        Returns:
            List of display names: ["Breathe", "Color Fade", "Snake", "Color Snake"]
        """
        return [info.display_name for info in self.animations.values()]

    def animation_has_parameter(self, tag: str, param_id: ParamID) -> bool:
        """
        Check if animation uses specific parameter

        Args:
            tag: Animation tag
            param_id: ParamID to check

        Returns:
            True if animation uses this parameter
        """
        anim = self.get_animation(tag)
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
