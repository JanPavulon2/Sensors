"""
Atomic frame models for centralized rendering system (FrameManager V3).

Each frame type represents a different rendering granularity:

✔ SingleZoneFrame - one zone → one Color
✔ MultiZoneFrame  - many zones → one Color each
✔ PixelFrameV2    - many zones → pixel list (List[Color])
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Union
from models.enums import ZoneID, FramePriority, FrameSource
from models.color import Color

# Payload type: one zone → either a single Color or list of Colors
ZoneUpdateValue = Union[Color, List[Color]]

# =====================================================================
# Base class (TTL, priority, source)
# =====================================================================

@dataclass
class BaseFrameV2:
    """
    Shared metadata for all frame types.
    """

    priority: FramePriority
    source: FrameSource

    timestamp: float = field(default_factory=time.time)
    ttl: float = 0.1
    partial: bool = False

    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl
    
# =====================================================================
# 1) SingleZoneFrame — the simplest and safest atomic frame type
# =====================================================================

@dataclass
class SingleZoneFrame(BaseFrameV2):
    """
    EXACTLY ONE zone → EXACTLY ONE color.
    """

    zone_id: ZoneID = ZoneID.BOTTOM  # dummy default; overwritten when created
    color: Color = field(default_factory=Color.black)

    def as_zone_update(self) -> Dict[ZoneID, Color]:
        return {self.zone_id: self.color}
    
    @property
    def zone_colors(self) -> dict:
        return {self.zone_id: self.color}

# =====================================================================
# 2) MultiZoneFrame — many zones → one Color per zone
# =====================================================================

@dataclass
class MultiZoneFrame(BaseFrameV2):
    """
    Multi-zone update where each zone receives exactly one Color.
    """

    zone_colors: Dict[ZoneID, Color] = field(default_factory=dict)

    def as_zone_update(self) -> Dict[ZoneID, Color]:
        return self.zone_colors

# =====================================================================
# 3) PixelFrameV2 — many zones → List[Color]
# =====================================================================

@dataclass
class PixelFrameV2(BaseFrameV2):
    """
    Pixel-precise frame: each zone maps to List[Color]
    """

    zone_pixels: Dict[ZoneID, List[Color]] = field(default_factory=dict)

    def as_zone_update(self) -> Dict[ZoneID, List[Color]]:
        return self.zone_pixels
    



@dataclass
class MainStripFrame:
    """
    Unified frame used internally by FrameManager V3.

    Carries:
        updates: Dict[ZoneID, Color | List[Color]]

    Supports:
        • single-zone updates
        • multi-zone updates
        • pixel-precise updates
        • partial frames (merged with previous state)
    """

    priority: FramePriority
    source: FrameSource

    updates: Dict[ZoneID, ZoneUpdateValue]

    # Metadata
    ttl: float = 0.1
    partial: bool = False
    timestamp: float = field(default_factory=time.time)

    # ------------------------------------------------------------
    # TTL handling
    # ------------------------------------------------------------
    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl

    # ------------------------------------------------------------
    # FrameManager interface
    # ------------------------------------------------------------
    def as_zone_update(self) -> Dict[ZoneID, ZoneUpdateValue]:
        """
        Returns the raw update dict without interpretation.
        FrameManager processes merging + normalization.
        """
        return self.updates
