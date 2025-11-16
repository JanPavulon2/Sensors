"""
FrameManager — Centralized rendering system with priority queues and dual strip support.

Architecture:
  - Collects frames from multiple sources (animations, transitions, static, preview)
  - Maintains separate priority queues for main strip and preview panel
  - Selects highest-priority frame each render tick
  - Renders atomically to all registered strips
  - Supports pause/step/FPS control for debugging

Priority System:
  IDLE (0) < MANUAL (10) < PULSE (20) < ANIMATION (30) < TRANSITION (40) < DEBUG (50)

Only the highest-priority frame is rendered. When high-priority sources stop,
rendering automatically falls back to lower priorities.
"""

import asyncio
import time
from typing import Dict, List, Optional, Deque, Callable
from collections import deque

from utils.logger2 import get_logger
from models.enums import LogCategory, FramePriority
from models.frame import (
    FullStripFrame, ZoneFrame, PixelFrame, PreviewFrame,
    MainStripFrame, AnyFrame
)

log = get_logger().for_category(LogCategory.RENDER_ENGINE)


class WS2811Timing:
    """
    WS2811 protocol timing requirements for 90-pixel strip.

    At 800kHz data rate with 24 bits per pixel and 90 pixels total:
    - Bits per frame: 2,160
    - DMA transfer time: 2.7ms
    - Reset time: 50µs minimum
    - Minimum frame time: 2.75ms
    """

    DATA_RATE_HZ = 800_000
    BIT_TIME_US = 1.25
    RESET_TIME_US = 50
    BITS_PER_PIXEL = 24
    PIXEL_COUNT = 90
    TOTAL_BITS = BITS_PER_PIXEL * PIXEL_COUNT

    DMA_TRANSFER_MS = (TOTAL_BITS * BIT_TIME_US) / 1000
    RESET_TIME_MS = RESET_TIME_US / 1000
    MIN_FRAME_TIME_MS = DMA_TRANSFER_MS + RESET_TIME_MS

    THEORETICAL_MAX_FPS = 1000 / MIN_FRAME_TIME_MS
    PRACTICAL_MAX_FPS = 150
    TARGET_FPS = 60


class FrameManager:
    """
    Centralized frame rendering manager.

    Manages:
    - Dual priority queues (main_queues, preview_queues)
    - Frame submission from multiple sources
    - Priority-based frame selection
    - Atomic rendering to multiple strips
    - Pause/step/FPS control
    - Frame expiration (TTL)
    - Performance metrics
    """

    def __init__(self, fps: int = 60):
        """
        Initialize FrameManager.

        Args:
            fps: Target render frequency (1-240, default 60)
        """
        self.fps = max(1, min(fps, 240))

        # Dual queue system (separate for main strip and preview)
        # maxlen=2 prevents unbounded growth
        self.main_queues: Dict[int, Deque[MainStripFrame]] = {
            p.value: deque(maxlen=2)
            for p in FramePriority
            if isinstance(p.value, int)
        }
        self.preview_queues: Dict[int, Deque[PreviewFrame]] = {
            p.value: deque(maxlen=2)
            for p in FramePriority
            if isinstance(p.value, int)
        }

        # Registered render targets
        self.main_strips: List = []  # ZoneStrip instances
        self.preview_strips: List = []  # PreviewPanel instances
        
        # Runtime state
        self.running = False
        self.paused = False
        self.step_requested = False
        self.render_task: Optional[asyncio.Task] = None

        # Timing & performance metrics
        self.last_show_time = time.perf_counter()
        self.frame_times: Deque[float] = deque(maxlen=300)  # Last 5 seconds @ 60 FPS
        self.dropped_frames = 0
        self.frames_rendered = 0

        # Async lock for frame submission safety
        self._lock = asyncio.Lock()

        log.info(
            "FrameManager initialized",
            fps=self.fps,
            timing=f"min={WS2811Timing.MIN_FRAME_TIME_MS:.2f}ms",
        )

    # === Strip Management ===

    def add_main_strip(self, strip) -> None:
        """Register a main LED strip (ZoneStrip)."""
        if strip not in self.main_strips:
            self.main_strips.append(strip)
            log.debug(f"Added main strip: {strip}")

    def add_preview_strip(self, strip) -> None:
        """Register a preview LED strip (PreviewPanel)."""
        if strip not in self.preview_strips:
            self.preview_strips.append(strip)
            log.debug(f"Added preview strip: {strip}")

    def remove_main_strip(self, strip) -> None:
        """Unregister a main LED strip."""
        if strip in self.main_strips:
            self.main_strips.remove(strip)
            log.debug(f"Removed main strip: {strip}")

    def remove_preview_strip(self, strip) -> None:
        """Unregister a preview LED strip."""
        if strip in self.preview_strips:
            self.preview_strips.remove(strip)
            log.debug(f"Removed preview strip: {strip}")

    # === Strip Registration (for controllers) ===

    def add_strip(self, strip) -> None:
        """
        Register a strip (used by LEDController).

        Note: New code should use add_main_strip() or add_preview_strip() explicitly.
        """
        self.add_main_strip(strip)

    def remove_strip(self, strip) -> None:
        """Unregister a strip."""
        self.remove_main_strip(strip)
        self.remove_preview_strip(strip)

    # === Frame Submission API (Type-Specific) ===

    async def submit_full_strip_frame(self, frame: FullStripFrame) -> None:
        """Submit a full-strip frame (single color for all zones)."""
        async with self._lock:
            self.main_queues[frame.priority.value].append(frame)

    async def submit_zone_frame(self, frame: ZoneFrame) -> None:
        """Submit a per-zone frame."""
        async with self._lock:
            self.main_queues[frame.priority.value].append(frame)

    async def submit_pixel_frame(self, frame: PixelFrame) -> None:
        """Submit a per-pixel frame."""
        async with self._lock:
            self.main_queues[frame.priority.value].append(frame)

    async def submit_preview_frame(self, frame: PreviewFrame) -> None:
        """Submit a preview panel frame."""
        async with self._lock:
            self.preview_queues[frame.priority.value].append(frame)

    # === Control API ===

    def pause(self) -> None:
        """Pause rendering (for debugging)."""
        self.paused = True
        log.info("FrameManager paused")

    def resume(self) -> None:
        """Resume rendering."""
        self.paused = False
        log.info("FrameManager resumed")

    def step_frame(self) -> None:
        """Render single frame when paused (frame-by-frame mode)."""
        if not self.paused:
            log.warn("step_frame() ignored — must be paused first")
            return
        self.step_requested = True

    def set_fps(self, fps: int) -> None:
        """Change FPS at runtime."""
        self.fps = max(1, min(fps, 240))
        log.info(f"FrameManager FPS set to {self.fps}")

    # === Lifecycle ===

    async def start(self) -> None:
        """Start the render loop."""
        if self.running:
            log.warn("FrameManager already running")
            return
        self.running = True
        self.render_task = asyncio.create_task(self._render_loop())
        log.info(f"FrameManager render loop started @ {self.fps} FPS")

    async def stop(self) -> None:
        """Stop the render loop."""
        if not self.running:
            return
        self.running = False
        if self.render_task:
            self.render_task.cancel()
            try:
                await self.render_task
            except asyncio.CancelledError:
                pass
            self.render_task = None
        log.info(
            "FrameManager stopped",
            frames_rendered=self.frames_rendered,
            dropped_frames=self.dropped_frames,
        )

    # === Metrics ===

    def get_actual_fps(self) -> float:
        """Get measured FPS over recent frames."""
        if len(self.frame_times) < 2:
            return 0.0
        duration = self.frame_times[-1] - self.frame_times[0]
        if duration <= 0:
            return 0.0
        return len(self.frame_times) / duration

    def get_metrics(self) -> Dict:
        """Get performance metrics."""
        return {
            "fps_target": self.fps,
            "fps_actual": self.get_actual_fps(),
            "frames_rendered": self.frames_rendered,
            "dropped_frames": self.dropped_frames,
            "pending_main": sum(len(q) for q in self.main_queues.values()),
            "pending_preview": sum(len(q) for q in self.preview_queues.values()),
        }

    # === Core Render Loop ===

    async def _render_loop(self) -> None:
        """Main render loop @ target FPS."""
        frame_delay = 1.0 / self.fps
        log.info(f"Render loop @ {self.fps} FPS (delay={frame_delay*1000:.2f}ms)")

        while self.running:
            # Handle pause/step
            if self.paused and not self.step_requested:
                await asyncio.sleep(0.01)
                continue

            # Enforce WS2811 timing constraints
            elapsed = time.perf_counter() - self.last_show_time
            if elapsed < WS2811Timing.MIN_FRAME_TIME_MS / 1000:
                await asyncio.sleep(
                    (WS2811Timing.MIN_FRAME_TIME_MS / 1000) - elapsed
                )

            # Select and render frames
            try:
                main_frame = await self._select_main_frame_by_priority()
                preview_frame = await self._select_preview_frame_by_priority()

                # Render atomically
                if main_frame or preview_frame:
                    self._render_atomic(main_frame, preview_frame)
                    self.frames_rendered += 1
                    self.frame_times.append(time.perf_counter())

            except Exception as e:
                log.error(f"Render error: {e}", exc_info=True)

            # Reset step flag
            self.step_requested = False
            self.last_show_time = time.perf_counter()

            # Frame rate control
            await asyncio.sleep(frame_delay)

    # === Frame Selection ===

    async def _select_main_frame_by_priority(self) -> Optional[MainStripFrame]:
        """
        Select highest-priority non-expired frame from main queues.

        Priority order: DEBUG > TRANSITION > ANIMATION > PULSE > MANUAL > IDLE

        Returns:
            MainStripFrame with highest priority, or None if all expired/empty
        """
        async with self._lock:
            # Iterate from highest to lowest priority
            for priority_value in sorted(self.main_queues.keys(), reverse=True):
                queue = self.main_queues[priority_value]
                while queue:
                    frame = queue.popleft()
                    if not frame.is_expired():
                        return frame
                    # Expired frame discarded, try next

        return None

    async def _select_preview_frame_by_priority(self) -> Optional[PreviewFrame]:
        """
        Select highest-priority non-expired frame from preview queues.

        Priority order: DEBUG > TRANSITION > ANIMATION > PULSE > MANUAL > IDLE

        Returns:
            PreviewFrame with highest priority, or None if all expired/empty
        """
        async with self._lock:
            # Iterate from highest to lowest priority
            for priority_value in sorted(self.preview_queues.keys(), reverse=True):
                queue = self.preview_queues[priority_value]
                while queue:
                    frame = queue.popleft()
                    if not frame.is_expired():
                        return frame
                    # Expired frame discarded, try next

        return None

    # === Rendering ===

    def _render_atomic(
        self, main_frame: Optional[MainStripFrame], preview_frame: Optional[PreviewFrame]
    ) -> None:
        """
        Render frames to all registered strips atomically.

        Ensures main strip and preview panel are synchronized.
        """
        # Render main strip
        if main_frame:
            self._render_main_frame(main_frame)

        # Render preview panel
        if preview_frame:
            self._render_preview_frame(preview_frame)

    def _render_main_frame(self, frame: MainStripFrame) -> None:
        """Render main strip frame (type dispatch)."""
        for strip in self.main_strips:
            try:
                if isinstance(frame, FullStripFrame):
                    self._render_full_strip(frame, strip)
                elif isinstance(frame, ZoneFrame):
                    self._render_zone_frame(frame, strip)
                elif isinstance(frame, PixelFrame):
                    self._render_pixel_frame(frame, strip)
            except Exception as e:
                log.error(f"Error rendering main frame to {strip}: {e}")

    def _render_preview_frame(self, frame: PreviewFrame) -> None:
        """Render preview panel frame."""
        for strip in self.preview_strips:
            try:
                strip.show_frame(frame.pixels)
            except Exception as e:
                log.error(f"Error rendering preview frame to {strip}: {e}")

    def _render_full_strip(self, frame: FullStripFrame, strip) -> None:
        """
        Render single color to all zones.

        Args:
            frame: FullStripFrame with single (r, g, b)
            strip: ZoneStrip instance
        """
        r, g, b = frame.color
        for zone_name in getattr(strip, "zones", {}).keys():
            try:
                strip.set_zone_color(zone_name, r, g, b, show=False)
            except Exception as e:
                log.error(f"Error setting zone {zone_name}: {e}")
        strip.show()

    def _render_zone_frame(self, frame: ZoneFrame, strip) -> None:
        """
        Render per-zone colors.

        Args:
            frame: ZoneFrame with zone_colors dict
            strip: ZoneStrip instance
        """
        for zone_id, (r, g, b) in frame.zone_colors.items():
            zone_name = zone_id.name if hasattr(zone_id, "name") else str(zone_id)
            try:
                strip.set_zone_color(zone_name, r, g, b, show=False)
            except Exception as e:
                log.error(f"Error setting zone {zone_name}: {e}")
        strip.show()

    def _render_pixel_frame(self, frame: PixelFrame, strip) -> None:
        """
        Render per-pixel colors using full-buffer overwrite.
        Ensures correct clearing when stepping backward in animations.
        """

        try:
            cleaned = {}
            
            for zone_id, pixels in frame.zone_pixels.items():
                zone_name = zone_id if isinstance(zone_id, str) else zone_id.name

                if zone_name not in strip.zones:
                    continue

                expected_len = len(strip.zones[zone_name])

                # extend or trim
                if len(pixels) != expected_len:
                    fixed = list(pixels[:expected_len])
                    if len(fixed) < expected_len:
                        fixed += [(0, 0, 0)] * (expected_len - len(fixed))
                    cleaned[zone_name] = fixed
                else:
                    cleaned[zone_name] = list(pixels)

            strip.show_full_pixel_frame(cleaned)

        except Exception as e:
            log.error(f"Error rendering pixel frame to {strip}: {e}")
    
    # === Cleanup ===

    def clear_all(self) -> None:
        """Clear all pending frames."""
        for queue in self.main_queues.values():
            queue.clear()
        for queue in self.preview_queues.values():
            queue.clear()
        log.info("FrameManager queues cleared")

    def clear_below_priority(self, min_priority: FramePriority) -> None:
        """
        Clear all frames below a specified priority level.

        Used by frame-by-frame debugging to remove animation frames
        before entering debug mode, preventing animation flicker.

        Args:
            min_priority: Frames below this priority are cleared
        """
        min_value = min_priority.value if isinstance(min_priority.value, int) else 0

        cleared_count = 0
        for priority_value, queue in list(self.main_queues.items()):
            if priority_value < min_value:
                cleared_count += len(queue)
                queue.clear()

        for priority_value, queue in list(self.preview_queues.items()):
            if priority_value < min_value:
                cleared_count += len(queue)
                queue.clear()

        if cleared_count > 0:
            log.debug(f"Cleared {cleared_count} frames below priority {min_priority.name}")

    def __repr__(self) -> str:
        metrics = self.get_metrics()
        return (
            f"FrameManager(fps={metrics['fps_actual']:.1f}/{metrics['fps_target']}, "
            f"rendered={metrics['frames_rendered']}, "
            f"dropped={metrics['dropped_frames']})"
        )
