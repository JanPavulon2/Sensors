"""
Base Animation Class

All animations inherit from BaseAnimation and implement the run() method.
"""

from typing import Dict, AsyncIterator, Optional, Any, TYPE_CHECKING

from models.animation_params import AnimationParamID, AnimationParam
from models.domain import ZoneCombined
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

    ARCHITECTURE INVARIANTS:
    - PARAMS: class-level dict of parameter definitions (metadata only)
    - params: instance-level dict of parameter values (runtime state)
    - Use get_param() to read values with fallback to defaults
    - Use set_param() or adjust_param() to modify values
    - Parameter definitions are stateless - they provide adjust/clamp logic
    """
    PARAMS: Dict[AnimationParamID, AnimationParam] = {}  # Parameter definitions (class-level)

    def __init__(
        self,
        zone: ZoneCombined,
        params: Dict[AnimationParamID, Any]
    ):
        # Every animation instance works on only ONE zone
        self.zone = zone
        self.zone_id: ZoneID = zone.config.id

        self.params: Dict[AnimationParamID, Any] = params.copy()  # Parameter values (instance-level)
        
        self.running = False
        
    # ------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------

    async def step(self):
        raise NotImplementedError

    def stop(self):
        self.running = False
        
        
    # ============================================================
    # Parameter helpers
    # ============================================================
    # Parameters store raw values (int/float/str/bool).
    # Parameter definitions (PARAMS) provide defaults and constraints.
    # ============================================================

    def get_param(self, param_id: AnimationParamID, default: Any = None) -> Any:
        """
        Get parameter value from instance storage.

        Falls back to:
        1. param_id in self.params → return value
        2. param_id in PARAMS → return param_def.default
        3. otherwise → return provided default
        """
        if param_id in self.params:
            return self.params[param_id]

        param_def = self.PARAMS.get(param_id)
        if param_def is not None:
            return param_def.default

        return default

    def set_param(self, param_id: AnimationParamID, value: Any) -> None:
        """Set parameter value directly (must be supported by PARAMS)"""
        if param_id in self.PARAMS:
            self.params[param_id] = value

    def adjust_param(self, param_id: AnimationParamID, delta: int) -> Optional[Any]:
        """Adjust parameter by delta, return adjusted value or None"""
        param_def = self.PARAMS.get(param_id)
        if not param_def:
            return None

        current_value = self.get_param(param_id, param_def.default)
        new_value = param_def.adjust(current_value, delta)

        self.params[param_id] = new_value
        return new_value
    
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
     