"""
Color Fade Animation

Smooth transition through hue spectrum (rainbow effect).
"""

import asyncio
from typing import List
from animations.base import BaseAnimation
from utils import hue_to_rgb
from models.domain.zone import ZoneCombined
from typing import AsyncIterator, Tuple

class ColorFadeAnimation(BaseAnimation):
    """
    Color fade animation - cycles through HSV hue spectrum

    All zones rotate through the full 360° hue spectrum smoothly.
    Brightness is preserved from each zone's current setting.

    Parameters:
        zones: Zone definitions
        speed: 1-100 (affects rotation speed)
        start_hue: Starting hue 0-360 (default: 0 = red)

    Example:
        anim = ColorFadeAnimation(zones, speed=50, start_hue=0)
        async for zone, r, g, b in anim.run():
            strip.set_zone_color(zone, r, g, b)
    """

    def __init__(
        self,
        zones: List[ZoneCombined],
        speed: int = 50,
        start_hue: int = 0,
        **kwargs
    ):
        super().__init__(zones, speed, **kwargs)
        self.current_hue = float(start_hue % 360)

    async def run(self) -> AsyncIterator[Tuple[str, int, int, int] | Tuple[str, int, int, int, int]]:
        """
        Run color fade animation

        Yields (zone_name, r, g, b) for each zone on each frame.
        """
        self.running = True

        while self.running:
            # Recalculate frame delay and hue increment each iteration for live updates
            frame_delay = self._calculate_frame_delay()

            # Calculate hue increment per frame based on speed
            # Speed 100 = full cycle in ~2s, Speed 1 = full cycle in ~20s
            min_increment = 360 / 1000  # Slow (speed=1)
            max_increment = 360 / 100   # Fast (speed=100)
            hue_increment = min_increment + (self.speed / 100) * (max_increment - min_increment)

            # Update all active zones (excluding lamp if lamp_solo)
            for zone_name in self.active_zones:
                # Get cached brightness or use default
                brightness = self.get_cached_brightness(zone_name)
                if brightness is None:
                    brightness = 255

                # Convert hue to RGB (full saturation)
                r, g, b = hue_to_rgb(int(self.current_hue))

                # Apply brightness scaling
                scale = brightness / 255.0
                r = int(r * scale)
                g = int(g * scale)
                b = int(b * scale)

                yield zone_name, r, g, b

            # Increment hue
            self.current_hue = (self.current_hue + hue_increment) % 360

            await asyncio.sleep(frame_delay)
