"""
Animation Engine

Manages animation lifecycle, switching between animations, and updating strip.
Uses TransitionService for smooth transitions between animation states.
"""

import asyncio
from typing import Optional, Dict, List
from animations.base import BaseAnimation
from animations.breathe import BreatheAnimation
from animations.color_fade import ColorFadeAnimation
from animations.snake import SnakeAnimation
from animations.color_snake import ColorSnakeAnimation
from animations.color_cycle import ColorCycleAnimation
from animations.matrix import MatrixAnimation
from models.domain.zone import ZoneCombined
from services.transition_service import TransitionService
from models.transition import TransitionConfig, TransitionType
from utils.logger import get_category_logger
from models.enums import LogCategory

log = get_category_logger(LogCategory.ANIMATION)

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
        await engine.start('breathe', speed=50, color=(255, 0, 0))
        await asyncio.sleep(5)
        await engine.stop()
    """

    # Registry of available animations
    ANIMATIONS = {
        'color_cycle': ColorCycleAnimation,
        'breathe': BreatheAnimation,
        'color_fade': ColorFadeAnimation,
        'snake': SnakeAnimation,
        'color_snake': ColorSnakeAnimation
        # 'matrix': MatrixAnimation,  # TEMPORARY: Disabled for testing
    }

    def __init__(self, strip, zones: List[ZoneCombined]):
        """
        Initialize animation engine

        Args:
            strip: ZoneStrip instance
            zones: List of Zone objects
        """
        self.strip = strip
        self.zones = zones
        self.current_animation: Optional[BaseAnimation] = None
        self.animation_task: Optional[asyncio.Task] = None
        self.current_name: Optional[str] = None

        # Transition service for smooth animation switches
        self.transition_service = TransitionService(strip)

        log.info("AnimationEngine initialized", animations=list(self.ANIMATIONS.keys()))

    async def start(
        self,
        name: str,
        excluded_zones=None,
        transition: Optional[TransitionConfig] = None,
        **params
    ):
        """
        Start an animation by name with optional transition

        Args:
            name: Animation name ('breathe', 'color_fade', 'snake')
            excluded_zones: List of zone names to exclude from animation (e.g., ["lamp"])
            transition: Transition configuration for switching (defaults to ANIMATION_SWITCH)
            **params: Animation-specific parameters (speed, color, etc.)

        Raises:
            ValueError: If animation name is not recognized

        Example:
            >>> # Start with default fade transition
            >>> await engine.start('breathe', speed=50)
            >>>
            >>> # Start with instant switch
            >>> await engine.start('snake', transition=TransitionConfig(TransitionType.NONE))
        """
        # If animation is running, apply transition and stop
        if self.is_running():
            transition = transition or self.transition_service.ANIMATION_SWITCH
            await self.stop(transition)
        else:
            # No animation running, just stop (no transition needed)
            await self.stop(TransitionConfig(type=TransitionType.NONE) if transition is None else transition)

        # Create new animation instance
        if name not in self.ANIMATIONS:
            raise ValueError(f"Unknown animation: {name}. Available: {list(self.ANIMATIONS.keys())}")

        animation_class = self.ANIMATIONS[name]
        self.current_animation = animation_class(self.zones, excluded_zones=excluded_zones or [], **params)
        self.current_name = name
        
        # Cache current zone colors for animations that need them
        # Note: Brightness is cached by LEDController (has actual 0-100% values)
        for zone in self.zones:
            color = self.strip.get_zone_color(zone.config.tag)
            if color and self.current_animation is not None:
                self.current_animation.set_zone_color_cache(zone.config.tag, *color)

        # Start animation loop
        self.animation_task = asyncio.create_task(self._run_loop())

        log.debug(f"AnimEngine: started {name} | params:{params}")
        
    async def stop(self, transition: Optional[TransitionConfig] = None):
        """
        Stop current animation with optional transition

        Args:
            transition: Transition configuration (defaults to ANIMATION_SWITCH preset)

        Example:
            >>> # Stop with fade
            >>> await engine.stop(TransitionService.ANIMATION_SWITCH)
            >>>
            >>> # Stop instantly
            >>> await engine.stop(TransitionConfig(TransitionType.NONE))
        """
        if not self.is_running():
            return

        transition = transition or self.transition_service.ANIMATION_SWITCH

        # Apply transition (fade out)
        await self.transition_service.fade_out(transition)

        # Stop animation task
        if self.current_animation:
            self.current_animation.stop()

        if self.animation_task:
            self.animation_task.cancel()
            try:
                await self.animation_task
            except asyncio.CancelledError:
                pass
            self.animation_task = None

        log.debug(f"AnimEngine: stopped {self.current_name}")
        
        self.current_animation = None
        self.current_name = None



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

    def get_current_animation(self) -> Optional[str]:
        """Get name of currently running animation"""
        return self.current_name if self.is_running() else None

    async def _run_loop(self):
        """
        Main animation loop

        Consumes frames from current animation and updates strip.
        Supports both zone-level and pixel-level updates.
        """
        try:
            assert self.current_animation is not None
            async for frame_data in self.current_animation.run():
                # Check frame type by tuple length
                # 4-tuple: (zone_name, r, g, b) -> zone-level
                # 5-tuple: (zone_name, pixel_index, r, g, b) -> pixel-level
                if len(frame_data) == 5:
                    zone_name, pixel_index, r, g, b = frame_data
                    self.strip.set_pixel_color(zone_name, pixel_index, r, g, b)
                else:  # len == 4
                    zone_name, r, g, b = frame_data
                    self.strip.set_zone_color(zone_name, r, g, b)

        except asyncio.CancelledError:
            # Animation was stopped gracefully
            log.debug("Animation loop cancelled")
        except Exception as e:
            log.error(f"Animation error: {e}", animation=self.current_name)
            raise