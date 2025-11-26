"""Zone-to-Hardware Mapping Models

Defines the relationship between logical zones (domain) and physical hardware strips.
No domain logic - pure data models.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List
from models.enums import ZoneID, LEDStripID


@dataclass(frozen=True)
class ZoneHardwareMapping:
    """Maps a hardware strip to the zones rendered on it"""
    hardware_id: LEDStripID    # e.g., MAIN_12V, AUX_5V
    zones: List[ZoneID]        # e.g., [FLOOR, LEFT, TOP, RIGHT, BOTTOM, LAMP]

    def __post_init__(self):
        """Validate that zones list is not empty"""
        if not self.zones:
            raise ValueError(f"ZoneHardwareMapping for {self.hardware_id.name} has no zones")


@dataclass(frozen=True)
class ZoneMappingConfig:
    """Container for all zone-to-hardware mappings"""
    mappings: List[ZoneHardwareMapping]

    def get_hardware_for_zone(self, zone_id: ZoneID) -> LEDStripID:
        """
        Get hardware strip ID for a given zone

        Args:
            zone_id: Zone to look up

        Returns:
            LEDStripID (e.g., MAIN_12V, AUX_5V)

        Raises:
            KeyError if zone not found in any mapping
        """
        for mapping in self.mappings:
            if zone_id in mapping.zones:
                return mapping.hardware_id
        raise KeyError(f"Zone {zone_id.name} not found in any hardware mapping")

    def get_zones_for_hardware(self, hardware_id: LEDStripID) -> List[ZoneID]:
        """
        Get all zones assigned to a hardware strip

        Args:
            hardware_id: Hardware strip ID (e.g., MAIN_12V)

        Returns:
            List of ZoneID enums assigned to this hardware

        Raises:
            KeyError if hardware not found
        """
        for mapping in self.mappings:
            if mapping.hardware_id == hardware_id:
                return list(mapping.zones)
        raise KeyError(f"Hardware {hardware_id.name} not found in mappings")