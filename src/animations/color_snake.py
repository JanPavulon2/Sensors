"""
Rainbow Snake Animation

Multi-pixel colorful snake travels through all zones sequentially.
"""

import asyncio
from typing import Tuple, List, AsyncIterator
from animations.base import BaseAnimation
from utils.colors import hue_to_rgb
from models.domain.zone import ZoneCombined
from utils.logger import get_category_logger, LogCategory

log = get_category_logger(LogCategory.ANIMATION)

class ColorSnakeAnimation(BaseAnimation):
    """
    Rainbow Snake animation - multi-pixel colorful snake travels through zones

    A colorful snake with rainbow gradient travels from the first zone to the last,
    leaving a trail of colors that fade out (snake effect with rainbow tail).

    Parameters:
        zones: Zone definitions
        speed: 1-100 (affects travel speed)
        length: Snake length in pixels (default: 5)
        hue_offset: Hue step between snake segments (default: 30)

    Example:
        anim = ColorSnakeAnimation(zones, speed=60, length=7, hue_offset=40)
        async for zone, r, g, b in anim.run():
            # Note: snake uses set_pixel_color() not set_zone_color()
            pass
    """

    def __init__(
        self,
        zones: List[ZoneCombined],
        speed: int = 50,
        length: int = 5,
        hue_offset: int = 30,
        hue: int = 0,  # Starting hue (ANIM_PRIMARY_COLOR_HUE)
        **kwargs
    ):
        super().__init__(zones, speed, **kwargs)
        self.length = max(2, min(5, length))  # Clamp 2-5
        self.hue_offset = hue_offset
        self.base_hue = hue  # Starting hue from parameter

        # Build zone pixel map for navigation
        # Sort active zones by physical position (start index) not alphabetically
        zone_items = [(name, start, end) for name, (start, end) in self.active_zones.items()]
        zone_items.sort(key=lambda x: x[1])  # Sort by start index

        self.zone_order = [name for name, _, _ in zone_items]
        self.zone_pixel_counts = {name: (end - start + 1) for name, start, end in zone_items}
        self.total_pixels = sum(self.zone_pixel_counts.values())
        self.current_position = 0

        # Track previous lit pixels
        self.previous_pixels: List[Tuple[str, int]] = []
        
    def _get_pixel_location(self, absolute_position: int) -> Tuple[str, int]:
        """
        Convert absolute pixel position to (zone_name, pixel_index_in_zone)

        Args:
            absolute_position: Global pixel position (0 to total_pixels-1)

        Returns:
            Tuple of (zone_name, pixel_index_within_zone)
        """
        accumulated = 0
        for zone_name in self.zone_order:
            zone_size = self.zone_pixel_counts[zone_name]
            if absolute_position < accumulated + zone_size:
                return zone_name, absolute_position - accumulated
            accumulated += zone_size

        # Fallback to first zone if position out of range
        return self.zone_order[0], 0

    def _get_snake_pixels(self) -> List[Tuple[str, int, int, int, int]]:
        """
        Get all snake pixels with their positions and colors

        Returns:
            List of (zone_name, pixel_index, r, g, b) tuples
        """
        snake_pixels = []

        for i in range(self.length):
            # Calculate position (head is at current_position, tail extends backward)
            pos = (self.current_position - i) % self.total_pixels

            # Calculate color with rainbow gradient
            hue = (self.base_hue + (i * self.hue_offset)) % 360
            r, g, b = hue_to_rgb(hue)

            # Get zone and pixel location
            zone_name, pixel_in_zone = self._get_pixel_location(pos)

            snake_pixels.append((zone_name, pixel_in_zone, r, g, b))

        return snake_pixels

    async def run(self) -> AsyncIterator[Tuple[str, int, int, int] | Tuple[str, int, int, int, int]]:
        """
        Run rainbow snake animation with continuous wrap-around

        Creates a multi-color snake with rainbow gradient that travels smoothly through all zones.
        Uses pixel-level control and only turns off tail pixels to eliminate flickering.
        Base hue rotates continuously for dynamic color shifting effect.

        Yields:
            Tuple[str, int, int, int, int]: (zone_name, pixel_index, r, g, b) for pixel-level updates
        """
        self.running = True
        self.previous_pixels: List[Tuple[str, int]] = []

        while self.running:
            # Dynamic delay for real-time speed adjustment
            min_delay = 0.01
            max_delay = 0.1
            move_delay = max_delay - (self.speed / 100) * (max_delay - min_delay)

            # Build list of current snake pixels
            snake_pixels: List[Tuple[str, int, int, int, int]] = []
            for i in range(self.length):
                # Head at current_position, tail behind (wraps automatically)
                pos = (self.current_position - i) % self.total_pixels
                hue = (self.base_hue + (i * self.hue_offset)) % 360
                r, g, b = hue_to_rgb(hue)
                zone_name, pixel_index = self._get_pixel_location(pos)
                snake_pixels.append((zone_name, pixel_index, r, g, b))

            # --- Only turn off pixels that are no longer in the snake ---
            new_pixel_set = {(z, p) for z, p, _, _, _ in snake_pixels}
            for (z, p) in self.previous_pixels:
                if (z, p) not in new_pixel_set:
                    yield (z, p, 0, 0, 0)

            # --- Light up current snake pixels ---
            for z, p, r, g, b in snake_pixels:
                yield (z, p, r, g, b)

            # Remember current pixels for next frame
            self.previous_pixels = [(z, p) for z, p, _, _, _ in snake_pixels]

            # Move snake forward smoothly and continuously
            self.current_position = (self.current_position + 1) % self.total_pixels
            self.base_hue = (self.base_hue + 1) % 360

            await asyncio.sleep(move_delay)
            
    async def run_preview(self, pixel_count: int = 8):
        """
        Simplified preview for 8-pixel preview panel

        Shows a rainbow snake moving across 8 pixels.
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

            # Light up snake pixels with rainbow colors
            for i in range(self.length):
                pixel_pos = (position - i) % pixel_count

                # Calculate hue with offset
                hue = (self.base_hue + (i * self.hue_offset)) % 360
                r, g, b = hue_to_rgb(hue)

                frame[pixel_pos] = (r, g, b)

            yield frame

            # Move to next position
            position = (position + 1) % pixel_count

            # Slowly rotate base hue for changing colors
            self.base_hue = (self.base_hue + 1) % 360

            await asyncio.sleep(move_delay)
