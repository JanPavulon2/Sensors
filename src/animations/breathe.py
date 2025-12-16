"""
Breathe Animation

Smooth fade in/out effect (breathing) for all zones synchronously.
"""

import math
import time
from typing import Optional, List
from animations.base import BaseAnimation
from models.animation_params.animation_param_id import AnimationParamID
from models.animation_params.brightness_param import BrightnessParam
from models.animation_params.speed_param import SpeedParam
from models.color import Color
from models.domain import ZoneCombined
from models.enums import ZoneID, FramePriority, FrameSource
from models.frame import SingleZoneFrame
from utils.logger import LogCategory, get_category_logger

log = get_category_logger(LogCategory.ANIMATION)

from dataclasses import dataclass
from typing import Any



class BreatheAnimation(BaseAnimation):
    """
    Smooth breathing (sinusoidal brightness modulation).

    Uses:
    - zone base color
    - zone base brightness
    """

    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(
            # default=50,
            # min=1, 
            # max=100,
            # step=10
        ),
        AnimationParamID.BRIGHTNESS: BrightnessParam(
            # default=100,   
            # min=5,
            # max=100,
            # step=5
            ),
    }
    def __init__(self, zone, params):
        super().__init__(zone, params)
        self._start_time = time.monotonic()
        self._phase = 0.0

    async def step(self) -> SingleZoneFrame:
        speed = self.get_param(AnimationParamID.SPEED, 50)
        brightness_percent = self.get_param(AnimationParamID.BRIGHTNESS, 100)

        
        period = max(0.8, 8.0 - (speed / 100) * 7.0)
        t = (time.monotonic() - self._start_time) / period
        
        # ---- breathe curve ----
        phase = (math.sin(t * 2 * math.pi - math.pi / 2) + 1) / 2
        scale = 0.15 + phase * 0.85   # never fully off

        # ---- final brightness ----
        base_brightness = self.base_brightness
        final_brightness = int(
            base_brightness * (brightness_percent / 100.0) * scale
        )
        
        color = self.base_color.with_brightness(final_brightness)

        return SingleZoneFrame(
            zone_id=self.zone_id,
            color=color,
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=0.12,
        )
        
        # speed → time scale
        phase_step = speed / 400.0
        self._phase += phase_step

        # sine wave 0..1
        pulse = (math.sin(self._phase) + 1.0) / 2.0

        brightness = int(pulse * max_brightness)

        color2 = Color.from_hue(self.base_color)
        
        color = self.zone.state.color.with_brightness(brightness)

        return SingleZoneFrame(
            zone_id=self.zone.id,
            color=color,
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
            ttl=0.1,
        )
# class BreatheAnimationParams:
#     """
#     Declares which parameters BREATHE animation supports.
#     Order matters (encoder cycling).
#     """
#     def __init__(
#         self,
#         speed: int = 50,
#         brightness: int = 100,
#         intensity: int = 50
#     ):
#         self.speed = SpeedParam(speed)
#         self.brightness = BrightnessParam(brightness)
#         self.intensity = IntensityParam(intensity)
        
#     def all(self) -> list[AnimationParam]:
#         return [
#             self.speed,
#             self.brightness,
#             self.intensity
#         ]
    
# class BreatheAnimation(BaseAnimation):
#     """
#     Breathe animation - smooth sine wave fade in/out

#     One animation instance controls ONE ZONE.
#     AnimationEngine launches one instance per animated zone.

#     """

#     def __init__(
#         self,
#         zone: ZoneCombined,
#         params: BreatheAnimationParams
#     ):
#         super().__init__(zone)
#         self.params = params
        
#         self.start_time = time.time()

#     # ------------------------------------------------------------
#     # Core animation step
#     # ------------------------------------------------------------
#     async def step(self):
#         """Compute one frame for THIS zone only."""

#         brightness = self.params.brightness.get_value()
#         speed = self.params.speed.get_value()
#         intensity = self.params.intensity.get_value()
                        
#         # log.info(f"Animatinon of {self.zone_id}: Step of BreatheAnimation...")

#         elapsed = time.time() - self.start_time

#         # speed controls breathing cycle length
#         min_cycle = 1.0
#         max_cycle = 5.0
#         cycle = max_cycle - (self.speed / 100) * (max_cycle - min_cycle)

#         # sine wave 0→1→0
#         phase = (elapsed / cycle) * 2 * math.pi
#         brightness_factor = (math.sin(phase) + 1) / 2

#         # apply intensity (0–100)
#         intensity = int(self.params.intensity.get_value()("intensity", 100))
#         brightness_factor *= (intensity / 100)

#         # compute final brightness (0–100 integer)
#         brightness_pct = int(brightness_factor * 100)

#         # base color = param color OR zone state's base color
#         color: Color = (
#             self.params.get("color")
#             or self.zone.state.color
#             or Color.white()
#         )

#         # output color with new brightness
#         out_color = color.with_brightness(brightness_pct)

#         # return proper frame model
#         return SingleZoneFrame(
#             priority=FramePriority.ANIMATION,
#             source=FrameSource.ANIMATION,
#             zone_id=self.zone_id,
#             color=out_color,
#             partial=True  # ← VERY IMPORTANT
#         )