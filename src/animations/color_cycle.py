"""
Color Cycle Animation

Simple test animation - cycles through RGB colors every 3 seconds.
"""

import asyncio
from typing import AsyncIterator, Tuple
from animations.base import BaseAnimation
from models.domain.zone import ZoneCombined
from utils.logger import get_category_logger, LogCategory

log = get_category_logger(LogCategory.ANIMATION)


class ColorCycleAnimation(BaseAnimation):
    """
    Color Cycle - simple test animation

    Cycles: RED → GREEN → BLUE → repeat
    All zones change simultaneously every 3 seconds.
    """

    def __init__(
        self,
        zones: list[ZoneCombined],
        speed: int = 50,
        **kwargs
    ):
        super().__init__(zones, speed, **kwargs)

        # Hardcoded RGB sequence
        self.colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
        ]
        self.current_index = 0

        log.debug("ColorCycleAnimation initialized (RGB test)")

    async def run(self) -> AsyncIterator[Tuple[str, int, int, int]]:
        """Run color cycle animation"""
        self.running = True

        while self.running:
            # Get current color
            r, g, b = self.colors[self.current_index]

            log.debug(f"Cycle color {self.current_index + 1}/3: RGB({r},{g},{b})")

            # Set all zones
            for zone in self.active_zones:
                yield (zone, r, g, b)

            # Next color (wrap)
            self.current_index = (self.current_index + 1) % len(self.colors)

            # Fixed 3 second delay
            await asyncio.sleep(3.0)

    async def run_preview(self, pixel_count: int = 8):
        """Preview panel - shows same color as main strip"""
        self.running = True

        while self.running:
            r, g, b = self.colors[self.current_index]

            # All pixels same color (matches main strip behavior)
            frame = [(r, g, b)] * pixel_count
            yield frame

            self.current_index = (self.current_index + 1) % len(self.colors)

            await asyncio.sleep(3.0)
