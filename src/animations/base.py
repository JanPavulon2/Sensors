"""
Base Animation Class

All animations inherit from BaseAnimation and implement the run() method.
"""

import asyncio
from typing import Dict, AsyncIterator, Optional, TYPE_CHECKING
from models.animation_params.animation_param import AnimationParam
from models.animation_params.animation_param_id import AnimationParamID
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
    PARAMS: Dict[AnimationParamID, AnimationParam] = {}
    
    def __init__(
        self, 
        zone: ZoneCombined, 
        params: Dict[AnimationParamID, object]
    ):
        # Every animation instance works on only ONE zone
        self.zone = zone
        self.zone_id: ZoneID = zone.config.id
        
        self.params: Dict[AnimationParamID, object] = params.copy()
        
        self.running = False
        
    # ------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------

    async def step(self):
        raise NotImplementedError

    def stop(self):
        self.running = False
        
        
    # ------------------------------------------------------------
    # Parameter helpers
    # ------------------------------------------------------------

    def get_param(self, param_id: AnimationParamID, default=None):
        return self.params.get(param_id, default)

    def set_param(self, param_id: AnimationParamID, value):
        if param_id in self.PARAMS:
            self.params[param_id] = value
            
    # ------------------------------------------------------------
    # Zone context helpers (NOT animation params)
    # ------------------------------------------------------------

    @property
    def base_color(self):
        return self.zone.state.color

    @property
    def base_brightness(self):
        return self.zone.brightness

    @property
    def pixel_count(self) -> int:
        return self.zone.config.pixel_count
    
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
     