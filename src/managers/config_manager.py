import yaml
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models.zone import Zone


class ConfigManager:
    def __init__(self, config_path="config/config.yaml", defaults_path="config/config_defaults.yaml"):
        self.config_path = Path(config_path)
        self.config_defaults_path = Path(defaults_path)
        self.data = {}
        self._zone_manager = None  # Private ZoneManager instance

    def load(self):
        """Load YAML configuration, fallback to defaults on failure."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.data = yaml.safe_load(f)
        except Exception as ex:
            print(f"[WARN] Failed to load config.yaml: {ex}")
            with open(self.config_defaults_path, "r", encoding="utf-8") as f:
                self.data = yaml.safe_load(f)

        # Initialize ZoneManager with zones from config
        zones_config = self.data.get("zones", [])
        if zones_config:
            from managers.zone_manager import ZoneManager
            self._zone_manager = ZoneManager(zones_config)
            # Print zone summary on load
            self._zone_manager.print_summary()
        else:
            print("[WARN] No zones defined in config!")

        return self.data

    @property
    def hardware(self):
        """Get hardware configuration"""
        return self.data.get("hardware", {})

    @property
    def zones(self):
        """
        Get zones in old dict format for compatibility

        Returns:
            Dict with zone tag as key and [start, end] as value
            Example: {"lamp": [0, 18], "top": [19, 22], ...}
        """
        if self._zone_manager:
            return self._zone_manager.get_zone_dict()
        return {}

    # ===== Zone access API (Opcja A) =====

    def get_zone(self, tag: str) -> Optional['Zone']:
        """
        Get zone object by tag

        Args:
            tag: Zone tag (e.g., "lamp", "top")

        Returns:
            Zone object or None if not found
        """
        if self._zone_manager:
            return self._zone_manager.get_zone(tag)
        return None

    def get_all_zones(self) -> List['Zone']:
        """
        Get all zone objects

        Returns:
            List of all Zone objects
        """
        if self._zone_manager:
            return self._zone_manager.zones
        return []

    def get_enabled_zones(self) -> List['Zone']:
        """
        Get only enabled zone objects

        Returns:
            List of enabled Zone objects
        """
        if self._zone_manager:
            return self._zone_manager.get_enabled_zones()
        return []

    def get_zone_tags(self) -> List[str]:
        """
        Get list of enabled zone tags in order

        Returns:
            List of zone tags: ["lamp", "top", "right", ...]
        """
        if self._zone_manager:
            return self._zone_manager.get_zone_tags()
        return []