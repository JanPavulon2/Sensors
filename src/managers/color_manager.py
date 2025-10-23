"""
Color Manager - Processes color preset definitions

Processes color data from ConfigManager (does NOT load files).
Single responsibility: Parse and provide access to color presets.
"""

from typing import Dict, List, Tuple


class ColorManager:
    """
    Color preset manager (data processor only)

    Responsibilities:
    - Parse color preset data
    - Cache RGB values
    - Identify white presets
    - Provide preset lookup methods

    Does NOT load files - receives data from ConfigManager.

    Example:
        # Created by ConfigManager
        color_mgr = ColorManager(data)

        # Access presets
        rgb = color_mgr.get_preset_rgb("warm_white")
        is_white = color_mgr.is_white_preset("warm_white")
    """

    def __init__(self, data: dict):
        """
        Initialize ColorManager with parsed config data

        Args:
            data: Config dict with 'presets' and 'preset_order' keys
                  Example: {
                      'presets': {'red': {'rgb': [255,0,0], 'category': 'basic'}, ...},
                      'preset_order': ['red', 'orange', ...]
                  }
        """
        self.data = data
        self._preset_colors_cache: Dict[str, Tuple[int, int, int]] = {}
        self._white_presets_cache: set = set()
        self._process_data()

    def _process_data(self):
        """Process color data and build caches"""
        # Cache RGB values
        self._preset_colors_cache = {
            name: tuple(preset_data['rgb'])
            for name, preset_data in self.data.get('presets', {}).items()
        }

        # Cache white preset names (category='white')
        self._white_presets_cache = {
            name for name, preset_data in self.data.get('presets', {}).items()
            if preset_data.get('category') == 'white'
        }

    @property
    def preset_colors(self) -> Dict[str, Tuple[int, int, int]]:
        """Get all preset colors as {name: (r,g,b)} dict"""
        return self._preset_colors_cache

    @property
    def preset_order(self) -> List[str]:
        """Get preset cycling order"""
        return self.data.get('preset_order', [])

    @property
    def white_presets(self) -> set:
        """Get set of white preset names (category='white')"""
        return self._white_presets_cache

    def get_preset_rgb(self, name: str) -> Tuple[int, int, int]:
        """
        Get RGB for a preset name

        Args:
            name: Preset name (e.g., "warm_white", "red")

        Returns:
            (r, g, b) tuple

        Raises:
            KeyError: If preset doesn't exist
        """
        return self._preset_colors_cache[name]

    def get_preset_by_index(self, index: int) -> Tuple[str, Tuple[int, int, int]]:
        """
        Get preset by index in preset_order (wraps around)

        Args:
            index: Index in preset_order (can be negative, will wrap)

        Returns:
            (preset_name, (r, g, b)) tuple
        """
        order = self.preset_order
        index = index % len(order)
        name = order[index]
        return name, self._preset_colors_cache[name]

    def is_white_preset(self, name: str) -> bool:
        """
        Check if preset is a white (low saturation)

        Args:
            name: Preset name

        Returns:
            True if category='white'
        """
        return name in self._white_presets_cache
