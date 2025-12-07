"""
Base Animation Class

All animations inherit from BaseAnimation and implement the run() method.
"""

import asyncio
from typing import Dict, Tuple, AsyncIterator, Optional, List, Sequence
from models.color import Color
from models.domain.zone import ZoneCombined
from models.enums import ZoneID


class BaseAnimation:
    """
    Base class for all LED animations

    Animations are async generators that yield frames
    to update LED colors frame by frame.

    IMPORTANT:
    - One instance of animation = ONE ZONE.
    - Multi-zone animations are handled by AnimationEngine by spawning
      multiple animation instances.

    Subclasses MUST implement async def step(self) which returns either:
        SingleZoneFrame    (zone-level color)
        PixelFrameV2       (pixel-level override)
    """

    def __init__(
        self, 
        zone: ZoneCombined, 
        speed: int = 50, 
        **params
    ):
        # Every animation instance works on only ONE zone
        self.zone = zone
        self.zone_id: ZoneID = zone.config.id
        self.speed = max(1, min(100, speed))
        self.running = False
        
        # These parameters come directly from ZoneState.animation_state
        self.params = params
        
        # Convenience cache for color/brightness
        self.base_color: Color = zone.state.color
        self.base_brightness: int = zone.brightness 

    # ------------------------------------------------------------
    # Main generator loop used by AnimationEngine
    # ------------------------------------------------------------
    async def run(self) -> AsyncIterator["BaseFrameV2"]:
        """
        Every animation runs in its own task created by AnimationEngine.
        Produces frames indefinitely until stop() is called.
        """
        self.running = True

        while self.running:
            frame = await self.step()
            if frame is not None:
                yield frame

            await asyncio.sleep(self._frame_delay())
          
    # ------------------------------------------------------------
    # To be implemented by subclasses
    # ------------------------------------------------------------
    async def step(self):
        raise NotImplementedError
      
    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def stop(self):
        self.running = False

    def update_param(self, param: str, value):
        """Live parameter update"""
        self.params[param] = value
      
    def _frame_delay(self) -> float:
        """
        Calculate delay based on speed.
        Speed 100 ←→ 50 FPS
        Speed 1   ←→ 10 FPS
        """
        min_delay = 0.02  # 50 FPS
        max_delay = 0.1   # 10 FPS
        return max_delay - (self.speed / 100) * (max_delay - min_delay)
    
    def set_base_color(self, color: Color):
        """Cache zone color for animations that need current colors"""
        self.base_color = color

    def set_base_brightness(self, brightness: int):
        """Cache zone brightness for animations that need current brightness"""
        self.base_brightness = brightness

    def get_base_color(self) -> Optional[Color]:
        """Get cached Color object for zone"""
        return self.base_color

    def get_base_brightness(self) -> Optional[int]:
        """Get cached brightness for zone"""
        return self.base_brightness

    # async def run_preview(self, pixel_count: int = 8) -> AsyncIterator[Sequence[Color]]:
    #     """
    #     Generate simplified preview frames for preview panel (8 pixels)

    #     Override this in subclasses to provide custom preview visualization.
    #     Default implementation shows static color.

    #     Args:
    #         pixel_count: Number of preview pixels (default: 8)

    #     Yields:
    #         List of (r, g, b) tuples, one per pixel

    #     Example:
    #         async for frame in animation.run_preview(8):
    #             preview_panel.show_frame(frame)
    #     """
    #     self.running = True
    #     # Default: show static color
    #     static_color = Color.from_rgb(100, 100, 100)
    #     frame = [static_color] * pixel_count

    #     while self.running:
    #         yield frame
    #         await asyncio.sleep(self._calculate_frame_delay())
