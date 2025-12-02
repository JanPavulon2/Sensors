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
from models.enums import LogCategory, AnimationID, FramePriority, FrameSource, ZoneID
from models.events import KeyboardKeyPressEvent, EventType
from models.frame import FullStripFrame, ZoneFrame, PixelFrame
from models.color import Color
from zone_layer.zone_strip import ZoneStrip
from lifecycle.task_registry import create_tracked_task, TaskCategory

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
        Preload animation frames by storing full absolute framebuffer snapshots.
        This guarantees correct backward stepping.
        
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

        
        # Prepare full framebuffer state
        current_state = self._blank_full_state()

        # Capture frames (limit to reasonable number to prevent memory issues)
        MAX_FRAMES = 1000
        load_start = time.perf_counter()

        try:
            async for update in anim.run(): # type: ignore
                
                # Apply update to framebuffer
                self._apply_update_to_state(current_state, update)

                # Store deep copy
                snapshot = {
                    zone_id: list(pixels)  # shallow copy of pixel list
                    for zone_id, pixels in current_state.items()
                }
                self._frames.append(snapshot)
                
                # Progress logging
                if len(self._frames) % 100 == 0:
                    log.debug(f"  Captured {len(self._frames)} full frames...")

                # Limit
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
            avg_ms=f"{(load_time / len(self._frames) * 1000):.1f} ms/frame" if self._frames else "N/A"
        )

        return len(self._frames)

    def _blank_full_state(self) -> Dict:
        """
        Create empty full-frame state for all zones.
        Uses ZoneID enums as keys.
        """
        state = {}

        # Find first ZoneStrip (skip PreviewPanel and other strip types)
        strip = None
        for s in self.frame_manager.zone_strips:
            if isinstance(s, ZoneStrip):
                strip = s
                break

        if not strip:
            log.error("No ZoneStrip found in main_strips")
            return {}

        # Initialize all zones with black
        for zone_id in strip.mapper.all_zone_ids():
            pixel_count = strip.mapper.get_zone_length(zone_id)
            state[zone_id] = [(0, 0, 0)] * pixel_count

        return state

    def _apply_update_to_state(self, state: Dict, update: Any) -> None:
        """
        Apply a raw animation update tuple to the full framebuffer state.

        Supports:
        (r,g,b)
        (zone_id, r,g,b)
        (zone_id, pixel_idx, r,g,b)

        State dict uses ZoneID enum keys.
        """
        if not isinstance(update, tuple):
            return

        # Case 1 — Full strip solid color
        if len(update) == 3 and isinstance(update[0], int):
            r, g, b = update
            for zone_id in state.keys():
                state[zone_id] = [(r, g, b)] * len(state[zone_id])
            return

        # Case 2 — Zone-level color update
        if len(update) == 4:
            zone_id, r, g, b = update
            if zone_id in state:
                state[zone_id] = [(r, g, b)] * len(state[zone_id])
            return

        # Case 3 — Pixel-level update
        if len(update) == 5:
            zone_id, pixel_idx, r, g, b = update
            if zone_id in state:
                if 0 <= pixel_idx < len(state[zone_id]):
                    state[zone_id][pixel_idx] = (r, g, b)
            return
        
    # ============================================================
    # Frame Navigation
    # ============================================================

    def _convert_tuple_to_frame(self, frame_data: Any) -> Optional[FullStripFrame | ZoneFrame | PixelFrame]:
        """
        Convert raw animation tuple to appropriate Frame object.

        Preserves full animation detail (pixel-level or zone-level):
        - (r, g, b) → FullStripFrame (all zones same color)
        - (zone_id, r, g, b) → ZoneFrame (single zone colored)
        - (zone_id, pixel_idx, r, g, b) → PixelFrame (single pixel in zone)

        Args:
            frame_data: Tuple from animation.run()

        Returns:
            Appropriate frame type (FullStripFrame, ZoneFrame, or PixelFrame), or None if format unknown
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
                    ttl=10.0
                )

            elif len(frame_data) == 4:
                # Zone-based: (zone_id, r, g, b)
                # Create ZoneFrame preserving zone-level structure with Color objects
                zone_id, r, g, b = frame_data
                return ZoneFrame(
                    zone_colors={zone_id: Color.from_rgb(r, g, b)},
                    priority=FramePriority.DEBUG,
                    source=FrameSource.DEBUG,
                    ttl=10.0
                )

            elif len(frame_data) == 5:
                # Pixel-based: (zone_id, pixel_idx, r, g, b)
                # Create PixelFrame preserving pixel-level structure with Color objects
                zone_id, pixel_idx, r, g, b = frame_data
                # Build pixel array for this zone with only this pixel lit
                # Note: We don't know exact zone pixel count here, so we build
                # a list large enough to contain this pixel
                pixels = [Color.black()] * (pixel_idx + 1)
                pixels[pixel_idx] = Color.from_rgb(r, g, b)

                return PixelFrame(
                    zone_pixels={zone_id: pixels},
                    priority=FramePriority.DEBUG,
                    source=FrameSource.DEBUG,
                    ttl=10.0
                )

        except Exception as e:
            log.error(f"Error converting frame: {e}")
            return None

        return None

    async def show_current_frame(self) -> bool:
        """
        Display the current full framebuffer snapshot.
        """
        
        if not self._frames:
            log.warn("No frames loaded")
            return False

        frame_idx = self._current_index
        full_state = self._frames[frame_idx]

        # Logging
        status = "PLAYING" if self._playing else "PAUSED"
        log.info(
            f"Frame {frame_idx + 1}/{len(self._frames)}",
            animation=self._animation_id.name if self._animation_id else "?",
            status=status
        )

        # Render as PixelFrame (the correct absolute frame)
        frame = PixelFrame(
            zone_pixels={
                zone: list(pixels)  # deep copy
                for zone, pixels in full_state.items()},
            priority=FramePriority.DEBUG,
            source=FrameSource.DEBUG,
            ttl=10.0
        )

        await self.frame_manager.submit_pixel_frame(frame)

        # Step when paused
        if self.frame_manager.paused:
            self.frame_manager.step_frame()

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

        self._play_task = create_tracked_task(
            self._playback_loop(fps),
            category=TaskCategory.BACKGROUND,
            description=f"FramePlayback: {fps} FPS playback loop"
        )

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
            
            # KILL CURRENT RUNNING ANIMATION
            await self.animation_engine.stop()
            await asyncio.sleep(0)
            
            # Load animation frames
            frame_count = await self._load_animation_frames(animation_id, **animation_params)

            if frame_count == 0:
                log.error("Failed to load animation frames")
                return

            # Freeze animation engine to prevent it from submitting frames while debugging
            # Animation continues running internally, but frames don't reach FrameManager
            self.animation_engine.freeze()
            log.debug("Animation engine frozen for frame-by-frame mode")

            # Clear frames below DEBUG priority to remove animation/transition flicker
            self.frame_manager.clear_below_priority(FramePriority.DEBUG)
            log.debug("Cleared frames below DEBUG priority")

            # Pause animation rendering for additional safety
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

            # Unfreeze animation engine to resume normal frame submission
            self.animation_engine.unfreeze()
            log.debug("Animation engine unfrozen, resuming normal submission")

            # Resume animation rendering
            self.frame_manager.resume()
            log.debug("Animation rendering resumed")

            
            await self.animation_engine.start(self._animation_id, **self._animation_params)

            self.frame_manager.resume()
            
            self._frame_by_frame_mode = False
            self._frames.clear()
            self._current_index = 0

            log.info("Exited frame-by-frame mode")
