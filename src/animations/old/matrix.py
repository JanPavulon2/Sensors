"""
Matrix Animation

Green "code rain" drops falling down through zones.
Perfect for lamp zone with 4 vertical columns.
"""

import asyncio
import random
from typing import List, Tuple
from animations.base import BaseAnimation
from utils.colors import hue_to_rgb
from models.domain.zone import ZoneCombined
from typing import AsyncIterator


class MatrixAnimation(BaseAnimation):
    """
    Matrix animation - green code rain drops falling through zones

    Each zone gets vertical "drops" of colored pixels falling down.
    Creates the iconic Matrix "digital rain" effect.

    Parameters:
        zones: Zone definitions
        speed: 1-100 (affects fall speed)
        hue: Hue value for drops (default: 120 = green)
        length: Drop length in pixels (2-8, default: 5)
        intensity: Brightness modulation (0-100, default: 100)

    Example:
        anim = MatrixAnimation(zones, speed=50, hue=120, length=5, intensity=100)
        async for zone, r, g, b in anim.run():
            strip.set_zone_color(zone, r, g, b)
    """

    def __init__(
        self,
        zones: List[ZoneCombined],
        speed: int = 50,
        hue: int = 120,  # Green
        length: int = 5,
        intensity: int = 100,
        **kwargs
    ):
        super().__init__(zones, speed, **kwargs)
        self.hue = hue
        self.length = max(2, min(8, length))
        self.intensity = max(0, min(100, intensity))

        # Track drop position for each zone
        self.zone_drops = {}
        for zone_name, (start, end) in self.active_zones.items():
            zone_size = end - start + 1
            # Random starting position for each zone
            self.zone_drops[zone_name] = {
                'position': random.randint(0, zone_size - 1),
                'speed_offset': random.uniform(0.8, 1.2)  # Slight speed variation per zone
            }

    async def run(self) -> AsyncIterator[Tuple[str, int, int, int, int]]:
        """
        Run Matrix animation

        Yields pixel-level updates: (zone_name, pixel_index, r, g, b)
        Uses batch updates - collects all pixel changes and yields them together
        to reduce strip.show() calls and eliminate PWM coil whine.
        """
        self.running = True

        while self.running:
            # Recalculate delay based on speed
            # Speed 100 = 20ms, Speed 1 = 100ms
            min_delay = 0.02
            max_delay = 0.1
            base_delay = max_delay - (self.speed / 100) * (max_delay - min_delay)

            # Get base color from hue
            base_r, base_g, base_b = hue_to_rgb(self.hue)

            # Apply intensity scaling
            intensity_factor = self.intensity / 100.0
            base_r = int(base_r * intensity_factor)
            base_g = int(base_g * intensity_factor)
            base_b = int(base_b * intensity_factor)

            # Collect all pixel updates for this frame (batch mode)
            pixel_updates = []

            # Render each zone
            for zone_name, (start, end) in self.active_zones.items():
                zone_size = end - start + 1
                drop_info = self.zone_drops[zone_name]
                drop_pos = int(drop_info['position'])

                # Turn off all pixels in zone first
                for pixel_idx in range(zone_size):
                    pixel_updates.append((zone_name, pixel_idx, 0, 0, 0))

                # Draw the drop with gradient
                for i in range(self.length):
                    pixel_pos = (drop_pos - i) % zone_size

                    # Brightness gradient: head is bright, tail fades
                    brightness_factor = 1.0 - (i / self.length)
                    brightness_factor = max(0.0, brightness_factor)

                    r = int(base_r * brightness_factor)
                    g = int(base_g * brightness_factor)
                    b = int(base_b * brightness_factor)

                    pixel_updates.append((zone_name, pixel_pos, r, g, b))

                # Move drop down
                move_speed = drop_info['speed_offset']
                drop_info['position'] = (drop_info['position'] + move_speed) % zone_size

                # Occasionally reset to top for continuous effect
                if random.random() < 0.02:  # 2% chance each frame
                    drop_info['position'] = 0

            # Yield all updates as batch (engine will need to handle this)
            for update in pixel_updates:
                yield update

            # Apply zone-specific delay variation
            await asyncio.sleep(base_delay)

    async def run_preview(self, pixel_count: int = 8):
        """
        Simplified preview for 8-pixel preview panel

        Shows a single Matrix drop falling through 8 pixels.
        """
        self.running = True
        drop_position = 0

        while self.running:
            # Recalculate delay based on speed
            min_delay = 0.02
            max_delay = 0.1
            move_delay = max_delay - (self.speed / 100) * (max_delay - min_delay)

            # Get base color from hue
            base_r, base_g, base_b = hue_to_rgb(self.hue)

            # Apply intensity scaling
            intensity_factor = self.intensity / 100.0
            base_r = int(base_r * intensity_factor)
            base_g = int(base_g * intensity_factor)
            base_b = int(base_b * intensity_factor)

            # Build frame: all pixels off
            frame = [(0, 0, 0)] * pixel_count

            # Clamp length to max 4 for preview (half of 8 pixels)
            preview_length = min(self.length, 4)

            # Light up drop pixels with gradient
            for i in range(preview_length):
                pixel_pos = (drop_position - i) % pixel_count

                # Brightness gradient: head is bright, tail fades
                brightness_factor = 1.0 - (i / preview_length)
                brightness_factor = max(0.0, brightness_factor)

                r = int(base_r * brightness_factor)
                g = int(base_g * brightness_factor)
                b = int(base_b * brightness_factor)

                frame[pixel_pos] = (r, g, b)

            yield frame

            # Move drop down
            drop_position = (drop_position + 1) % pixel_count

            await asyncio.sleep(move_delay)
