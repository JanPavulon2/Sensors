"""
Snake Animation

Single or multi-pixel snake travels through all zones sequentially.
"""

import asyncio
from typing import Tuple, List
from animations.base import BaseAnimation
from utils.colors import hue_to_rgb
from models.domain.zone import ZoneCombined
from typing import AsyncIterator, Tuple

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
        if color is not None:
            self.color = color
        else:
            self.color = hue_to_rgb(hue)

        self.length = max(1, min(4, length))  # Clamp 1-20 pixels

        # Build zone pixel map for navigation
        # Sort active zones by physical position (start index) not alphabetically
        zone_items = [(name, start, end) for name, (start, end) in self.active_zones.items()]
        zone_items.sort(key=lambda x: x[1])  # Sort by start index

        self.zone_order = [name for name, _, _ in zone_items]
        self.zone_pixel_counts = {}
        self.total_pixels = 0

        for name, start, end in zone_items:
            pixel_count = end - start + 1
            self.zone_pixel_counts[name] = pixel_count
            self.total_pixels += pixel_count

        self.current_position = 0

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
                pixel_in_zone = absolute_position - accumulated
                return zone_name, pixel_in_zone
            accumulated += zone_size

        # Shouldn't reach here, but fallback to first zone
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

    async def run(self) -> AsyncIterator[Tuple[str, int, int, int] | Tuple[str, int, int, int, int]]:
        """
        Run snake animation

        Note: This animation requires special handling - it needs to
        turn off ALL pixels first, then light up snake pixels.
        """
        self.running = True

        while self.running:
            # Recalculate delay each iteration for live speed updates
            # Speed 100 = 10ms per pixel, Speed 1 = 100ms per pixel
            min_delay = 0.01   # 10ms (fast)
            max_delay = 0.1    # 100ms (slow)
            move_delay = max_delay - (self.speed / 100) * (max_delay - min_delay)

            # First, yield "turn off" for all active zones
            for zone_name in self.active_zones:
                yield zone_name, 0, 0, 0

            # Then yield "turn on" for all snake pixels with brightness fade
            for i in range(self.length):
                # Calculate position (head is at current_position, tail extends backward)
                pos = (self.current_position - i) % self.total_pixels
                zone_name, pixel_in_zone = self._get_pixel_location(pos)

                # Apply brightness fade: each pixel after first has 20% lower brightness
                # i=0 (head): 100% brightness
                # i=1: 80% brightness
                # i=2: 60% brightness, etc.
                brightness_factor = 1.0 - (i * 0.2)
                brightness_factor = max(0.0, brightness_factor)  # Clamp to 0

                # Apply brightness to color
                r = int(self.color[0] * brightness_factor)
                g = int(self.color[1] * brightness_factor)
                b = int(self.color[2] * brightness_factor)

                # Special yield format: (zone_name, pixel_index, r, g, b)
                # This tells the engine to use set_pixel_color() instead of set_zone_color()
                yield (zone_name, pixel_in_zone, r, g, b)

            # Move to next position
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
