"""
LedChannel - Logical zone-aware LED strip rendering interface.

Core Rendering Path:
    FrameManager.show_full_pixel_frame() ← Main rendering (60 FPS)

Secondary Methods:
    build_frame_from_zones() ← Transition target capture
    get_frame() ← State readback for transitions
    clear() ← Shutdown
    show() ← Hardware flush (rarely used)

Architecture:
    LedChannel (zone-to-pixel mapper + rendering interface)
      ↓ delegates to
    IPhysicalStrip (hardware abstraction)
      ↓ implemented by
    WS281xStrip (GPIO/DMA driver)
"""

from __future__ import annotations
from typing import Dict, List

from models.enums import ZoneID
from models.domain.zone import ZoneConfig
from models.color import Color
from hardware.led.strip_interface import IPhysicalStrip
from zone_layer.zone_pixel_mapper import ZonePixelMapper
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.ZONE)


class LedChannel:
    """
    Logical multi-zone LED strip rendering interface.

    Core responsibility: Accept zone-to-pixel mappings and push atomically to hardware.

    Used by:
    - FrameManager: Calls show_full_pixel_frame() at 60 FPS to render selected frame
    - TransitionService: Reads current frame state via get_frame()
    """

    def __init__(
        self,
        pixel_count: int,
        zones: List[ZoneConfig],
        hardware: IPhysicalStrip,
    ) -> None:
        """
        Initialize LedChannel.

        Args:
            pixel_count: Total LEDs on physical strip
            zones: List of ZoneConfig (start, end, reversed, id)
            hardware: Physical strip driver (WS281xStrip)
        """
        self.pixel_count = pixel_count
        self.hardware = hardware
        self.mapper = ZonePixelMapper(zones, pixel_count)

        log.info(
            "LedChannel initialized",
            pixel_count=pixel_count,
            zones=len(zones),
            zone_ids=[z.id.name for z in zones],
        )

    # ==================== Reading Current State ====================

    def get_frame(self) -> List[Color]:
        """
        Read current full-strip state from hardware.

        Used by TransitionService to capture current state before transitions.

        Returns:
            List of Color objects (length = pixel_count)
        """
        return self.hardware.get_frame()

    # ==================== Frame Rendering ====================

    def show_full_pixel_frame(self, zone_pixels_dict: Dict[ZoneID, List[Color]]) -> None:
        """
        Atomic render of full frame from zone-pixel dictionary.

        MAIN RENDERING PATH - Called by FrameManager at 60 FPS.

        Builds complete pixel frame, applies zone updates, and pushes atomically to hardware
        (single DMA transfer with no flicker).

        Args:
            zone_pixels_dict: {ZoneID: [Color, Color, ...]}
                Zone IDs map to their pixel colors (respects zone reversal via mapper)
        """
        # Build full frame (preserving pixels from zones not in dict)
        full_frame: List[Color] = self.hardware.get_frame()

        # Apply zone pixel updates to full frame
        for zone, pixels in zone_pixels_dict.items():
            indices = self.mapper.get_indices(zone)
            for logical_idx, color in enumerate(pixels):
                if logical_idx >= len(indices):
                    break
                phys_idx = indices[logical_idx]
                if 0 <= phys_idx < self.pixel_count:
                    full_frame[phys_idx] = color

        # Atomic push (single DMA transfer - no flicker)
        try:
            self.hardware.apply_frame(full_frame)
        except Exception as ex:
            # Fallback: per-pixel set + show (slower but compatible)
            log.warn("apply_frame failed, using fallback", error=str(ex))
            for i, color in enumerate(full_frame):
                self.hardware.set_pixel(i, color)
            self.show()

    # ==================== Control ====================

    def show(self) -> None:
        """
        Hardware flush (rarely used; prefer show_full_pixel_frame for atomicity).
        """
        self.hardware.show()

    def clear(self) -> None:
        """
        Turn off all LEDs (black + flush to hardware).

        Used during shutdown to ensure LEDs are off before GPIO teardown.
        """
        self.hardware.clear()

    # ==================== Utility ====================

    def __repr__(self) -> str:
        zones = len(self.mapper.all_zone_ids())
        return f"<LedChannel pixels={self.pixel_count} zones={zones}>"
