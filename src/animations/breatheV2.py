"""
Breathe Animation

Smooth fade in/out effect (breathing) for all zones synchronously.
"""

import math
import time
from typing import Optional
from animations.base import BaseAnimation
from models.color import Color
from models.domain import ZoneCombined
from models.enums import ZoneID, FramePriority, FrameSource
from models.frame_v2 import SingleZoneFrame

class BreatheAnimationV2(BaseAnimation):
    """
    Breathe animation - smooth sine wave fade in/out

    One animation instance controls ONE ZONE.
    AnimationEngine launches one instance per animated zone.
    
    """

    def __init__(
        self,
        zone: ZoneCombined,
        speed: int = 50,
        color: Optional[Color] = None,
        intensity: int = 100,
        **params
    ):
        if color is not None:
            params["color"] = color
        
        params.setdefault("intensity", intensity)
        
        super().__init__(zone, speed, **params)
        
        self.start_time = time.time()
        
    # ------------------------------------------------------------
    # Core animation step
    # ------------------------------------------------------------
    async def step(self):
        """Compute one frame for THIS zone only."""

        
        elapsed = time.time() - self.start_time

        # speed controls breathing cycle length
        min_cycle = 1.0
        max_cycle = 5.0
        cycle = max_cycle - (self.speed / 100) * (max_cycle - min_cycle)

        # sine wave 0→1→0
        phase = (elapsed / cycle) * 2 * math.pi
        brightness_factor = (math.sin(phase) + 1) / 2

        # apply intensity (0–100)
        intensity = int(self.params.get("intensity", 100))
        brightness_factor *= (intensity / 100)
        
        # compute final brightness (0–100 integer)
        brightness_pct = int(brightness_factor * 100)

        # base color = param color OR zone state's base color
        color: Color = (
            self.params.get("color")
            or self.zone.state.color
            or Color.white()
        )
        
        # output color with new brightness
        out_color = color.with_brightness(brightness_pct)

        # return proper frame model
        return SingleZoneFrame(
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            zone_id=self.zone_id,
            color=out_color,
            partial=True  # ← VERY IMPORTANT
        )
        
    
    # async def run_preview(self, pixel_count: int = 8):
    #     """
    #     Preview for breathe animation

    #     If zone_colors provided: Each pixel represents one zone with its own color.
    #     Otherwise: All pixels breathe with the same specified color.
    #     """
    #     self.running = True
    #     start_time = time.time()

    #     while self.running:
    #         # Calculate cycle duration based on speed
    #         min_cycle = 1.0
    #         max_cycle = 5.0
    #         cycle_duration = max_cycle - (self.speed / 100) * (max_cycle - min_cycle)

    #         # Calculate frame delay for smooth animation (60 steps per cycle)
    #         target_steps = 60
    #         frame_delay = cycle_duration / target_steps

    #         elapsed = time.time() - start_time

    #         # Sine wave: 0 -> 1 -> 0
    #         phase = (elapsed / cycle_duration) * 2 * math.pi
    #         brightness_factor = (math.sin(phase) + 1) / 2

    #         # Apply intensity scaling
    #         brightness_factor *= (self.intensity / 100)

    #         frame = []

    #         # Check if zone_colors provided (per-zone preview)
    #         if hasattr(self, 'zone_colors') and self.zone_colors:
    #             # Each pixel = one zone with its own color
    #             for i in range(pixel_count):
    #                 if i < len(self.zone_colors):
    #                     r, g, b = self.zone_colors[i].to_rgb()
    #                 else:
    #                     r, g, b = Color.black().to_rgb()  # Black for extra pixels

    #                 # Apply breathing brightness modulation
    #                 r_out = int(r * brightness_factor)
    #                 g_out = int(g * brightness_factor)
    #                 b_out = int(b * brightness_factor)
    #                 frame.append((r_out, g_out, b_out))
    #         else:
    #             # All pixels same color (fallback behavior)
    #             if self.color:
    #                 r, g, b = self.color
    #             else:
    #                 r, g, b = 255, 255, 255

    #             # Apply breathing brightness modulation
    #             r_out = int(r * brightness_factor)
    #             g_out = int(g * brightness_factor)
    #             b_out = int(b * brightness_factor)

    #             frame = [(r_out, g_out, b_out)] * pixel_count

    #         yield frame
    #         await asyncio.sleep(frame_delay)
