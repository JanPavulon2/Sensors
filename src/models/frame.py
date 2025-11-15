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

    Use Case: ColorCycleAnimation - entire strip cycles through hues
    Yield Format: (r, g, b)
    """

    color: Tuple[int, int, int] = field(default=(0, 0, 0))  # (r, g, b), default black


@dataclass
class ZoneFrame(BaseFrame):
    """
    Per-zone colors (each zone can have different color).

    Use Case: BreatheAnimation - zones breathe with individual colors
    Yield Format: (zone_id, r, g, b) OR dict of zone_id -> (r, g, b)
    """

    zone_colors: Dict[ZoneID, Tuple[int, int, int]] = field(default_factory=dict)  # zone_id -> (r, g, b)


@dataclass
class PixelFrame(BaseFrame):
    """
    Per-pixel colors (pixel-level control).

    Use Case: SnakeAnimation - snake moves pixel by pixel
    Yield Format: (zone_id, pixel_index, r, g, b) OR dict of zone_id -> [pixels]
    """

    zone_pixels: Dict[ZoneID, List[Tuple[int, int, int]]] = field(default_factory=dict)  # zone_id -> [(r, g, b), ...]


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
