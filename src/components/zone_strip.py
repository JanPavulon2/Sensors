"""
ZoneStrip - Logical zone-aware LED strip
==========================================
Domain layer: zone mapping + buffering + rendering coordination.

Responsibilities:
- Zone → physical index mapping (via ZonePixelMapper)
- Per-zone color cache (for AnimationEngine)
- Buffer sync with hardware
- Legacy API compatibility (FrameManager, TransitionService, AnimationEngine)
- Fast path rendering (apply_frame for atomic DMA push)

Does NOT:
- Create PixelStrip hardware (injected via IPhysicalStrip)
- Call GPIO/DMA directly
- Handle color order (delegated to WS281xStrip)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

from models.color import Color
from models.enums import ZoneID
from models.domain.zone import ZoneConfig
from hardware.led.strip_interface import IPhysicalStrip
from zone_layer.zone_pixel_mapper import ZonePixelMapper
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.ZONE)


class ZoneStrip:
    """
    Logical multi-zone LED strip.

    Architecture:
        ZoneStrip (domain logic)
          ↓ uses
        IPhysicalStrip (hardware abstraction)
          ↓ implemented by
        WS281xStrip (rpi_ws281x driver)

    Key features:
    - Zone color cache (_zone_color_cache)
    - Atomic frame rendering (show_full_pixel_frame → apply_frame)
    - Reversed zone support (via ZonePixelMapper)
    - Legacy API compatibility (tuple-based + Color-based)
    """

    def __init__(
        self,
        pixel_count: int,
        zones: List[ZoneConfig],
        hardware: IPhysicalStrip,
    ) -> None:
        """
        Initialize ZoneStrip.

        Args:
            pixel_count: Total LEDs on physical strip
            zones: List of ZoneConfig (start, end, reversed, id)
            hardware: Physical strip driver (WS281xStrip)
        """
        self.pixel_count = pixel_count
        self.hw = hardware

        # Zone mapping with reversed support
        self.mapper = ZonePixelMapper(zones, pixel_count)

        # Zone color cache (single representative color per zone)
        self._zone_color_cache: Dict[ZoneID, Color] = {}

        log.info(
            "ZoneStrip initialized",
            pixel_count=pixel_count,
            zones=len(zones),
            zone_ids=[z.id.name for z in zones],
        )

    # ==================== Core Setters ====================

    def set_zone_color(self, zone: ZoneID, color: Color, show: bool = True) -> None:
        """
        Set entire zone to single color.

        Args:
            zone: ZoneID enum
            color: models.color.Color
            show: If True, push to hardware immediately
        """
        indices = self.mapper.get_indices(zone)
        for phys_idx in indices:
            self.hw.set_pixel(phys_idx, color)

        # Update cache
        self._zone_color_cache[zone] = color

        if show:
            self.hw.show()

    def set_multiple_zones(self, zone_colors: Dict[ZoneID, Tuple[int, int, int]]) -> None:
        """
        Batch update multiple zones (single show() call).

        Args:
            zone_colors: {ZoneID: (r, g, b), ...}
        """
        for zone, rgb in zone_colors.items():
            color = Color.from_rgb(*rgb) if isinstance(rgb, tuple) else rgb
            indices = self.mapper.get_indices(zone)
            for phys_idx in indices:
                self.hw.set_pixel(phys_idx, color)
            self._zone_color_cache[zone] = color

        # Single flush (fast path)
        self.hw.show()

    def set_pixel_color(
        self,
        zone: ZoneID,
        pixel_index: int,
        r: int,
        g: int,
        b: int,
        show: bool = True,
    ) -> None:
        """
        Set single pixel within zone (logical index).

        Args:
            zone: ZoneID
            pixel_index: Logical index within zone (0-based)
            r, g, b: RGB values (0-255)
            show: If True, push to hardware
        """
        indices = self.mapper.get_indices(zone)
        if 0 <= pixel_index < len(indices):
            phys_idx = indices[pixel_index]
            color = Color.from_rgb(r, g, b)
            self.hw.set_pixel(phys_idx, color)

            if show:
                self.hw.show()

    def set_pixel(self, zone: ZoneID, idx: int, color: Color) -> None:
        """Set single pixel (Color object API)."""
        indices = self.mapper.get_indices(zone)
        if 0 <= idx < len(indices):
            self.hw.set_pixel(indices[idx], color)

    # ==================== Getters ====================

    def get_zone_color(self, zone: ZoneID) -> Optional[Tuple[int, int, int]]:
        """
        Get cached color for zone (used by AnimationEngine).

        Returns:
            (r, g, b) tuple or None if zone never set
        """
        color = self._zone_color_cache.get(zone)
        return color.to_rgb() if color else None

    def get_frame(self) -> List[Tuple[int, int, int]]:
        """
        Read current full-strip state from hardware (for TransitionService).

        Returns:
            List of (r, g, b) tuples (length = pixel_count)
        """
        return [self.hw.get_pixel(i).to_rgb() for i in range(self.pixel_count)]

    def get_zone_buffer(self, zone: ZoneID) -> List[Color]:
        """Get zone pixels as Color list (logical order)."""
        indices = self.mapper.get_indices(zone)
        return [self.hw.get_pixel(i) for i in indices]

    # ==================== Frame Rendering ====================

    def show_full_pixel_frame(
        self, zone_pixels_dict: Dict[ZoneID, List[Tuple[int, int, int]]]
    ) -> None:
        """
        Atomic render of full frame from zone-pixel dict.

        MAIN RENDERING PATH - used by FrameManager @ 60 FPS.

        Fast path: builds full frame buffer → apply_frame (single DMA push).

        Args:
            zone_pixels_dict: {ZoneID: [(r,g,b), (r,g,b), ...], ...}
                Each list is logical pixels for that zone (respects reversed).
        """
        # Build full frame (preserving pixels from zones not in dict)
        full_frame: List[Color] = [self.hw.get_pixel(i) for i in range(self.pixel_count)]

        for zone, pixels in zone_pixels_dict.items():
            indices = self.mapper.get_indices(zone)
            for logical_idx, (r, g, b) in enumerate(pixels):
                if logical_idx >= len(indices):
                    break
                phys_idx = indices[logical_idx]
                if 0 <= phys_idx < self.pixel_count:
                    full_frame[phys_idx] = Color.from_rgb(r, g, b)

        # Atomic push (single DMA transfer - no flicker)
        try:
            self.hw.apply_frame(full_frame)
        except Exception as ex:
            # Fallback: per-pixel set + show (slower but compatible)
            log.warn("apply_frame failed, using fallback", error=str(ex))
            for i, color in enumerate(full_frame):
                self.hw.set_pixel(i, color)
            self.hw.show()

    def build_frame_from_zones(
        self, zone_colors: Dict[ZoneID, Tuple[int, int, int]]
    ) -> List[Tuple[int, int, int]]:
        """
        Build absolute frame from zone colors (for transitions).

        Args:
            zone_colors: {ZoneID: (r, g, b), ...}

        Returns:
            List of (r, g, b) tuples (length = pixel_count)
        """
        frame = [(0, 0, 0)] * self.pixel_count
        for zone, (r, g, b) in zone_colors.items():
            indices = self.mapper.get_indices(zone)
            for phys_idx in indices:
                if 0 <= phys_idx < self.pixel_count:
                    frame[phys_idx] = (int(r), int(g), int(b))
        return frame

    def get_full_frame(self) -> List[Color]:
        """Get full strip as Color list (for new API)."""
        return [self.hw.get_pixel(i) for i in range(self.pixel_count)]

    # ==================== Control ====================

    def show(self) -> None:
        """
        Explicit hardware flush.

        Prefer apply_frame if full frame available (faster).
        """
        self.hw.show()

    def clear(self) -> None:
        """Turn off all LEDs (black + show)."""
        self.hw.clear()
        self._zone_color_cache.clear()

    def clear_zone(self, zone: ZoneID) -> None:
        """Set zone to black."""
        self.set_zone_color(zone, Color.black(), show=False)

    def clear_all(self) -> None:
        """Alias for clear()."""
        self.clear()

    # ==================== Utility ====================

    @property
    def led_count(self) -> int:
        """Total pixel count (alias for compatibility)."""
        return self.pixel_count

    def __repr__(self) -> str:
        zones = len(self.mapper.all_zone_ids())
        return f"<ZoneStrip pixels={self.pixel_count} zones={zones}>"
