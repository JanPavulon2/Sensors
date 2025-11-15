"""
Breathe Animation

Smooth fade in/out effect (breathing) for all zones synchronously.
"""

import asyncio
import math
import time
from typing import Optional, Tuple, List, AsyncIterator
from animations.base import BaseAnimation
from models.domain.zone import ZoneCombined
from models.enums import ZoneID

class BreatheAnimation(BaseAnimation):
    """
    Breathe animation - smooth sine wave fade in/out

    All zones fade in/out synchronously, creating a calming breathing effect.

    Parameters:
        zones: Zone definitions
        speed: 1-100 (affects cycle duration)
        color: RGB tuple or None (None = use zone's current color)
        intensity: 1-100 (maximum brightness multiplier)

    Example:
        anim = BreatheAnimation(zones, speed=50, color=(255, 0, 0), intensity=100)
        async for zone, r, g, b in anim.run():
            strip.set_zone_color(zone, r, g, b)
    """

    def __init__(
        self,
        zones: List[ZoneCombined],
        speed: int = 50,
        color: Optional[Tuple[int, int, int]] = None,
        intensity: int = 100,
        **kwargs
    ):
        super().__init__(zones, speed, **kwargs)
        self.color = color
        self.intensity = max(1, min(100, intensity))

    async def run(self) -> AsyncIterator[Tuple[ZoneID, int, int, int]]:
        """
        Run breathe animation

        Yields (zone_id, r, g, b) for each zone on each frame.
        """
        self.running = True
        start_time = time.time()

        while self.running:
            # Calculate cycle duration based on speed
            # Speed 100 = 1s cycle, Speed 1 = 5s cycle
            min_cycle = 1.0
            max_cycle = 5.0
            cycle_duration = max_cycle - (self.speed / 100) * (max_cycle - min_cycle)

            # Calculate frame delay for smooth animation (60 steps per cycle)
            target_steps = 60
            frame_delay = cycle_duration / target_steps

            elapsed = time.time() - start_time

            # Sine wave: 0 -> 1 -> 0
            phase = (elapsed / cycle_duration) * 2 * math.pi
            brightness_factor = (math.sin(phase) + 1) / 2

            # Apply intensity scaling
            brightness_factor *= (self.intensity / 100)

            # Update all active zones (excluding lamp if lamp_solo)
            for zone_name in self.active_zones:
                if self.color:
                    # Use specified color
                    r, g, b = self.color
                else:
                    # Use zone's cached color
                    cached = self.get_cached_color(zone_name)
                    if cached:
                        r, g, b = cached
                    else:
                        # Fallback to white if no color cached
                        r, g, b = 255, 255, 255

                # Apply brightness modulation
                r_out = int(r * brightness_factor)
                g_out = int(g * brightness_factor)
                b_out = int(b * brightness_factor)

                yield zone_name, r_out, g_out, b_out

            await asyncio.sleep(frame_delay)

    async def run_preview(self, pixel_count: int = 8):
        """
        Preview for breathe animation

        If zone_colors provided: Each pixel represents one zone with its own color.
        Otherwise: All pixels breathe with the same specified color.
        """
        self.running = True
        start_time = time.time()

        while self.running:
            # Calculate cycle duration based on speed
            min_cycle = 1.0
            max_cycle = 5.0
            cycle_duration = max_cycle - (self.speed / 100) * (max_cycle - min_cycle)

            # Calculate frame delay for smooth animation (60 steps per cycle)
            target_steps = 60
            frame_delay = cycle_duration / target_steps

            elapsed = time.time() - start_time

            # Sine wave: 0 -> 1 -> 0
            phase = (elapsed / cycle_duration) * 2 * math.pi
            brightness_factor = (math.sin(phase) + 1) / 2

            # Apply intensity scaling
            brightness_factor *= (self.intensity / 100)

            frame = []

            # Check if zone_colors provided (per-zone preview)
            if hasattr(self, 'zone_colors') and self.zone_colors:
                # Each pixel = one zone with its own color
                for i in range(pixel_count):
                    if i < len(self.zone_colors):
                        r, g, b = self.zone_colors[i]
                    else:
                        r, g, b = 0, 0, 0  # Black for extra pixels

                    # Apply breathing brightness modulation
                    r_out = int(r * brightness_factor)
                    g_out = int(g * brightness_factor)
                    b_out = int(b * brightness_factor)
                    frame.append((r_out, g_out, b_out))
            else:
                # All pixels same color (fallback behavior)
                if self.color:
                    r, g, b = self.color
                else:
                    r, g, b = 255, 255, 255

                # Apply breathing brightness modulation
                r_out = int(r * brightness_factor)
                g_out = int(g * brightness_factor)
                b_out = int(b * brightness_factor)

                frame = [(r_out, g_out, b_out)] * pixel_count

            yield frame
            await asyncio.sleep(frame_delay)
