"""
Frame-by-frame animation debugging controller.

Integrates with EventBus for keyboard input handling (A/D/SPACE/Q).
Allows stepping through animation frames one at a time for debugging.

Architecture:
- Subscribe to KEYBOARD_KEYPRESS events
- When in frame-by-frame mode, handle A/D/SPACE/Q keys
- Load animation frames offline (one-time capture)
- Submit frames to FrameManager with DEBUG priority
- Pause animation rendering during debugging
"""

import asyncio
import time
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from utils.logger import get_category_logger
from models.enums import LogCategory, AnimationID, FramePriority, FrameSource
from models.events import KeyboardKeyPressEvent, EventType
from models.frame import FullStripFrame

if TYPE_CHECKING:
    from engine.frame_manager import FrameManager
    from animations.engine import AnimationEngine
    from services.event_bus import EventBus

log = get_category_logger(LogCategory.RENDER_ENGINE)


class FramePlaybackController:
    """
    Frame-by-frame animation debugging controller.

    Integrates with EventBus to handle keyboard input for stepping through
    animation frames in debugging mode.

    Keyboard Controls (active only in frame-by-frame mode):
    - [A]: Previous frame
    - [D]: Next frame
    - [SPACE]: Play/Pause toggle
    - [Q]: Exit frame-by-frame mode

    Frame Loading:
    - Captures N frames from animation (offline preload)
    - Stores raw animation tuples (not Frame objects)
    - No real-time conversion - simple and fast

    Frame Rendering:
    - Submits frame to FrameManager with DEBUG priority (50)
    - Pauses animation rendering (FrameManager.pause())
    - Automatically displays current frame

    Usage:
        # Initialize (typically in main app)
        controller = FramePlaybackController(frame_manager, animation_engine, event_bus)

        # User enters frame-by-frame mode (e.g., button press triggers this)
        await controller.enter_frame_by_frame_mode(AnimationID.SNAKE, ANIM_SPEED=50)
        # -> Loads frames, pauses animation, enables keyboard handlers
        # -> Returns when user presses Q
        # -> Resumes animation rendering automatically

        # Keyboard events are handled automatically via _handle_keyboard_event()
    """

    def __init__(
        self,
        frame_manager: "FrameManager",
        animation_engine: "AnimationEngine",
        event_bus: "EventBus"
    ) -> None:
        """
        Initialize frame-by-frame controller.

        Args:
            frame_manager: FrameManager for rendering frames
            animation_engine: AnimationEngine for animation instantiation
            event_bus: EventBus for keyboard event subscription
        """
        self.frame_manager = frame_manager
        self.animation_engine = animation_engine
        self.event_bus = event_bus

        # Playback state
        self._frames: List[Any] = []  # Raw animation tuples (not Frame objects)
        self._current_index: int = 0
        self._playing: bool = False
        self._play_task: Optional[asyncio.Task] = None

        # Frame-by-frame mode state
        self._frame_by_frame_mode: bool = False
        self._animation_id: Optional[AnimationID] = None
        self._animation_params: Dict[str, Any] = {}
        self._exit_event: Optional[asyncio.Event] = None

        # Subscribe to keyboard events
        self.event_bus.subscribe(EventType.KEYBOARD_KEYPRESS, self._handle_keyboard_event)

        log.debug("FramePlaybackController initialized")

    # ============================================================
    # Event Handling
    # ============================================================

    def _handle_keyboard_event(self, event: KeyboardKeyPressEvent) -> None:
        """
        Handle keyboard events (callback from EventBus).

        Only processes events when in frame-by-frame mode.
        Creates async tasks for each key action (non-blocking).

        Args:
            event: KeyboardKeyPressEvent from EventBus
        """
        if not self._frame_by_frame_mode:
            return

        key = event.key.upper()  # Normalize to uppercase

        if key == 'Q':
            log.info("Exiting frame-by-frame mode (Q pressed)")
            # Signal exit to the main mode loop
            if self._exit_event:
                self._exit_event.set()

        elif key == 'A':
            log.debug("Previous frame (A pressed)")
            asyncio.create_task(self.previous_frame())

        elif key == 'D':
            log.debug("Next frame (D pressed)")
            asyncio.create_task(self.next_frame())

        elif key == 'SPACE':
            log.debug("Toggle play/pause (SPACE pressed)")
            asyncio.create_task(self._toggle_play_pause())

        # Silently ignore other keys in frame-by-frame mode

    # ============================================================
    # Frame Loading
    # ============================================================

    async def _load_animation_frames(
        self,
        animation_id: AnimationID,
        **animation_params
    ) -> int:
        """
        Preload animation frames offline.

        Creates animation instance and captures N frames from its generator.
        Stores raw tuples from animation.run() for simplicity.

        Args:
            animation_id: Which animation to load
            **animation_params: Animation parameters (ANIM_SPEED, ANIM_SNAKE_LENGTH, etc.)

        Returns:
            Number of frames loaded
        """
        log.info(
            f"Loading animation frames: {animation_id.name}",
            params=animation_params
        )

        self._frames.clear()
        self._current_index = 0

        # Create animation instance
        anim = self.animation_engine.create_animation_instance(
            animation_id,
            **animation_params
        )

        # Capture frames (limit to reasonable number to prevent memory issues)
        MAX_FRAMES = 1000
        load_start = time.perf_counter()

        try:
            async for frame_data in anim.run():
                self._frames.append(frame_data)

                # Progress logging every 100 frames
                if len(self._frames) % 100 == 0:
                    log.debug(f"  Captured {len(self._frames)} frames...")

                # Stop at limit (prevent infinite loops from infinite animations)
                if len(self._frames) >= MAX_FRAMES:
                    log.debug(f"Reached frame limit ({MAX_FRAMES})")
                    break

        except Exception as e:
            log.error(f"Error loading frames: {e}")
            self._frames.clear()
            return 0

        load_time = time.perf_counter() - load_start

        log.info(
            f"Animation frames loaded: {len(self._frames)} in {load_time:.2f}s",
            animation=animation_id.name,
            avg_ms=f"{(load_time / len(self._frames) * 1000):.1f}ms per frame" if self._frames else "N/A"
        )

        return len(self._frames)

    # ============================================================
    # Frame Navigation
    # ============================================================

    def _convert_tuple_to_frame(self, frame_data: Any) -> Optional[FullStripFrame]:
        """
        Convert raw animation tuple to Frame object.

        Supports three formats:
        - (r, g, b) -> FullStripFrame (all zones same color)
        - (zone_id, r, g, b) -> FullStripFrame (for now, render uniform)
        - (zone_id, pixel_idx, r, g, b) -> FullStripFrame (for now, render uniform)

        Note: We convert all to FullStripFrame for simplicity in debug mode.
        This means individual zones/pixels get converted to a uniform color
        (the first pixel's color). This is a limitation of frame-by-frame
        debugging, but it's simple and works.

        Args:
            frame_data: Tuple from animation.run()

        Returns:
            FullStripFrame ready for rendering, or None if format unknown
        """
        if not isinstance(frame_data, tuple):
            return None

        try:
            if len(frame_data) == 3 and isinstance(frame_data[0], int):
                # Full strip: (r, g, b)
                r, g, b = frame_data
                return FullStripFrame(
                    color=(r, g, b),
                    priority=FramePriority.DEBUG,
                    source=FrameSource.DEBUG,
                    ttl=10.0  # Long TTL so frame persists while user navigates
                )

            elif len(frame_data) == 4:
                # Zone-based: (zone_id, r, g, b)
                # For debug, just use the color
                zone_id, r, g, b = frame_data
                return FullStripFrame(
                    color=(r, g, b),
                    priority=FramePriority.DEBUG,
                    source=FrameSource.DEBUG,
                    ttl=10.0  # Long TTL so frame persists while user navigates
                )

            elif len(frame_data) == 5:
                # Pixel-based: (zone_id, pixel_idx, r, g, b)
                # For debug, just use the color
                zone_id, pixel_idx, r, g, b = frame_data
                return FullStripFrame(
                    color=(r, g, b),
                    priority=FramePriority.DEBUG,
                    source=FrameSource.DEBUG,
                    ttl=10.0  # Long TTL so frame persists while user navigates
                )

        except Exception as e:
            log.error(f"Error converting frame: {e}")
            return None

        return None

    async def show_current_frame(self) -> bool:
        """
        Display current frame.

        Converts raw animation tuple to Frame object and submits to FrameManager
        for rendering to LEDs. Also logs frame info.

        Returns:
            True if frame exists, False if no frames loaded
        """
        if not self._frames:
            log.warn("No frames loaded")
            return False

        frame_idx = self._current_index
        total = len(self._frames)
        frame_data = self._frames[frame_idx]

        # Log frame information
        status = "PLAYING" if self._playing else "PAUSED"
        log.info(
            f"Frame {frame_idx + 1}/{total}",
            animation=self._animation_id.name if self._animation_id else "?",
            status=status
        )

        # Log frame data (raw tuple format)
        if isinstance(frame_data, tuple):
            if len(frame_data) == 3 and isinstance(frame_data[0], int):
                # Full strip: (r, g, b)
                r, g, b = frame_data
                log.debug(f"Full strip color: RGB({r}, {g}, {b}) #{r:02x}{g:02x}{b:02x}")

            elif len(frame_data) == 4:
                # Zone-based: (zone_id, r, g, b)
                zone_id, r, g, b = frame_data
                log.debug(f"Zone {zone_id.name}: RGB({r}, {g}, {b})")

            elif len(frame_data) == 5:
                # Pixel-based: (zone_id, pixel_idx, r, g, b)
                zone_id, pixel_idx, r, g, b = frame_data
                log.debug(f"Pixel: zone={zone_id.name} idx={pixel_idx} RGB({r}, {g}, {b})")

        # Convert to Frame object and render
        frame = self._convert_tuple_to_frame(frame_data)
        if frame:
            await self.frame_manager.submit_full_strip_frame(frame)
            log.debug("Frame submitted to FrameManager for rendering")

            # If paused, manually step through frame
            if self.frame_manager.paused:
                self.frame_manager.step_frame()
                log.debug("Frame step requested (paused mode)")
        else:
            log.warn(f"Could not convert frame data: {frame_data}")

        return True

    async def next_frame(self) -> bool:
        """
        Advance to next frame (with wrapping).

        Returns:
            True if successful, False if no frames loaded
        """
        if not self._frames:
            log.warn("No frames loaded")
            return False

        self._current_index = (self._current_index + 1) % len(self._frames)
        return await self.show_current_frame()

    async def previous_frame(self) -> bool:
        """
        Go to previous frame (with wrapping).

        Returns:
            True if successful, False if no frames loaded
        """
        if not self._frames:
            log.warn("No frames loaded")
            return False

        self._current_index = (self._current_index - 1) % len(self._frames)
        return await self.show_current_frame()

    # ============================================================
    # Playback Control
    # ============================================================

    async def play(self, fps: int = 30) -> None:
        """
        Start automatic playback loop.

        Args:
            fps: Playback frames per second (default 30)
        """
        if not self._frames:
            log.warn("No frames loaded")
            return

        if self._playing:
            log.warn("Already playing")
            return

        self._playing = True
        log.info(f"Starting playback: {fps} FPS")

        self._play_task = asyncio.create_task(self._playback_loop(fps))

    async def stop(self) -> None:
        """Stop automatic playback."""
        self._playing = False

        if self._play_task:
            self._play_task.cancel()
            try:
                await self._play_task
            except asyncio.CancelledError:
                pass
            self._play_task = None

        log.debug("Playback stopped")

    async def _toggle_play_pause(self) -> None:
        """Toggle between playing and paused."""
        if self._playing:
            await self.stop()
        else:
            await self.play()

    async def _playback_loop(self, fps: int) -> None:
        """
        Internal: Auto-playback loop.

        Advances frame every 1/fps seconds.

        Args:
            fps: Frames per second
        """
        frame_delay = 1.0 / fps

        try:
            while self._playing:
                await self.show_current_frame()
                self._current_index = (self._current_index + 1) % len(self._frames)
                await asyncio.sleep(frame_delay)
        except asyncio.CancelledError:
            log.debug("Playback loop cancelled")

    # ============================================================
    # Frame-by-Frame Mode
    # ============================================================

    async def enter_frame_by_frame_mode(
        self,
        animation_id: AnimationID,
        **animation_params
    ) -> None:
        """
        Enter frame-by-frame debugging mode.

        Loads animation frames, pauses animation rendering, and enables
        keyboard handlers. Returns when user presses Q.

        During this mode:
        - Animation rendering is paused (FrameManager.pause())
        - Keyboard events (A/D/SPACE/Q) are processed
        - User can step through frames manually or use play/pause

        Args:
            animation_id: Which animation to debug
            **animation_params: Animation parameters
        """
        log.info(f"Entering frame-by-frame mode: {animation_id.name}")

        self._frame_by_frame_mode = True
        self._animation_id = animation_id
        self._animation_params = animation_params
        self._exit_event = asyncio.Event()

        try:
            # Load animation frames
            frame_count = await self._load_animation_frames(animation_id, **animation_params)

            if frame_count == 0:
                log.error("Failed to load animation frames")
                return

            # Pause animation rendering to prevent flicker
            # DEBUG priority won't be enough because animation frames are constantly being submitted
            self.frame_manager.pause()
            log.debug("Animation rendering paused for frame-by-frame mode")

            # Show first frame
            await self.show_current_frame()
            log.debug("Frame-by-frame mode: first frame displayed")

            # Wait for user to press Q (sets _exit_event)
            log.info(
                "Frame-by-frame mode active",
                controls="[A]=prev  [D]=next  [SPACE]=play/pause  [Q]=quit"
            )

            await self._exit_event.wait()

        finally:
            # Cleanup
            if self._playing:
                await self.stop()

            # Resume animation rendering
            self.frame_manager.resume()
            log.debug("Animation rendering resumed")

            self._frame_by_frame_mode = False
            self._frames.clear()
            self._current_index = 0

            log.info("Exited frame-by-frame mode")
