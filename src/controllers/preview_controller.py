"""
Preview Controller

Orchestrates preview preview_panel display modes and animation playback.
Uses adapter pattern to run real animation classes with virtual zones.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List, TYPE_CHECKING
from components.preview_panel import PreviewPanel
from utils.logger import get_logger, LogLevel, LogCategory
from models import Color, ParamID
from models.enums import ZoneID
from models.domain.parameter import ParameterCombined, ParameterConfig, ParameterState

if TYPE_CHECKING:
    from animations.base import BaseAnimation


@dataclass
class VirtualZoneConfig:
    """Minimal zone config for preview panel virtual zones"""
    tag: str  # "p0", "p1", etc.
    start_index: int
    end_index: int


@dataclass
class VirtualZone:
    """
    Lightweight zone wrapper for preview animations

    Mimics ZoneCombined structure but uses simple VirtualZoneConfig
    that allows custom tags ("p0", "p1", etc.)
    """
    config: VirtualZoneConfig
    state: Any = None  # Not used
    parameters: Dict = None  # Not used

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

log = get_logger()


class PreviewController:
    """
    Preview preview_panel orchestration controller

    Manages preview display modes and delegates to PreviewPanel for rendering.
    Uses real Animation classes with virtual zones for animation previews.

    Architecture:
        - Converts 8 LEDs into 8 virtual "zones" (1 LED each)
        - Instantiates real animation classes (SnakeAnimation, BreatheAnimation, etc.)
        - Translates animation frames (zone_tag → LED index)
        - Displays frames using PreviewPanel.show_frame()

    Responsibilities:
        - Display mode management (color, bar, animation)
        - Animation lifecycle (start/stop async tasks)
        - Frame translation (animation zones → preview LEDs)
        - Parameter updates (speed, color changes)

    Args:
        preview_panel: PreviewPanel instance for hardware control

    Example:
        >>> controller = PreviewController(preview_panel)
        >>> controller.show_color((255, 0, 0), 50)  # Red at 50% brightness
        >>> controller.start_animation_preview('snake', speed=60, color=(0, 255, 0))
        >>> controller.update_param('speed', 80)  # Live speed change
        >>> controller.stop_animation_preview()
    """

    def __init__(self, preview_panel: PreviewPanel):
        self.preview_panel = preview_panel
        self._animation_task: Optional[asyncio.Task] = None
        self._current_animation: Optional['BaseAnimation'] = None
        self._animation_running = False
        self._current_animation_id: Optional[str] = None  # Track which animation is running

    # ===== STATIC DISPLAY METHODS =====

    
    def fill_with_color(self, color: Color) -> None:
        if self._animation_running:
            self.stop_animation_preview()
        
        r, g, b = color.to_rgb()
        self.preview_panel.fill_with_color((r, g, b))
        
    def show_color(self, rgb: Tuple[int, int, int], brightness: int = 100) -> None:
        """
        Show static color on all 8 LEDs with brightness scaling

        Stops any running animation before displaying.

        Args:
            rgb: RGB tuple (0-255 values)
            brightness: Brightness percentage (0-100)

        Example:
            >>> controller.show_color((255, 100, 50), 75)  # Orange at 75%
        """
        self.stop_animation_preview()
        
        # Apply brightness scaling
        r, g, b = [int(c * brightness / 100) for c in rgb]
        self.preview_panel.fill_with_color((r, g, b))

    def show_bar(self, value: int, max_value: int = 100,
                 color: Tuple[int, int, int] = (255, 255, 255)) -> None:
        """
        Show bar indicator (0-8 LEDs lit proportionally to value)

        Stops any running animation before displaying.

        Args:
            value: Current value
            max_value: Maximum value for normalization
            color: RGB color for lit LEDs

        Example:
            >>> controller.show_bar(60, 100, (0, 255, 0))  # 5 LEDs green (60%)
        """
        self.stop_animation_preview()
        self.preview_panel.show_bar(value, max_value, color)

    # ===== ANIMATION PREVIEW METHODS =====

    def _create_virtual_zones(self) -> List[VirtualZone]:
        """
        Create 8 virtual zones for preview panel (1 LED per zone)

        This allows reusing real Animation classes by treating each preview LED
        as a separate "zone". Animations think they're controlling zones,
        but we're actually controlling individual LEDs.

        Returns:
            List of 8 VirtualZone objects with tags "p0"-"p7"
        """
        zones = []
        for i in range(self.preview_panel.count):
            # Create lightweight virtual zone config
            # Each virtual zone is 1 pixel with tag "p0", "p1", etc.
            virtual_config = VirtualZoneConfig(
                tag=f"p{i}",  # Virtual zone tag for animation frame lookup
                start_index=i,
                end_index=i  # start == end for 1-pixel zones
            )

            # Create VirtualZone wrapper (animations only need config.tag and indices)
            virtual_zone = VirtualZone(config=virtual_config)
            zones.append(virtual_zone)

        return zones

    def _create_animation_instance(
        self,
        animation_id: str,
        speed: int,
        **params
    ) -> Optional['BaseAnimation']:
        """
        Factory method to create animation instances for preview

        Creates animation without zones - preview uses run_preview() method.

        Args:
            animation_id: Animation identifier ('snake', 'breathe', etc.)
            speed: Animation speed (1-100)
            **params: Additional animation-specific parameters

        Returns:
            Animation instance or None if animation_id is unknown
        """
        # Import animation classes
        from animations.snake import SnakeAnimation
        from animations.breathe import BreatheAnimation
        from animations.color_fade import ColorFadeAnimation
        from animations.color_snake import ColorSnakeAnimation

        # Create minimal empty zone list (animations need it for __init__ but won't use it in preview)
        empty_zones = []

        # Animation factory mapping
        if animation_id == "snake":
            return SnakeAnimation(
                zones=empty_zones,
                speed=speed,
                hue=params.get('hue', 0),
                length=params.get('length', 1),
                color=params.get('color')  # Backwards compat
            )

        elif animation_id == "breathe":
            return BreatheAnimation(
                zones=empty_zones,
                speed=speed,
                color=params.get('color', (255, 0, 0)),
                intensity=params.get('intensity', 100)
            )

        elif animation_id == "color_fade":
            return ColorFadeAnimation(
                zones=empty_zones,
                speed=speed,
                start_hue=params.get('start_hue', 0)
            )

        elif animation_id == "color_snake":
            return ColorSnakeAnimation(
                zones=empty_zones,
                speed=speed,
                hue=params.get('hue', 0),
                length=params.get('length', 5),
                hue_offset=params.get('hue_offset', 30)
            )

        else:
            # Unknown animation
            return None

    def start_animation_preview(self, animation_id: str, speed: int = 50, **params) -> None:
        """
        Start animation preview using animation's run_preview() method

        Instantiates the animation class and runs its simplified preview visualization
        designed for 8 pixels.

        Args:
            animation_id: Animation name ('snake', 'breathe', 'color_fade', 'color_snake')
            speed: Animation speed (1-100)
            **params: Additional animation parameters (color, intensity, start_hue, etc.)

        Example:
            >>> controller.start_animation_preview('snake', speed=70, hue=120, length=3)
            >>> controller.start_animation_preview('breathe', speed=50, intensity=80)
        """
        # If same animation is already running, don't restart (prevents flicker)
        if self._animation_running and self._current_animation_id == animation_id:
            # Just update parameters if needed
            if self._current_animation:
                self._current_animation.speed = speed
                for key, value in params.items():
                    self._current_animation.update_param(key, value)
            return

        self.stop_animation_preview()
        self._current_animation_id = animation_id

        # Instantiate animation (no zones needed - preview mode uses simplified logic)
        try:
            self._current_animation = self._create_animation_instance(
                animation_id, speed, **params
            )

            if not self._current_animation:
                log.log(LogCategory.SYSTEM, "Unknown animation for preview",
                       level=LogLevel.WARN, animation_id=animation_id)
                # Fallback: show static color
                self.show_color((50, 50, 50))
                return

            # Start animation task
            self._animation_running = True
            self._animation_task = asyncio.create_task(self._run_preview_loop())

            log.log(LogCategory.SYSTEM, "Preview animation started",
                   animation_id=animation_id, speed=speed)

        except Exception as e:
            log.log(LogCategory.SYSTEM, "Failed to start preview animation",
                   level=LogLevel.ERROR, error=str(e), animation_id=animation_id)
            self.preview_panel.clear()

    def stop_animation_preview(self) -> None:
        """
        Stop currently running animation preview

        Cancels async task, stops animation, and clears preview preview_panel.
        Safe to call even if no animation is running.
        """
        self._animation_running = False

        if self._current_animation:
            self._current_animation.stop()
            self._current_animation = None

        if self._animation_task:
            self._animation_task.cancel()
            self._animation_task = None

        self.preview_panel.clear()

    def update_param(self, param: str, value: Any) -> None:
        """
        Update parameter of running animation (live update)

        Allows changing animation parameters (speed, intensity, color) without
        restarting the animation.

        Args:
            param: Parameter name ('speed', 'intensity', 'color', etc.)
            value: New parameter value

        Example:
            >>> controller.update_param('speed', 80)  # Speed up animation
            >>> controller.update_param('intensity', 60)  # Reduce breathe depth
        """
        if self._current_animation:
            self._current_animation.update_param(param, value)
            log.log(LogCategory.SYSTEM, "Preview animation parameter updated",
                   param=param, value=value)

    async def _run_preview_loop(self) -> None:
        """
        Run animation preview loop - uses animation's run_preview() method

        Each animation provides its own simplified preview visualization for 8 pixels.
        Frames are directly displayed on the preview panel.
        """
        if not self._current_animation:
            return

        try:
            self._current_animation.running = True

            async for frame in self._current_animation.run_preview(pixel_count=self.preview_panel.count):
                if not self._animation_running:
                    break

                # Display frame directly (already in correct format)
                self.preview_panel.show_frame(frame)

        except asyncio.CancelledError:
            # Animation stopped gracefully
            pass
        except Exception as e:
            log.log(LogCategory.SYSTEM, "Preview animation error",
                   level=LogLevel.ERROR, error=str(e))
        finally:
            self._current_animation = None
            if self._animation_running:  # Only clear if not already cleared by stop()
                self.preview_panel.clear()
