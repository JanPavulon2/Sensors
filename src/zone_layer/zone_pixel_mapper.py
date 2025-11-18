from __future__ import annotations
from dataclasses import dataclass
from typing import List
from models.domain.zone import ZoneConfig
from models.enums import ZoneID

@dataclass(frozen=True)
class ZonePixelMapping:
    zone_id: ZoneID
    physical_indices: List[int]    # always absolute indices on the physical strip

class ZonePixelMapper:
    """
    Maps ZoneConfig (start_index, end_index, reversed) into
    a physical pixel index list ready for writing.
    """

    def __init__(self, zones: List[ZoneConfig], strip_led_count: int) -> None:
        self.strip_led_count = strip_led_count
        self.mappings: dict[ZoneID, ZonePixelMapping] = {}

        for z in zones:
            indices = list(range(z.start_index, z.end_index + 1))
            if z.reversed:
                indices.reverse()

            # Clamp to physical strip (safe guard)
            indices = [i for i in indices if 0 <= i < strip_led_count]

            self.mappings[z.id] = ZonePixelMapping(
                zone_id=z.id,
                physical_indices=indices
            )

    def get_indices(self, zone_id: ZoneID) -> List[int]:
        return self.mappings[zone_id].physical_indices
