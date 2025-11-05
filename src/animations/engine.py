"""
Animation Engine

Manages animation lifecycle, switching between animations, and updating strip.
Uses TransitionService for smooth transitions between animation states.
"""

import asyncio
from typing import Optional, Dict, List, Any, Type

from animations.base import BaseAnimation  # ✅ direct import — breaks circular import safely

# Import animation classes here (NOT in __init__ to avoid circular imports)
from animations.breathe import BreatheAnimation
from animations.color_fade import ColorFadeAnimation
from animations.snake import SnakeAnimation
from animations.color_snake import ColorSnakeAnimation
from animations.color_cycle import ColorCycleAnimation

from models.domain.zone import ZoneCombined
from services.transition_service import TransitionService
from services import AnimationService
from models.transition import TransitionConfig, TransitionType
from models.enums import ParamID, LogCategory
from utils.logger import get_category_logger
from models.enums import LogCategory, AnimationID
from components import ZoneStrip

log = get_category_logger(LogCategory.ANIMATION)

def _build_animation_registry() -> Dict[AnimationID, Type[BaseAnimation]]:
    """Build animation registry dynamically from AnimationID enum"""
    class_map = {
        AnimationID.COLOR_CYCLE: ColorCycleAnimation,
        AnimationID.BREATHE: BreatheAnimation,
        AnimationID.COLOR_FADE: ColorFadeAnimation,
        AnimationID.SNAKE: SnakeAnimation,
        AnimationID.COLOR_SNAKE: ColorSnakeAnimation,
        # AnimationID.MATRIX: MatrixAnimation,  # TEMPORARY: Disabled
    }

    # Convert enum to string keys using .name
    return {anim_id: anim_class for anim_id, anim_class in class_map.items()}

class AnimationEngine:
    """
    Animation engine that manages running animations

    Handles:
    - Starting/stopping animations
    - Switching between animations
    - Updating LED strip with animation frames
    - Parameter updates

    Example:
        engine = AnimationEngine(strip, zones)
        await engine.start('BREATHE', speed=50, color=(255, 0, 0))
        await asyncio.sleep(5)
        await engine.stop()
    """

    # Registry of available animations - built dynamically from enum
    ANIMATIONS: Dict[AnimationID, Type[BaseAnimation]] = _build_animation_registry()

    def __init__(self, strip, zones: List[ZoneCombined]):
        """
        Initialize animation engine

        Args:
            strip: ZoneStrip instance
            zones: List of Zone objects
        """
        self.strip: ZoneStrip = strip
        self.zones = zones
        self.current_animation: Optional[BaseAnimation] = None
        self.animation_task: Optional[asyncio.Task] = None
        self.current_id: Optional[AnimationID] = None

        # Transition service for smooth animation switches
        self.transition_service = TransitionService(strip)
        # self.animation_service = AnimationService()
        log.info("AnimationEngine initialized", animations=list(self.ANIMATIONS.keys()))

    async def start(
        self,
        animation_id: AnimationID,
        excluded_zones: Optional[List] = None,
        transition: Optional[TransitionConfig] = None,
        **params
    ):
        """
        Start an animation by animation ID with optional transition

        Args:
            name: Animation ID ('BREATHE', 'COLOR_FADE', 'SNAKE')
            excluded_zones: List of zone names to exclude from animation (e.g., ["lamp"])
            transition: Transition configuration for switching (defaults to ANIMATION_SWITCH)
            **params: Animation-specific parameters (speed, color, etc.)

        Raises:
            ValueError: If animation name is not recognized

        Example:
            # Start with default fade transition
            await engine.start('breathe', speed=50)
            
            # Start with instant switch
            await engine.start('snake', transition=TransitionConfig(TransitionType.NONE))
        """
        log.info(f"AnimEngine.start(): {animation_id}")

        # If animation is running, apply transition and stop
        if self.is_running():
            log.info(f"AnimEngine: Stopping current animation first")
            transition = transition or self.transition_service.ANIMATION_SWITCH
            await self.stop(transition)
        else:
            # No animation running, just stop (no transition needed)
            log.info(f"AnimEngine: No animation running, calling stop with NONE transition")
            await self.stop(TransitionConfig(type=TransitionType.NONE) if transition is None else transition)

        # Create new animation instance
        log.info(f"AnimEngine: Creating animation instance: {animation_id}")
        if animation_id not in self.ANIMATIONS.keys():
            raise ValueError(f"Unknown animation: {animation_id}. Available: {list(self.ANIMATIONS.keys())}")

        animation_class = self.ANIMATIONS[animation_id]
        if not animation_class:
            raise ValueError(f"Unknown animation: {animation_id}")
        
        log.debug(f"Creating animation instance: {animation_id.name}")
        self.current_animation = animation_class(
            self.zones,
            excluded_zones=excluded_zones or [],
            **params,
        )
        self.current_id = animation_id

        log.info(f"AnimEngine: Caching zone colors")
        # Cache current zone colors for animations that need them
        # Note: Brightness is cached by LEDController (has actual 0-100% values)
        for zone in self.zones:
            color = self.strip.get_zone_color(zone.config.id.name)
            if color and self.current_animation:
                self.current_animation.set_zone_color_cache(zone.config.id, *color)

        # Start animation loop
        log.info(f"AnimEngine: Starting animation loop task")
        self.animation_task = asyncio.create_task(self._run_loop())

        log.info(f"AnimEngine: Started {animation_id} | params:{params}")
        
    async def stop(self, transition: Optional[TransitionConfig] = None):
        if not self.is_running() or not self.current_animation:
            return

        transition = transition or self.transition_service.ANIMATION_SWITCH

        await self.transition_service.fade_out(transition)

        self.current_animation.stop()

        if self.animation_task:
            self.animation_task.cancel()
            try:
                await self.animation_task
            except asyncio.CancelledError:
                pass
            self.animation_task = None

        log.debug(f"AnimEngine: stopped {self.current_id.name if self.current_id else '?'}")
        self.current_animation = None
        self.current_id = None
        self.animation_task = None
        
    
    # ------------------------------------------------------------------
    # RUNTIME HELPERS
    # ------------------------------------------------------------------

    def update_param(self, param: str, value):
        """
        Update parameter of running animation

        Args:
            param: Parameter name ('speed', 'color', etc.)
            value: New value
        """
        if self.current_animation:
            self.current_animation.update_param(param, value)

    def is_running(self) -> bool:
        """Check if animation is currently running"""
        return self.animation_task is not None and not self.animation_task.done()

    def get_current_animation_id(self) -> Optional[AnimationID]:
        """Get name of currently running animation"""
        return self.current_id if self.is_running() else None

    def get_current_animation(self) -> Optional['BaseAnimation']:
        """Get name of currently running animation"""
        return self.current_animation if self.is_running() else None

    
    # ------------------------------------------------------------------
    # INTERNAL LOOP
    # ------------------------------------------------------------------

    async def _run_loop(self):
        """Main loop — consumes frames from the running animation"""
        assert self.current_animation is not None

        try:
            async for frame in self.current_animation.run():
                if len(frame) == 5:
                    zone_id, pixel_index, r, g, b = frame
                    log.info(
                        f"Setting pixel: {zone_id.name} (value={zone_id.value}) index={pixel_index} rgb=({r},{g},{b})"
                    )
                    self.strip.set_pixel_color(zone_id.name, pixel_index, r, g, b)
                elif len(frame) == 4:
                    zone_id, r, g, b = frame
                    log.info(f"Setting zone: {zone_id.name} rgb=({r},{g},{b})")
                    self.strip.set_zone_color(zone_id.name, r, g, b)

                log.info(f"Yield frame: for {zone_id}:  {frame}")


                # ✅ flush each frame for now (you can optimize later)
                self.strip.show()

        except asyncio.CancelledError:
            log.debug("Animation loop cancelled gracefully")
        except Exception as e:
            log.error(f"Animation error: {e}", animation=self.current_id)
            raise
    
    # async def _run_loop(self):
    #     """
    #     Main animation loop

    #     Consumes frames from current animation and updates strip.
    #     Supports both zone-level and pixel-level updates.
    #     """
        
    #     assert self.current_animation is not None
            
    #     try:
    #         async for frame_data in self.current_animation.run():
    #             # Check frame type by tuple length
    #             # 4-tuple: (zone_name, r, g, b) -> zone-level
    #             # 5-tuple: (zone_name, pixel_index, r, g, b) -> pixel-level
    #             if len(frame_data) == 5:
    #                 zone_id, pixel_index, r, g, b = frame_data
    #                 self.strip.set_pixel_color(zone_id, pixel_index, r, g, b)
    #             else:  # len == 4
    #                 zone_id, r, g, b = frame_data
    #                 self.strip.set_zone_color(zone_id, r, g, b)
                    
    #             log.info(f"Yield frame: for {zone_id}:  {frame_data}")


    #     except asyncio.CancelledError:
    #         # Animation was stopped gracefully
    #         log.debug("Animation loop cancelled")
    #     except Exception as e:
    #         log.error(f"Animation error: {e}", animation=self.current_id)
    #         raise
        
    def convert_params(self, params: dict) -> dict:
        """
        Convert parameter dictionary keys (possibly enums) to string names.

        Ensures **kwargs passed into animation constructors use string keys,
        since Python requires keyword argument names to be str.

        Example:
            {ParamID.ANIM_SPEED: 50, ParamID.ANIM_INTENSITY: 80}
            → {"ANIM_SPEED": 50, "ANIM_INTENSITY": 80}
        """
        if not params:
            return {}

        safe_params = {}
        for k, v in params.items():
            if hasattr(k, "name"):
                safe_params[k.name] = v
            elif isinstance(k, str):
                safe_params[k] = v
            else:
                safe_params[str(k)] = v
        return safe_params