from dataclasses import dataclass
from typing import Callable, Optional, List, Tuple
from models.enums import ZoneID
from enum import Enum

from dataclasses import dataclass
from typing import List, Tuple
from models.enums import ZoneID


@dataclass
class Frame:
    zone_id: ZoneID
    pixels: List[Tuple[int, int, int]]  # (r, g, b)
    
@dataclass
class ZoneFrame:
    zone_id: ZoneID
    pixels: List[Tuple[int, int, int]]  # lista kolorów w danej strefie
    
    