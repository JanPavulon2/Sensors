from dataclasses import dataclass
from typing import Dict, List
from models.enums import ZoneID
from models.color import Color


@dataclass
class OutputFrame:
    """
    Final rendered frame.

    Represents the exact visual state sent to hardware
    and streamed to external consumers (UI, recorder, replay).
    """

    # Global animation time (seconds, synced to app clock)
    t: float

    # Fully expanded per-zone pixel data
    zones: Dict[ZoneID, List[Color]]