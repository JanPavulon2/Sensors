"""
Snake Animation

Single or multi-pixel snake travels through all zones sequentially.
"""

import asyncio
from typing import Tuple, List, AsyncIterator
from animations.base import BaseAnimation
from utils.colors import hue_to_rgb
from models.domain.zone import ZoneCombined
from utils.logger import get_category_logger, LogCategory
from models.domain import ZoneCombined
from models.enums import ZoneID

log = get_category_logger(LogCategory.ANIMATION)

class SnakeAnimation(BaseAnimation):
    """
    Snake animation - single or multi-pixel snake travels through zones

    A snake with configurable length and color travels from the first zone to the last,
    turning off pixels behind it as it moves (snake effect).

    Parameters:
        zones: Zone definitions
        speed: 1-100 (affects travel speed)
        hue: Hue value (0-360) for snake color (ANIM_PRIMARY_COLOR_HUE)
        length: Snake length in pixels (default: 1)
        color: RGB tuple for backwards compatibility (deprecated, use hue instead)

    Example:
        anim = SnakeAnimation(zones, speed=60, hue=120, length=5)
        async for zone, r, g, b in anim.run():
            # Note: snake uses set_pixel_color() not set_zone_color()
            pass
    """

    def __init__(
        self,
        zones: List[ZoneCombined],
        speed: int = 50,
        hue: int = 0,
        length: int = 1,
        color: Tuple[int, int, int] | None = None,
        **kwargs
    ):
        super().__init__(zones, speed, **kwargs)

        # Support both hue (new) and color (backwards compat)
        self.color = hue_to_rgb(hue) if color is None else color

        self.length = max(1, min(4, length))  # Clamp 1-20 pixels

        # Build zone pixel map for navigation
        # Use only active zones (already filtered in BaseAnimation.__init__)
        zone_items = [(z.config.id, z.config.start_index, z.config.end_index) for z in self.active_zone_objects]
        zone_items.sort(key=lambda x: x[1])

        self.zone_order = [zone_id for zone_id, _, _ in zone_items]
        self.zone_pixel_counts = {zone_id: (end - start + 1) for zone_id, start, end in zone_items}
        self.total_pixels = sum(self.zone_pixel_counts.values())

        if self.total_pixels == 0:
            raise ValueError(
                f"SnakeAnimation requires at least one zone with pixels. "
                f"Got {len(zones)} zones with total {self.total_pixels} pixels."
            )

        self.current_position = 0

        # Track currently lit pixels to know which to turn off next frame
        self.previous_pixels: List[Tuple[ZoneID, int]] = []

        log.debug(f"SnakeAnimation initialized",
            length=self.length,
            total_pixels=self.total_pixels,
            zones=len(self.zone_order))
        
    def _get_pixel_location(self, absolute_position: int) -> Tuple[ZoneID, int]:
        """
        Convert absolute pixel position to (zone_name, pixel_index_in_zone)

        Args:
            absolute_position: Global pixel position (0 to total_pixels-1)

        Returns:
            Tuple of (zone_name, pixel_index_within_zone)
        """
        accumulated = 0
        for zone_id in self.zone_order:
            zone_size = self.zone_pixel_counts[zone_id]
            if absolute_position < accumulated + zone_size:
                return zone_id, absolute_position - accumulated
            accumulated += zone_size
        return self.zone_order[0], 0

    def update_param(self, param: str, value):
        """
        Update animation parameter live

        Special handling for 'hue' parameter - converts to RGB color
        """
        if param == "hue":
            # Convert hue to RGB and update color
            self.color = hue_to_rgb(value)
            setattr(self, param, value)  # Also store hue value
        else:
            # Use base class default behavior
            super().update_param(param, value)

    async def run(self) -> AsyncIterator[Tuple[ZoneID, int, int, int, int] | Tuple[str, int, int, int, int]]:
        """
        Run snake animation with smooth continuous motion

        Uses pixel-level control to create a snake that travels through all zones.
        Only turns off tail pixels (not all pixels) to eliminate flickering during wrap-around.

        Yields:
            Tuple[str, int, int, int, int]: (zone_name, pixel_index, r, g, b) for pixel-level updates
        """
        self.running = True

        while self.running:
            # Recalculate delay each iteration for live speed updates
            # Speed 100 = 10ms per pixel, Speed 1 = 100ms per pixel
            min_delay = 0.01   # 10ms (fast)
            max_delay = 0.1    # 100ms (slow)
            move_delay = max_delay - (self.speed / 100) * (max_delay - min_delay)

            # Determine which pixels should be on this frame
            snake_pixels: List[Tuple[ZoneID, int, int, int, int]] = []

            for i in range(self.length):
                pos = (self.current_position - i) % self.total_pixels
                zone_id, pixel_index = self._get_pixel_location(pos)
                brightness_factor = max(0.0, 1.0 - i * 0.2)
                r = int(self.color[0] * brightness_factor)
                g = int(self.color[1] * brightness_factor)
                b = int(self.color[2] * brightness_factor)
                snake_pixels.append((zone_id, pixel_index, r, g, b))
             
            
            # Determine which pixels to turn off (tail only)
            new_pixel_set = {(z, p) for z, p, _, _, _ in snake_pixels}
            for (z, p) in self.previous_pixels:
                if (z, p) not in new_pixel_set:
                    yield (z, p, 0, 0, 0)

            # Light up snake pixels
            for z, p, r, g, b in snake_pixels:
                yield (z, p, r, g, b)

            # Update previous state
            self.previous_pixels = [(z, p) for z, p, _, _, _ in snake_pixels]

            # Move forward
            self.current_position = (self.current_position + 1) % self.total_pixels
            await asyncio.sleep(move_delay)

    async def run_preview(self, pixel_count: int = 8):
        """
        Simplified preview for 8-pixel preview panel

        Shows a snake moving across 8 pixels with brightness fade (only when length > 1).
        Length clamped to 4 for preview (half of 8 pixels).
        """
        self.running = True
        position = 0

        while self.running:
            # Recalculate delay each iteration for live speed updates
            min_delay = 0.01   # 10ms (fast)
            max_delay = 0.1    # 100ms (slow)
            move_delay = max_delay - (self.speed / 100) * (max_delay - min_delay)

            # Build frame: all pixels off
            frame = [(0, 0, 0)] * pixel_count

            # Clamp length to max 4 for preview (half of 8 pixels)
            preview_length = min(self.length, 4)

            # Light up snake pixels with brightness fade (only when length > 1)
            for i in range(preview_length):
                pixel_pos = (position - i) % pixel_count

                # Apply brightness fade only when length > 1
                if preview_length > 1:
                    brightness_factor = 1.0 - (i * 0.2)
                    brightness_factor = max(0.0, brightness_factor)
                else:
                    brightness_factor = 1.0  # Full brightness for single pixel

                r = int(self.color[0] * brightness_factor)
                g = int(self.color[1] * brightness_factor)
                b = int(self.color[2] * brightness_factor)

                frame[pixel_pos] = (r, g, b)

            yield frame

            # Move to next position
            position = (position + 1) % pixel_count
            await asyncio.sleep(move_delay)
