"""
Preview Controller

Orchestrates preview panel display modes and animation playback.
Each animation provides its own simplified preview visualization via run_preview().
"""

import asyncio
from typing import Optional, Tuple, List, TYPE_CHECKING, Any
from obsolete.preview_panel import PreviewPanel
from utils.logger import get_logger, LogLevel, LogCategory
from models.color import Color
from models.enums import AnimationID
from services.transition_service import TransitionService

if TYPE_CHECKING:
    from animations.base import BaseAnimation

log = get_logger().for_category(LogCategory.HARDWARE)


class PreviewPanelController:
    """
    Preview panel orchestration controller

    Manages preview display modes and delegates to PreviewPanel for rendering.
    Animations provide simplified 8-pixel preview via their run_preview() method.

    Responsibilities:
        - Display mode management (color, bar, animation)
        - Animation lifecycle (start/stop async tasks)
        - Direct frame rendering (no translation needed)
        - Parameter updates (speed, color changes)

    Args:
        preview_panel: PreviewPanel instance for hardware control

    Example:
        >>> controller = PreviewController(preview_panel)
        >>> controller.show_color((255, 0, 0), 50)  # Red at 50% brightness
        >>> controller.start_animation_preview('snake', speed=60, hue=120, length=3)
        >>> controller.update_param('speed', 80)  # Live speed change
        >>> controller.stop_animation_preview()
    """

    def __init__(self, preview_panel: PreviewPanel, transition_service: TransitionService, parent_controller=None):
        self.preview_panel = preview_panel
        self.transition_service = transition_service
        self._parent_controller = parent_controller  # Parent LEDController reference for mode checking
        self._animation_task: Optional[asyncio.Task] = None
        self._current_animation: Optional['BaseAnimation'] = None
        self._animation_running = False
        self._current_animation_id: Optional[AnimationID] = None  # Track which animation is running

    # ===== STATIC DISPLAY METHODS =====

    def fill_with_color(self, color: Color) -> None:
        if self._animation_running:
            # Stop synchronously without crossfade
            asyncio.create_task(self._stop_animation_without_crossfade())

        r, g, b = color.to_rgb()
        self.preview_panel.fill_with_color((r, g, b))

    def show_color(self, rgb: Tuple[int, int, int], brightness: int = 100, use_crossfade: bool = True) -> None:
        """
        Show static color on all 8 LEDs with brightness scaling

        Stops any running animation before displaying, optionally with crossfade.

        Args:
            rgb: RGB tuple (0-255 values)
            brightness: Brightness percentage (0-100)
            use_crossfade: If True and animation is running, crossfade to new color

        Example:
            >>> controller.show_color((255, 100, 50), 75)  # Orange at 75%
        """
        # Apply brightness scaling
        r, g, b = [int(c * brightness / 100) for c in rgb]
        target_frame = [(r, g, b)] * self.preview_panel.count

        if self._animation_running and use_crossfade:
            # Stop with crossfade to target
            asyncio.create_task(self.stop_animation_preview(target_frame))
        else:
            # Stop without crossfade or no animation running
            if self._animation_running:
                asyncio.create_task(self._stop_animation_without_crossfade())
            self.preview_panel.fill_with_color((r, g, b))

    def show_bar(self, value: int, max_value: int = 100,
                 color: Tuple[int, int, int] = (255, 255, 255), use_crossfade: bool = True) -> None:
        """
        Show bar indicator (0-8 LEDs lit proportionally to value)

        Stops any running animation before displaying, optionally with crossfade.

        Args:
            value: Current value
            max_value: Maximum value for normalization
            color: RGB color for lit LEDs
            use_crossfade: If True and animation is running, crossfade to bar

        Example:
            >>> controller.show_bar(60, 100, (0, 255, 0))  # 5 LEDs green (60%)
        """
        # Build target frame for bar
        filled = int((value / max_value) * self.preview_panel.count)
        filled = max(0, min(self.preview_panel.count, filled))
        target_frame = [color if i < filled else (0, 0, 0) for i in range(self.preview_panel.count)]

        if self._animation_running and use_crossfade:
            # Stop with crossfade to bar
            asyncio.create_task(self.stop_animation_preview(target_frame))
        else:
            # Stop without crossfade or no animation running
            if self._animation_running:
                asyncio.create_task(self._stop_animation_without_crossfade())
            self.preview_panel.show_bar(value, max_value, color)

    async def _stop_animation_without_crossfade(self) -> None:
        """Stop animation immediately without crossfade"""
        await self.stop_animation_preview(target_frame=None)

    # ===== ANIMATION PREVIEW METHODS =====

    def _create_animation_instance(
        self,
        animation_id: AnimationID,
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
        if animation_id == AnimationID.SNAKE:
            return SnakeAnimation(
                zones=empty_zones,
                speed=speed,
                hue=params.get('hue', 0),
                length=params.get('length', 1),
                color=params.get('color')  # Backwards compat
            )

        # elif animation_id == AnimationID.BREATHE:
        #     # For breathe preview, check if zone_colors provided (per-zone preview)
        #     zone_colors = params.get('zone_colors')

        #     # If no zone colors, convert hue to RGB for single-color preview
        #     if zone_colors is None:
        #         from utils.colors import hue_to_rgb
        #         color = params.get('color')
        #         if color is None and 'hue' in params:
        #             color = hue_to_rgb(params['hue'])
        #         if color is None:
        #             color = (255, 0, 0)  # Default red
        #     else:
        #         color = None  # Will use zone_colors in run_preview

        #     return BreatheAnimation(
        #         zones=empty_zones,
        #         speed=speed,
        #         color=color,
        #         intensity=params.get('intensity', 100),
        #         zone_colors=zone_colors  # Pass zone colors for per-zone preview
        #     )

        elif animation_id == AnimationID.COLOR_FADE:
            return ColorFadeAnimation(
                zones=empty_zones,
                speed=speed,
                start_hue=params.get('start_hue', 0)
            )

        elif animation_id == AnimationID.COLOR_SNAKE:
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

    def start_animation_preview(self, animation_id: AnimationID, speed: int = 50, use_crossfade: bool = True, **params) -> None:
        """
        Start animation preview using animation's run_preview() method

        Instantiates the animation class and runs its simplified preview visualization
        designed for 8 pixels.

        Args:
            animation_id: Animation name ('snake', 'breathe', 'color_fade', 'color_snake')
            speed: Animation speed (1-100)
            use_crossfade: If True and previous animation running, crossfade between them
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

        # If crossfade enabled and animation running, do async crossfade transition
        if use_crossfade and (self._animation_running or self._animation_task):
            # Get first frame of new animation for crossfade target
            asyncio.create_task(self._crossfade_to_new_animation(animation_id, speed, params))
            return

        # Stop previous animation IMMEDIATELY (no crossfade)
        if self._animation_running or self._animation_task:
            self._stop_animation_sync()

        self._start_animation_preview_internal(animation_id, speed, params)

    async def _crossfade_to_new_animation(self, animation_id: AnimationID, speed: int, params: dict) -> None:
        """
        Crossfade from current animation to new animation

        Captures first frame of new animation and crossfades to it.
        """
        # Capture current frame before stopping
        from_frame = self.preview_panel.get_frame()

        # Stop old animation (wait for completion)
        await self.stop_animation_preview(target_frame=None)  # Don't crossfade yet

        # Create new animation instance temporarily to get first frame
        try:
            temp_anim = self._create_animation_instance(animation_id, speed, **params)
            if temp_anim:
                temp_anim.running = True
                # Get first frame from preview
                async for first_frame in temp_anim.run_preview(pixel_count=self.preview_panel.count):
                    # Stop temporary animation
                    temp_anim.stop()

                    # Crossfade from old last frame to new first frame
                    await self._crossfade_preview(from_frame, first_frame, duration_ms=200, steps=8)
                    break
        except Exception as e:
            log.error(
                "Crossfade failed, using instant switch",
                level=LogLevel.WARN, 
                error=str(e)
            )

        # Start the actual animation
        self._start_animation_preview_internal(animation_id, speed, params)

    def _stop_animation_sync(self) -> None:
        """
        Stop animation synchronously (sets flags, cancels task)

        Does NOT wait for task completion - old task will finish in background.
        Does NOT perform crossfade - instant stop for animation-to-animation transitions.
        """
        self._animation_running = False

        if self._current_animation:
            self._current_animation.stop()

        if self._animation_task:
            self._animation_task.cancel()
            self._animation_task = None

        self._current_animation = None

    def _start_animation_preview_internal(self, animation_id: AnimationID, speed: int, params: dict) -> None:
        """Internal method to start animation preview (assumes no animation is running)"""
        self._current_animation_id = animation_id

        # Instantiate animation (no zones needed - preview mode uses simplified logic)
        try:
            self._current_animation = self._create_animation_instance(
                animation_id, speed, **params
            )

            if not self._current_animation:
                log.warn(
                    "Unknown animation for preview",
                    animation_id=animation_id
                )
                
                # Fallback: show static color
                self.show_color((50, 50, 50))
                return

            # Start animation task
            self._animation_running = True
            self._animation_task = asyncio.create_task(self._run_preview_loop())

            log.debug(f"Preview: {animation_id} @ {speed}")

        except Exception as e:
            log.error("Failed to start preview animation",
                   level=LogLevel.ERROR, error=str(e), animation_id=animation_id)
            self.preview_panel.clear()

    async def stop_animation_preview(self, target_frame: Optional[List[Tuple[int, int, int]]] = None) -> None:
        """
        Stop currently running animation preview

        Cancels async task, stops animation, and optionally crossfades to target frame.
        If no target_frame provided, clears to black.
        Safe to call even if no animation is running.
        Waits for task to actually finish before returning.

        Args:
            target_frame: Optional target frame to crossfade to (instead of clearing to black)
        """
        # Capture current frame before stopping (for crossfade)
        from_frame = self.preview_panel.get_frame() if target_frame else None

        self._animation_running = False

        if self._current_animation:
            self._current_animation.stop()

        if self._animation_task:
            self._animation_task.cancel()
            try:
                await self._animation_task
            except asyncio.CancelledError:
                pass
            self._animation_task = None

        self._current_animation = None

        # Crossfade to target or clear
        if target_frame and from_frame:
            await self._crossfade_preview(from_frame, target_frame)
        else:
            self.preview_panel.clear()

    async def _crossfade_preview(
        self,
        from_frame: List[Tuple[int, int, int]],
        to_frame: List[Tuple[int, int, int]],
        duration_ms: int = 300,
        steps: int = 10
    ) -> None:
        """
        Crossfade between two frames on preview panel

        Smoothly interpolates RGB values from one frame to another.

        Args:
            from_frame: Starting frame
            to_frame: Target frame
            duration_ms: Total duration in milliseconds
            steps: Number of interpolation steps
        """
        if len(from_frame) != len(to_frame):
            # Fallback to instant switch if frames don't match
            self.preview_panel.show_frame(to_frame)
            return

        step_delay = duration_ms / 1000 / steps

        for step in range(steps + 1):
            progress = step / steps

            # Interpolate each pixel
            interpolated_frame = []
            for (r1, g1, b1), (r2, g2, b2) in zip(from_frame, to_frame):
                r = int(r1 + (r2 - r1) * progress)
                g = int(g1 + (g2 - g1) * progress)
                b = int(b1 + (b2 - b1) * progress)
                interpolated_frame.append((r, g, b))

            self.preview_panel.show_frame(interpolated_frame)
            await asyncio.sleep(step_delay)

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
            log.info(
                "Preview animation parameter updated",
                param=param, 
                value=value
            )

    async def _run_preview_loop(self) -> None:
        """
        Run animation preview loop - uses animation's run_preview() method

        Each animation provides its own simplified preview visualization for 8 pixels.
        Frames are directly displayed on the preview panel.
        """
        # Capture animation instance at start to avoid race conditions
        animation_instance = self._current_animation
        if not animation_instance:
            return

        try:
            animation_instance.running = True

            async for frame in animation_instance.run_preview(pixel_count=self.preview_panel.count):
                if not self._animation_running:
                    break

                # Display frame directly (already in correct format)
                self.preview_panel.show_frame(frame)

        except asyncio.CancelledError as e:
            log.warn(
                "asyncio.CancelledError catched",
                error=str(e)
            )
            pass
        
        except Exception as e:
            log.error(
                "Preview animation error",
                error=str(e)
            )
            
        finally:
            # Only clear if this is still the current animation (not replaced by new one)
            if self._current_animation is animation_instance:
                self._current_animation = None
                if self._animation_running:
                    self.preview_panel.clear()

    def clear(self) -> None:
        """Clear preview panel immediately"""
        # if self._animation_running:
        #     # Stop synchronously without crossfade
        #     asyncio.create_task(self._stop_animation_without_crossfade())

        self.preview_panel.clear()

    # ===== POWER TOGGLE FADE SUPPORT =====

    async def fade_out_for_power_off(self, duration_ms: int = 500, steps: int = 20):
        """
        Fade out preview panel to black (for power toggle).

        Preview panel doesn't have TransitionService, so we do manual fade.
        This is called by PowerToggleController during power off.

        Args:
            duration_ms: Total fade duration in milliseconds
            steps: Number of fade steps
        """
        try:
            current_frame = self.preview_panel.get_frame()
            step_delay = duration_ms / 1000 / steps

            for step in range(steps, -1, -1):
                factor = step / steps
                faded_frame = [
                    (int(r * factor), int(g * factor), int(b * factor))
                    for r, g, b in current_frame
                ]
                self.preview_panel.show_frame(faded_frame)
                await asyncio.sleep(step_delay)

            self.preview_panel.clear()
            log.debug("Preview panel faded out")

        except Exception as e:
            log.error(
                "Preview fade-out failed",
                error=str(e)
            )

    async def fade_in_for_power_on(self, duration_ms: int = 500, steps: int = 20):
        """
        Fade in preview panel from black to current state (for power toggle).

        Builds target frame from current zone/animation state.
        This is called by PowerToggleController during power on.

        Args:
            duration_ms: Total fade duration in milliseconds
            steps: Number of fade steps
        """
        try:
            # Import here to avoid circular dependency
            from models.enums import ZoneRenderMode

            # Build target frame based on current mode
            if hasattr(self, '_parent_controller'):
                # If we have parent reference
                parent = self._parent_controller
                current_zone = parent.zone_service.get_selected_zone()
                if current_zone and current_zone.state.mode == ZoneRenderMode.STATIC:
                    # Static mode: show current zone color
                    r, g, b = current_zone.state.color.to_rgb()
                    brightness = current_zone.brightness
                    r = int(r * brightness / 100)
                    g = int(g * brightness / 100)
                    b = int(b * brightness / 100)
                    target_frame = [(r, g, b)] * self.preview_panel.count
                else:
                    # Animation mode: get current preview frame
                    target_frame = self.preview_panel.get_frame()
            else:
                # Fallback: use current frame (if animation is running)
                target_frame = self.preview_panel.get_frame()

            # Fade in from black to target
            step_delay = duration_ms / 1000 / steps

            for step in range(steps + 1):
                factor = step / steps
                faded_frame = [
                    (int(r * factor), int(g * factor), int(b * factor))
                    for r, g, b in target_frame
                ]
                self.preview_panel.show_frame(faded_frame)
                await asyncio.sleep(step_delay)

            log.debug("Preview panel faded in")

        except Exception as e:
            log.error(
                "Preview fade-in failed",
                error=str(e)
            )