"""
Base Animation Class

All animations inherit from BaseAnimation and implement the run() method.
"""

import asyncio
from typing import Dict, Tuple, AsyncIterator, Optional, List
from models.zone import Zone


class BaseAnimation:
    """
    Base class for all LED animations

    Animations are async generators that yield (zone_name, r, g, b) tuples
    to update LED colors frame by frame.

    Args:
        zones: List of Zone objects
        speed: Animation speed (1-100, where 100 is fastest)
        **kwargs: Animation-specific parameters

    Example:
        async for zone_name, r, g, b in animation.run():
            strip.set_zone_color(zone_name, r, g, b)
    """

    def __init__(self, zones: List[Zone], speed: int = 50, excluded_zones=None, **kwargs):
        self.zones = zones
        self.excluded_zones = excluded_zones or []
        self.speed = max(1, min(100, speed))  # Clamp 1-100
        self.running = False
        self.zone_colors = {}  # Cache current zone colors
        self.zone_brightness = {}  # Cache current zone brightness

        # Filter out excluded zones and build dict for compatibility
        self.active_zones = {
            zone.tag: [zone.start_index, zone.end_index]
            for zone in zones
            if zone.tag not in self.excluded_zones
        }

    async def run(self) -> AsyncIterator[Tuple[str, int, int, int]]:
        """
        Main animation loop - yields (zone_name, r, g, b) tuples

        Must be implemented by subclasses.

        Yields:
            Tuple of (zone_name, red, green, blue)
        """
        raise NotImplementedError("Subclasses must implement run()")

    def stop(self):
        """Stop the animation"""
        self.running = False

    def update_param(self, param: str, value):
        """
        Update animation parameter live

        Args:
            param: Parameter name (e.g., 'speed', 'color')
            value: New value
        """
        if hasattr(self, param):
            setattr(self, param, value)

    def set_zone_color_cache(self, zone_name: str, r: int, g: int, b: int):
        """Cache zone color for animations that need current colors"""
        self.zone_colors[zone_name] = (r, g, b)

    def set_zone_brightness_cache(self, zone_name: str, brightness: int):
        """Cache zone brightness for animations that need current brightness"""
        self.zone_brightness[zone_name] = brightness

    def get_cached_color(self, zone_name: str) -> Optional[Tuple[int, int, int]]:
        """Get cached color for zone"""
        return self.zone_colors.get(zone_name)

    def get_cached_brightness(self, zone_name: str) -> Optional[int]:
        """Get cached brightness for zone"""
        return self.zone_brightness.get(zone_name)

    def _calculate_frame_delay(self) -> float:
        """
        Calculate delay between frames based on speed

        Returns:
            Delay in seconds (50 FPS at speed 100, slower at lower speeds)
        """
        # Speed 100 = 50 FPS (0.02s), Speed 1 = 10 FPS (0.1s)
        min_delay = 0.02  # 50 FPS max
        max_delay = 0.1   # 10 FPS min
        return max_delay - (self.speed / 100) * (max_delay - min_delay)
