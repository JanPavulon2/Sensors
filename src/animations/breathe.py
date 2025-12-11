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
from utils.logger import LogCategory, get_category_logger

log = get_category_logger(LogCategory.ANIMATION)

class BreatheAnimation(BaseAnimation):
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
        log.info("Initializing BreatheAnimation...")

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

        # log.info(f"Animatinon of {self.zone_id}: Step of BreatheAnimation...")

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