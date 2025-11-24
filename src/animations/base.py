"""
Base Animation Class

All animations inherit from BaseAnimation and implement the run() method.
"""

import asyncio
from typing import Dict, Tuple, AsyncIterator, Optional, List, Sequence
from models.domain.zone import ZoneCombined
from models.enums import ZoneID


class BaseAnimation:
    """
    Base class for all LED animations

    Animations are async generators that yield (zone_id, r, g, b) tuples
    to update LED colors frame by frame.

    Args:
        zones: List of ZoneCombined objects
        speed: Animation speed (1-100, where 100 is fastest)
        excluded_zones: List of ZoneID enums to exclude from animation
        **kwargs: Animation-specific parameters

    Example:
        async for zone_id, r, g, b in animation.run():
            strip.set_zone_color(zone_id, r, g, b)
    """

    def __init__(self, zones: List[ZoneCombined], speed: int = 50, excluded_zones: Optional[List[ZoneID]] = None, **kwargs):
        self.zones = zones
        self.excluded_zones = excluded_zones or []
        self.speed = max(1, min(100, speed))  # Clamp 1-100
        self.running = False
        self.zone_colors: Dict[ZoneID, Tuple[int, int, int]] = {}  # Cache current zone colors
        self.zone_brightness: Dict[ZoneID, int] = {}  # Cache current zone brightness

        # Filter out excluded zones - use ZoneID as keys
        self.active_zones: Dict[ZoneID, List[int]] = {
            zone.config.id: [zone.config.start_index, zone.config.end_index]
            for zone in zones
            if zone.config.id not in self.excluded_zones
        }

        # Store only active zones for animations that need sequential access
        self.active_zone_objects: List[ZoneCombined] = [
            zone for zone in zones
            if zone.config.id not in self.excluded_zones
        ]

    async def run(self) -> AsyncIterator[Tuple[ZoneID, int, int, int]]:
        """
        Main animation loop - yields (zone_id, r, g, b) tuples

        Must be implemented by subclasses.

        Yields:
            Tuple of (ZoneID enum, red, green, blue)
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

    def set_zone_color_cache(self, zone_id: ZoneID, r: int, g: int, b: int):
        """Cache zone color for animations that need current colors"""
        self.zone_colors[zone_id] = (r, g, b)

    def set_zone_brightness_cache(self, zone_id: ZoneID, brightness: int):
        """Cache zone brightness for animations that need current brightness"""
        self.zone_brightness[zone_id] = brightness

    def get_cached_color(self, zone_id: ZoneID) -> Optional[Tuple[int, int, int]]:
        """Get cached color for zone"""
        return self.zone_colors.get(zone_id)

    def get_cached_brightness(self, zone_id: ZoneID) -> Optional[int]:
        """Get cached brightness for zone"""
        return self.zone_brightness.get(zone_id)

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

    async def run_preview(self, pixel_count: int = 8) -> AsyncIterator[Sequence[Tuple[int, int, int]]]:
        """
        Generate simplified preview frames for preview panel (8 pixels)

        Override this in subclasses to provide custom preview visualization.
        Default implementation shows static color.

        Args:
            pixel_count: Number of preview pixels (default: 8)

        Yields:
            List of (r, g, b) tuples, one per pixel

        Example:
            async for frame in animation.run_preview(8):
                preview_panel.show_frame(frame)
        """
        self.running = True
        # Default: show static color
        static_color = (100, 100, 100)
        frame = [static_color] * pixel_count

        while self.running:
            yield frame
            await asyncio.sleep(self._calculate_frame_delay())
