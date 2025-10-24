"""
Rainbow Snake Animation

Multi-pixel colorful snake travels through all zones sequentially.
"""

import asyncio
from typing import Tuple, List
from animations.base import BaseAnimation
from models.zone import Zone


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
        zones: dict,
        speed: int = 50,
        length: int = 5,
        hue_offset: int = 30,
        **kwargs
    ):
        super().__init__(zones, speed, **kwargs)
        self.length = max(2, min(20, length))  # Clamp 2-20
        self.hue_offset = hue_offset
        self.base_hue = 0  # Starting hue that will rotate

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

    def _hue_to_rgb(self, hue: int) -> Tuple[int, int, int]:
        """
        Convert hue (0-360) to RGB

        Args:
            hue: Hue value (0-360 degrees)

        Returns:
            RGB tuple (0-255 each)
        """
        hue = hue % 360
        h = hue / 60.0
        c = 255
        x = int(c * (1 - abs(h % 2 - 1)))

        if h < 1:
            return (c, x, 0)
        elif h < 2:
            return (x, c, 0)
        elif h < 3:
            return (0, c, x)
        elif h < 4:
            return (0, x, c)
        elif h < 5:
            return (x, 0, c)
        else:
            return (c, 0, x)

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
            r, g, b = self._hue_to_rgb(hue)

            # Get zone and pixel location
            zone_name, pixel_in_zone = self._get_pixel_location(pos)

            snake_pixels.append((zone_name, pixel_in_zone, r, g, b))

        return snake_pixels

    async def run(self):
        """
        Run rainbow snake animation

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

            # Then yield "turn on" for all snake pixels
            snake_pixels = self._get_snake_pixels()
            for zone_name, pixel_in_zone, r, g, b in snake_pixels:
                # Special yield format: (zone_name, pixel_index, r, g, b)
                # This tells the engine to use set_pixel_color() instead of set_zone_color()
                yield (zone_name, pixel_in_zone, r, g, b)

            # Move to next position
            self.current_position = (self.current_position + 1) % self.total_pixels

            # Slowly rotate base hue for changing colors
            self.base_hue = (self.base_hue + 1) % 360

            await asyncio.sleep(move_delay)
