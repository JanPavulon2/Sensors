# zone_layer/zone_pixel_mapper.py
"""
ZonePixelMapper
===============
Maps ZoneID → physical pixel indices with reversed zone support.

Handles:
- start_index/end_index (inclusive)
- reversed flag (flips logical → physical mapping)
- Bounds validation
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

from models.enums import ZoneID
from models.domain.zone import ZoneConfig


@dataclass(frozen=True)
class ZoneMapping:
    """Internal zone geometry storage."""
    zone_id: ZoneID
    indices: List[int]  # Physical indices in logical order
    reversed: bool      # If True, logical 0 = last physical index


class ZonePixelMapper:
    """
    Zone → physical indices mapper with reversed support.

    Usage:
        mapper = ZonePixelMapper(zones, strip_led_count)
        indices = mapper.get_indices(ZoneID.FLOOR)  # respects reversed flag
    """

    def __init__(self, zones: List[ZoneConfig], strip_led_count: int) -> None:
        self.strip_led_count = strip_led_count
        self._mappings: Dict[ZoneID, ZoneMapping] = {}

        
        for zone in zones:
            start, end = zone.start_index, zone.end_index

            # normalize order
            if start <= end:
                indices = list(range(start, end + 1))
            else:
                # allow misconfigured zones
                indices = list(range(end, start + 1))

            # clamp for safety
            indices = [i for i in indices if 0 <= i < strip_led_count]

            self._mappings[zone.id] = ZoneMapping(
                zone_id=zone.id,
                indices=indices,
                reversed=zone.reversed,
            )
            
        # ----------------------------
    # PUBLIC API
    # ----------------------------

    def get_indices(self, zone_id: ZoneID) -> List[int]:
        """
        Return physical indices for this zone in LOGICAL order
        (meaning reversed if the zone is marked as reversed).
        """
        mapping = self._mappings.get(zone_id)
        if not mapping:
            return []

        if mapping.reversed:
            return list(reversed(mapping.indices))

        return list(mapping.indices)

    def get_physical_indices_raw(self, zone_id: ZoneID) -> List[int]:
        """Return raw physical indices without reversal."""
        mapping = self._mappings.get(zone_id)
        return list(mapping.indices) if mapping else []

    def all_zone_ids(self) -> List[ZoneID]:
        """Return IDs of all configured zones."""
        return list(self._mappings.keys())

    def get_zone_length(self, zone_id: ZoneID) -> int:
        """Return number of pixels for a zone."""
        mapping = self._mappings.get(zone_id)
        return len(mapping.indices) if mapping else 0