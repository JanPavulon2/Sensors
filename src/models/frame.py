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
from typing import Dict, List, Tuple
from models.enums import ZoneID, FramePriority, FrameSource
from models.color import Color

@dataclass
class BaseFrame:
    """Base class for all frame types with priority and TTL."""

    priority: FramePriority
    source: FrameSource
    timestamp: float = field(default_factory=time.time)
    ttl: float = 0.1  # 100ms default expiration

    def is_expired(self) -> bool:
        """Check if frame has exceeded its time-to-live."""
        return (time.time() - self.timestamp) > self.ttl


@dataclass
class FullStripFrame(BaseFrame):
    """
    Single color for entire strip (all zones same color).
    """
    color: Tuple[int, int, int] = field(default=Color.black().to_rgb()) 
   
    def as_zone_update(self) -> Dict[ZoneID, Color]:
        """
        Convert FullStripFrame → per-zone pixel lists.
        All zones receive the same color, repeated for their length.
        """
        return {zone_id: Color.from_rgb(*self.color)
            for zone_id in ZoneID}
    
@dataclass
class ZoneFrame(BaseFrame):
    """
    Per-zone colors (each zone can have different color).

    Use Case: BreatheAnimation - zones breathe with individual colors
    Yield Format: (zone_id, r, g, b) OR dict of zone_id -> (r, g, b)
    """
    zone_colors: Dict[ZoneID, Color] = field(default_factory=dict)  # zone_id -> (r, g, b)
    
    def as_zone_update(self) -> Dict[ZoneID, Color]:
        return self.zone_colors

@dataclass
class PixelFrame(BaseFrame):
    # zone_pixels stores Color objects (not RGB tuples) for type consistency
    # This matches TransitionService and AnimationEngine output
    zone_pixels: Dict[ZoneID, List[Color]] = field(default_factory=dict)
    clear_other_zones: bool = False

    def as_zone_update(self) -> Dict[ZoneID, List[Color]]:
        # Colors already in correct format (service layer uses Color, not RGB tuples)
        return self.zone_pixels

@dataclass
class PreviewFrame(BaseFrame):
    """
    Preview panel frame (always 8 pixels).

    Use Cases:
    - Animation preview (synchronized mini-animation)
    - Parameter preview (brightness bar, color fill, etc.)
    """

    pixels: List[Tuple[int, int, int]] = field(default_factory=list)  # Always length 8, (r, g, b) per pixel

    def __post_init__(self):
        """Validate preview frame has exactly 8 pixels."""
        if len(self.pixels) != 8:
            raise ValueError(f"Preview must have 8 pixels, got {len(self.pixels)}")


# Type aliases for clarity
MainStripFrame = FullStripFrame | ZoneFrame | PixelFrame
AnyFrame = MainStripFrame | PreviewFrame
