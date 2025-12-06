"""
Atomic frame models for centralized rendering system.

Each frame type represents a different rendering granularity:
- FullStripFrame: Single color for entire strip
- ZoneFrame: Per-zone colors
- PixelFrame: Per-pixel colors
- PreviewFrame: 8-pixel preview panel
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from models.enums import ZoneID, FramePriority, FrameSource
from models.color import Color

@dataclass
class BaseFrameV2:
    """Base class for all frame types with priority and TTL."""

    priority: FramePriority
    source: FrameSource
    timestamp: float = field(default_factory=time.time)
    ttl: float = 0.1  # 100ms default expiration
    partial: bool = False
    
    def is_expired(self) -> bool:
        """Check if frame has exceeded its time-to-live."""
        return (time.time() - self.timestamp) > self.ttl

@dataclass
class SingleZoneFrame(BaseFrameV2):
    zone_id: Optional[ZoneID] = None
    color: Optional[Color] = None

    def as_zone_update(self) -> Dict[ZoneID, Color]:
        if self.zone_id is not None and self.color is not None:
            return {self.zone_id: self.color}
        return {}
        
@dataclass
class MultiZoneFrame(BaseFrameV2):
    zone_colors: Dict[ZoneID, Color] = field(default_factory=dict)

    def as_zone_update(self) -> Dict[ZoneID, Color]:
        return self.zone_colors
    
@dataclass
class PixelFrameV2(BaseFrameV2):
    zone_pixels: Dict[ZoneID, List[Color]] = field(default_factory=dict)

    def as_zone_update(self) -> Dict[ZoneID, List[Color]]:
        return self.zone_pixels
    