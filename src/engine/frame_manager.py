"""
Simplified FrameManager — zone-based frame renderer (fixed version).
"""

import asyncio
import threading
from typing import List, Optional, Callable, Tuple
from collections import deque

from utils.logger import get_category_logger
from models.enums import LogCategory, ZoneID
from models.frame import Frame, ZoneFrame

log = get_category_logger(LogCategory.RENDER_ENGINE)


class FrameManager:
    """
    FrameManager (zone-based)

    Responsibilities:
      - Collect frames from "push" (submit_zone_frame) and "pull" (frame_sources)
      - Render frames to registered strips (ZoneStrip-like objects)
      - Support pause / single-step / FPS control
      - Minimal concurrency safety for pending frames (threading.Lock)
    """

    def __init__(self, fps: int = 60):
        self.strips: List = []
        self.fps = max(1, min(fps, 240))
        self.running = False
        self.paused = False
        self.step_requested = False

        # Pull-based frame sources
        self.frame_sources: List[Callable[[], Optional[Frame]]] = []

        # Push-based frames from AnimationEngine
        self.pending_frames: deque[ZoneFrame] = deque()
        self._pending_lock = threading.Lock()

        # Cache of latest frame per zone (so multiple zones can be rendered together)
        self._zone_cache: dict[ZoneID, List[Tuple[int, int, int]]] = {}

        # Runtime
        self.render_task: Optional[asyncio.Task] = None
        self.last_frame: Optional[Frame | ZoneFrame] = None

        log.info("FrameManager initialized", fps=self.fps)

    # === Strip management ===

    def add_strip(self, strip) -> None:
        if strip not in self.strips:
            self.strips.append(strip)
            log.info(f"Added strip: {strip}")

    def remove_strip(self, strip) -> None:
        if strip in self.strips:
            self.strips.remove(strip)
            log.info(f"Removed strip: {strip}")

    # === Frame sources (pull) ===

    def add_source(self, source: Callable[[], Optional[Frame]]) -> None:
        if source not in self.frame_sources:
            self.frame_sources.append(source)
            log.info(f"Frame source added: {source}")

    def remove_source(self, source: Callable) -> None:
        if source in self.frame_sources:
            self.frame_sources.remove(source)
            log.info(f"Frame source removed: {source}")

    # === Control API ===

    def pause(self) -> None:
        self.paused = True
        log.info("FrameManager paused")

    def resume(self) -> None:
        self.paused = False
        log.info("FrameManager resumed")

    def step_once(self) -> None:
        if not self.paused:
            log.warn("step_once() ignored — must be paused first")
            return
        self.step_requested = True
        log.info("FrameManager: single frame step requested")

    def set_fps(self, fps: int) -> None:
        self.fps = max(1, min(fps, 240))
        log.info(f"FrameManager FPS set to {self.fps}")

    async def start(self) -> None:
        if self.running:
            log.warn("FrameManager already running")
            return
        self.running = True
        self.render_task = asyncio.create_task(self._render_loop())
        log.info("FrameManager render loop started")

    async def stop(self) -> None:
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
        log.info("FrameManager render loop stopped")

    # === Push API for animations (fast path) ===

    def submit_zone_frame(self, zone_id: ZoneID, pixels: List[Tuple[int, int, int]]) -> None:
        """Submit a ZoneFrame for rendering."""
        zf = ZoneFrame(zone_id=zone_id, pixels=pixels)
        with self._pending_lock:
            self.pending_frames.append(zf)
        # log.info(f"[FrameManager] ZoneFrame submitted: {zone_id.name} ({len(pixels)} px)")  # Too verbose

    # === Core render loop ===

    async def _render_loop(self) -> None:
        frame_delay = 1.0 / self.fps
        log.info(f"Render loop running at {self.fps} FPS")

        frame_counter = 0

        while self.running:
            if self.paused and not self.step_requested:
                await asyncio.sleep(0.01)
                continue

             # Fetch new zone frames (push-based)
            pushed_frames = self._fetch_pending_frames()
            if pushed_frames:
                for frame in pushed_frames:
                    self._zone_cache[frame.zone_id] = frame.pixels

                if frame_counter % 60 == 0:  # Log every second
                    log.info(f"[FrameManager] Received {len(pushed_frames)} zone frames, cache size: {len(self._zone_cache)}")

            # Optional: combine with pull-based sources
            pulled_frame = self._compose_frame_from_sources()
            if pulled_frame:
                self._zone_cache.update(pulled_frame.to_zone_dict())

            # Render all known zones
            if self._zone_cache:
                self._render_all_zones()

            frame_counter += 1
            self.step_requested = False
            await asyncio.sleep(frame_delay)

    # === internal helpers ===

    def _fetch_pending_frames(self) -> List[ZoneFrame]:
        """Fetch all currently pending ZoneFrames."""
        frames = []
        with self._pending_lock:
            while self.pending_frames:
                frames.append(self.pending_frames.popleft())
        return frames

    def _compose_frame_from_sources(self) -> Optional[Frame]:
        """Pull latest non-empty frame from registered sources."""
        latest_frame: Optional[Frame] = None
        for source in self.frame_sources:
            try:
                f = source()
                if f:
                    latest_frame = f
            except Exception as e:
                log.error(f"Frame source error: {e}")
        return latest_frame

    def _render_all_zones(self):
        """Render all cached zones to all strips."""
        for zone_id, pixels in self._zone_cache.items():
            zone_name = zone_id.name  # Convert ZoneID enum → "LAMP" string

            for strip in self.strips:
                # Check if this strip supports this zone
                # ZoneStrip: has 'zones' dict attribute
                if hasattr(strip, 'zones') and zone_name in strip.zones:
                    try:
                        # Batch update all pixels in zone (show=False)
                        for i, (r, g, b) in enumerate(pixels):
                            strip.set_pixel_color(zone_name, i, r, g, b, show=False)

                        # Single show() call per zone (efficient)
                        strip.show()
                        log.debug(f"[Render] Zone {zone_name}: {len(pixels)} px rendered")
                    except Exception as e:
                        log.error(f"Render error on zone {zone_name}: {e}")

                # PreviewPanel or other single-zone strips
                elif hasattr(strip, 'zone_id') and strip.zone_id == zone_id:
                    try:
                        for i, (r, g, b) in enumerate(pixels):
                            strip.set_pixel_color_absolute(i, r, g, b, show=False)
                        strip.show()
                        log.info(f"[Render] SingleZone {zone_name}: {len(pixels)} px rendered")
                    except Exception as e:
                        log.error(f"Render error on single-zone strip {zone_name}: {e}")
                
    def _apply_zone_cache(self, zone_cache: dict[ZoneID, List[Tuple[int, int, int]]]) -> None:
        """Apply latest cached frame per zone to all matching strips."""
        for zone_id, pixels in zone_cache.items():
            for strip in self.strips:
                strip_zone = getattr(strip, "zone_id", None)
                if strip_zone != zone_id:
                    continue
                try:
                    pixel_count = getattr(strip, "pixel_count", len(pixels))
                    for i, (r, g, b) in enumerate(pixels[:pixel_count]):
                        strip.set_pixel_color_absolute(i, r, g, b, show=False)
                    strip.show()
                except Exception as e:
                    log.error(f"Error applying frame to {strip}: {e}")
