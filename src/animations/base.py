"""
Base Animation Class

All animations inherit from BaseAnimation and implement the run() method.
"""

import asyncio
from typing import Dict, Tuple, AsyncIterator, Optional, List, Sequence, TYPE_CHECKING
from models.color import Color
from models.domain.zone import ZoneCombined
from models.enums import ZoneID

if TYPE_CHECKING:
    from models.frame import BaseFrame
    
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
        PixelFrame       (pixel-level override)
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
    async def run(self) -> AsyncIterator["BaseFrame"]:
        """
        Every animation runs in its own task created by AnimationEngine.
        Produces frames indefinitely until stop() is called.
        """
        self.running = True

        while self.running:
            frame = await self.step()
            if frame is not None:
                yield frame
          
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