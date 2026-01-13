"""
ZoneRenderState — Runtime render buffer per zone (not persisted).

Tracks the currently rendered pixel state, allowing FrameManager to:
- Detect frame changes (via hash comparison)
- Implement fallback logic when frames expire
- Debug which source last updated each zone

This is separate from domain ZoneState (which is persisted in state.json).

Warstwa: ENGINE / RENDER STATE
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import List, Optional

from models.enums import ZoneID, ZoneRenderMode, FrameSource
from models.color import Color


@dataclass
class ZoneRenderState:
    """
    Runtime state for a single zone's current pixel rendering.

    Kept separate from domain state to distinguish:
    - Domain state (persisted): User intent (color, brightness, mode, animation config)
    - Render state (ephemeral): Currently displayed pixels, which source rendered them

    Attributes:
        zone_id: Which zone this render state belongs to
        pixels: Currently rendered pixel colors (List[Color])
        brightness: Applied brightness level (0-100)
        mode: Current render mode (STATIC, ANIMATION)
        source: Which FrameSource last updated this zone
        last_update_ts: When this zone was last rendered
        dirty: Whether zone changed since last hardware push (for optimization)
    """

    zone_id: ZoneID
    pixels: List[Color] = field(default_factory=list)
    brightness: int = 100
    mode: ZoneRenderMode = ZoneRenderMode.STATIC
    source: Optional[FrameSource] = None
    last_update_ts: float = field(default_factory=time.time)
    dirty: bool = True

    # Internal: cached pixel hash (not persisted)
    _pixel_hash: Optional[int] = field(default=None, init=False, repr=False)

    def update_pixels(self, pixels: List[Color], source: FrameSource) -> None:
        """
        Update pixel data and mark as rendered by source.

        Args:
            pixels: New pixel colors for this zone
            source: Which FrameSource provided these pixels
        """
        self.pixels = pixels
        self.source = source
        self.last_update_ts = time.time()
        self.dirty = True
        self._pixel_hash = None  # Invalidate cached hash

    def get_pixel_hash(self) -> int:
        """
        Get hash of current pixel data (cached for performance).

        Hash includes both zone_id and pixel colors to avoid collisions.
        Used by FrameManager for frame change detection.

        Returns:
            Hash of (zone_id, tuple of RGB tuples)
        """
        if self._pixel_hash is None:
            # Hash pixels as a tuple of Color RGB values
            pixel_tuple = tuple(color.to_rgb() for color in self.pixels)
            self._pixel_hash = hash((self.zone_id, pixel_tuple))
        return self._pixel_hash

    def __repr__(self) -> str:
        return (
            f"ZoneRenderState({self.zone_id.name}, "
            f"pixels={len(self.pixels)}, "
            f"brightness={self.brightness}, "
            f"mode={self.mode.name}, "
            f"source={self.source.name if self.source else None})"
        )
