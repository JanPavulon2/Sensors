"""
Preview Controller

Orchestrates preview panel display modes and animation playback.
Uses adapter pattern to run real animation classes with virtual zones.
"""

import asyncio
from typing import Optional, Tuple, Dict, Any, List, TYPE_CHECKING
from components.preview_panel import PreviewPanel
from utils.logger import get_logger, LogLevel, LogCategory

if TYPE_CHECKING:
    from models.zone import Zone
    from animations.base import BaseAnimation

log = get_logger()


class PreviewController:
    """
    Preview panel orchestration controller

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
        panel: PreviewPanel instance for hardware control

    Example:
        >>> controller = PreviewController(preview_panel)
        >>> controller.show_color((255, 0, 0), 50)  # Red at 50% brightness
        >>> controller.start_animation_preview('snake', speed=60, color=(0, 255, 0))
        >>> controller.update_param('speed', 80)  # Live speed change
        >>> controller.stop_animation_preview()
    """

    def __init__(self, panel: PreviewPanel):
        self.panel = panel
        self._animation_task: Optional[asyncio.Task] = None
        self._current_animation: Optional['BaseAnimation'] = None
        self._running = False

    # ===== STATIC DISPLAY METHODS =====

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
        self.panel.show_color((r, g, b))

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
        self.panel.show_bar(value, max_value, color)

    # ===== ANIMATION PREVIEW METHODS =====

    def _create_virtual_zones(self) -> List['Zone']:
        """
        Create 8 virtual zones for preview panel (1 LED per zone)

        This allows reusing real Animation classes by treating each preview LED
        as a separate "zone". Animations think they're controlling zones,
        but we're actually controlling individual LEDs.

        Returns:
            List of 8 Zone objects (p0-p7)
        """
        from models.zone import Zone

        zones = []
        for i in range(self.panel.count):
            zone = Zone(
                name=f"Preview {i}",
                tag=f"p{i}",
                pixel_count=1,
                enabled=True,
                order=i
            )
            # Set indices manually (start == end for 1 LED zones)
            zone.start_index = i
            zone.end_index = i
            zones.append(zone)
        return zones

    def start_animation_preview(self, animation_id: str, speed: int = 50, **params) -> None:
        """
        Start animation preview using real Animation class with virtual zones

        Creates virtual zones (8 LEDs as zones), instantiates the actual animation
        class, and runs it in an async task. Frames are translated from zone updates
        to LED indices.

        Args:
            animation_id: Animation name ('snake', 'breathe', 'color_fade', 'color_snake')
            speed: Animation speed (1-100)
            **params: Additional animation parameters (color, intensity, start_hue, etc.)

        Example:
            >>> controller.start_animation_preview('snake', speed=70, color=(255, 0, 0))
            >>> controller.start_animation_preview('breathe', speed=50, intensity=80)
        """
        self.stop_animation_preview()

        # Create virtual zones (8 LEDs as individual zones)
        virtual_zones = self._create_virtual_zones()

        # Import animation classes
        from animations.snake import SnakeAnimation
        from animations.breathe import BreatheAnimation
        from animations.color_fade import ColorFadeAnimation
        from animations.color_snake import ColorSnakeAnimation

        # Instantiate real animation with virtual zones
        try:
            if animation_id == "snake":
                self._current_animation = SnakeAnimation(
                    zones=virtual_zones,
                    speed=speed,
                    color=params.get('color', (255, 255, 255)),
                    excluded_zones=[]
                )
            elif animation_id == "breathe":
                self._current_animation = BreatheAnimation(
                    zones=virtual_zones,
                    speed=speed,
                    color=params.get('color', (255, 0, 0)),
                    intensity=params.get('intensity', 100)
                )
            elif animation_id == "color_fade":
                self._current_animation = ColorFadeAnimation(
                    zones=virtual_zones,
                    speed=speed,
                    start_hue=params.get('start_hue', 0)
                )
            elif animation_id == "color_snake":
                self._current_animation = ColorSnakeAnimation(
                    zones=virtual_zones,
                    speed=speed
                )
            else:
                log.log(LogCategory.SYSTEM, "Unknown animation for preview",
                       level=LogLevel.WARN, animation_id=animation_id)
                # Fallback: show static color
                self.show_color((50, 50, 50))
                return

            # Start animation task
            self._running = True
            self._animation_task = asyncio.create_task(self._run_animation_loop())

            log.log(LogCategory.SYSTEM, "Preview animation started",
                   animation_id=animation_id, speed=speed)

        except Exception as e:
            log.log(LogCategory.SYSTEM, "Failed to start preview animation",
                   level=LogLevel.ERROR, error=str(e), animation_id=animation_id)
            self.panel.clear()

    def stop_animation_preview(self) -> None:
        """
        Stop currently running animation preview

        Cancels async task, stops animation, and clears preview panel.
        Safe to call even if no animation is running.
        """
        self._running = False

        if self._current_animation:
            self._current_animation.stop()
            self._current_animation = None

        if self._animation_task:
            self._animation_task.cancel()
            self._animation_task = None

        self.panel.clear()

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

    async def _run_animation_loop(self) -> None:
        """
        Run animation loop - processes frames from animation generator

        The animation yields tuples:
        - 4-tuple (zone_tag, r, g, b) for zone-level updates
        - 5-tuple (zone_tag, pixel_idx, r, g, b) for pixel-level updates

        We extract LED index from zone_tag ("p0" → 0) and build frames for
        PreviewPanel.show_frame().
        """
        if not self._current_animation:
            return

        try:
            self._current_animation.running = True

            async for frame_data in self._current_animation.run():
                if not self._running:
                    break

                # Initialize frame (all LEDs off)
                frame = [(0, 0, 0)] * self.panel.count

                # Parse frame data
                if len(frame_data) == 5:  # Pixel-level (zone_tag, pixel_idx, r, g, b)
                    zone_tag, pixel_idx, r, g, b = frame_data
                    if zone_tag.startswith("p"):
                        led_index = int(zone_tag[1:])  # "p0" → 0, "p7" → 7
                        if 0 <= led_index < self.panel.count:
                            frame[led_index] = (r, g, b)

                elif len(frame_data) == 4:  # Zone-level (zone_tag, r, g, b)
                    zone_tag, r, g, b = frame_data
                    if zone_tag.startswith("p"):
                        led_index = int(zone_tag[1:])
                        if 0 <= led_index < self.panel.count:
                            frame[led_index] = (r, g, b)

                # Display frame
                self.panel.show_frame(frame)

        except asyncio.CancelledError:
            # Animation stopped gracefully
            pass
        except Exception as e:
            log.log(LogCategory.SYSTEM, "Preview animation error",
                   level=LogLevel.ERROR, error=str(e))
        finally:
            self._current_animation = None
            if self._running:  # Only clear if not already cleared by stop()
                self.panel.clear()
