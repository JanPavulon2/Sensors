"""
Zone Manager

Manages collection of zones and calculates indices automatically.
"""

from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models.domain.zone import ZoneConfig


class ZoneManager:
    """
    Manages collection of LED zones

    Responsibilities:
    - Load zones from config
    - Sort zones by order
    - Calculate start/end indices automatically
    - Provide access to zones by tag or as dict

    Example:
        zones_config = [
            {"name": "Lamp", "tag": "lamp", "total_leds": 57, "enabled": True, "order": 1},
            {"name": "Top", "tag": "top", "total_leds": 12, "enabled": True, "order": 2},
        ]
        zone_manager = ZoneManager(zones_config)
        zone_manager.print_summary()

        lamp = zone_manager.get_zone("lamp")
        zones_dict = zone_manager.get_zone_dict()  # {"lamp": [0, 18], "top": [19, 22]}
    """

    def __init__(self, zones_config: List[dict]):
        """
        Initialize ZoneManager with zones configuration

        Args:
            zones_config: List of zone dicts from config.yaml
        """
        self.zones: List['ZoneConfig'] = []
        self._load_zones(zones_config)

        self._calculate_all_indices()

    def _load_zones(self, config: List[dict]):
        """
        Load zones from config and sort by order

        Args:
            config: List of zone configuration dicts
        """
        from models.domain.zone import ZoneConfig


        previous_end_index = -1
        for zone_cfg in config:
            
            self.start_index = previous_end_index + 1 if previous_end_index >= 0 else 0
            self.end_index = self.start_index + zone_cfg["pixel_count"] - 1

            zone = ZoneConfig(
                id=zone_cfg["id"],
                display_name=zone_cfg["name"],
                pixel_count=zone_cfg["pixel_count"],
                enabled=zone_cfg.get("enabled", True),
                reversed=zone_cfg.get("reversed", False),
                order=zone_cfg.get("order", 5),
                start_index=self.start_index,
                end_index=self.end_index)
            
            
            self.zones.append(zone)

        # Sort by order
        self.zones.sort(key=lambda z: z.order)

    def _calculate_all_indices(self):
        """
        Calculate start/end indices for all zones based on order

        Enabled zones get sequential indices, disabled zones get -1
        """
        prev_end = -1
        for zone in self.zones:
            if zone.enabled:
                zone.calculate_indices(prev_end)
                prev_end = zone.end_index
            else:
                zone.start_index = -1
                zone.end_index = -1

    def get_zone(self, tag: str) -> Optional['ZoneConfig']:
        """
        Get zone by tag

        Args:
            tag: Zone tag (e.g., "lamp", "top")

        Returns:
            Zone object or None if not found
        """
        return next((z for z in self.zones if z.tag == tag), None)

    def get_enabled_zones(self) -> List['ZoneConfig']:
        """
        Get only enabled zones

        Returns:
            List of enabled Zone objects
        """
        return [z for z in self.zones if z.enabled]

    def get_zone_dict(self) -> Dict[str, list]:
        """
        Get zones in old format for ZoneStrip compatibility

        Returns:
            Dict with tag as key and [start, end] as value
            Example: {"lamp": [0, 18], "top": [19, 22], ...}
        """
        return {
            z.tag: [z.start_index, z.end_index]
            for z in self.zones if z.enabled
        }

    def get_zone_tags(self) -> List[str]:
        """
        Get list of enabled zone tags in order

        Returns:
            List of zone tags: ["lamp", "top", "right", ...]
        """
        return [z.tag for z in self.zones if z.enabled]

    def print_summary(self):
        """Print zone summary for debugging"""
        print("=" * 70)
        print("ZONES CONFIGURATION")
        print("=" * 70)
        total_pixels = 0
        total_leds = 0

        for zone in self.zones:
            print(zone)
            if zone.enabled:
                total_pixels += zone.pixel_count
                total_leds += zone.total_leds

        print("-" * 70)
        print(f"Total: {total_pixels} pixels ({total_leds} LEDs)")
        print("=" * 70)
