"""
Animation Engine

Manages animation lifecycle, switching between animations, and updating strip.
"""

import asyncio
from typing import Optional, Dict
from animations.base import BaseAnimation
from animations.breathe import BreatheAnimation
from animations.color_fade import ColorFadeAnimation
from animations.snake import SnakeAnimation


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
        'breathe': BreatheAnimation,
        'color_fade': ColorFadeAnimation,
        'snake': SnakeAnimation,
    }

    def __init__(self, strip, zones: Dict[str, list]):
        """
        Initialize animation engine

        Args:
            strip: ZoneStrip instance
            zones: Dict of zone definitions {name: [start, end]}
        """
        self.strip = strip
        self.zones = zones
        self.current_animation: Optional[BaseAnimation] = None
        self.animation_task: Optional[asyncio.Task] = None
        self.current_name: Optional[str] = None

    async def start(self, name: str, excluded_zones=None, **params):
        """
        Start an animation by name

        Args:
            name: Animation name ('breathe', 'color_fade', 'snake')
            excluded_zones: List of zone names to exclude from animation (e.g., ["lamp"])
            **params: Animation-specific parameters (speed, color, etc.)

        Raises:
            ValueError: If animation name is not recognized
        """
        # Stop current animation if running
        await self.stop()

        # Create new animation instance
        if name not in self.ANIMATIONS:
            raise ValueError(f"Unknown animation: {name}. Available: {list(self.ANIMATIONS.keys())}")

        animation_class = self.ANIMATIONS[name]
        self.current_animation = animation_class(self.zones, excluded_zones=excluded_zones or [], **params)
        self.current_name = name

        # Cache current zone colors/brightness for animations that need them
        # We need to get brightness from LEDController, not from strip
        # For now, cache the RGB values and extract brightness
        for zone_name in self.zones:
            color = self.strip.get_zone_color(zone_name)
            if color:
                self.current_animation.set_zone_color_cache(zone_name, *color)
                # Calculate brightness from RGB (approximate as max channel)
                brightness = max(color)
                self.current_animation.set_zone_brightness_cache(zone_name, brightness)

        # Start animation loop
        self.animation_task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop current animation and restore static colors"""
        if self.current_animation:
            self.current_animation.stop()

        if self.animation_task:
            self.animation_task.cancel()
            try:
                await self.animation_task
            except asyncio.CancelledError:
                pass
            self.animation_task = None

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
            # Animation was stopped
            pass
        except Exception as e:
            print(f"[!] Animation error: {e}")
            raise
