"""
Snake Animation

Single pixel travels through all zones sequentially.
"""

import asyncio
from typing import Tuple, List
from animations.base import BaseAnimation
from models.domain.zone import ZoneCombined
from typing import AsyncIterator, Tuple

class SnakeAnimation(BaseAnimation):
    """
    Snake animation - single lit pixel travels through zones

    A single pixel lights up and travels from the first zone to the last,
    turning off previous pixels as it moves (snake effect).

    Parameters:
        zones: Zone definitions
        speed: 1-100 (affects travel speed)
        color: RGB tuple for the snake pixel

    Example:
        anim = SnakeAnimation(zones, speed=60, color=(0, 255, 0))
        async for zone, r, g, b in anim.run():
            # Note: snake uses set_pixel_color() not set_zone_color()
            pass
    """

    def __init__(
        self,
        zones: List[ZoneCombined],
        speed: int = 50,
        color: Tuple[int, int, int] = (255, 255, 255),
        **kwargs
    ):
        super().__init__(zones, speed, **kwargs)
        self.color = color

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

    async def run(self) -> AsyncIterator[Tuple[str, int, int, int] | Tuple[str, int, int, int, int]]:
        """
        Run snake animation

        Note: This animation requires special handling - it needs to
        turn off ALL pixels first, then light up one pixel.
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

            # Then yield "turn on" for current pixel position
            zone_name, pixel_in_zone = self._get_pixel_location(self.current_position)

            # Special yield format: (zone_name, pixel_index, r, g, b)
            # This tells the engine to use set_pixel_color() instead of set_zone_color()
            yield (zone_name, pixel_in_zone, *self.color)

            # Move to next position
            self.current_position = (self.current_position + 1) % self.total_pixels

            await asyncio.sleep(move_delay)
