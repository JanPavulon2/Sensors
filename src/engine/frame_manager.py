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

FrameManager v2
---------------
Wielokanałowy renderer LED wspierający:
- wiele GPIO
- wiele fizycznych stripów
- strefy rozłożone na kilku GPIO
- preview + główne paski
- odwracanie stref (reversed)
- animacje i tryb statyczny

Warstwa: RENDER / INFRASTRUCTURE
"""


from __future__ import annotations
import asyncio
import time
from typing import Dict, List, Optional, Deque, cast
from collections import deque

from utils.logger import get_logger
from models.enums import FrameSource, LogCategory, FramePriority, ZoneID
from models.color import Color
from models.frame import PreviewFrame
from models.frame_v2 import SingleZoneFrame, MultiZoneFrame, PixelFrameV2, MainStripFrame, ZoneUpdateValue
from zone_layer.zone_strip import ZoneStrip
from engine.zone_render_state import ZoneRenderState

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
        
        # Registered render targets
        self.zone_strips: List[ZoneStrip] = []  # ZoneStrip instances
       
        self.zone_render_states: Dict[ZoneID, ZoneRenderState] = {}

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
        self.dma_skipped = 0  # Count of DMA transfers skipped due to frame match
        
        self.last_rendered_main_frame: Optional[MainStripFrame] = None

        self.last_rendered_frame_hash = None
        
        # Async lock for frame submission safety
        self._lock = asyncio.Lock()

        log.info(
            "FrameManager initialized",
            fps=self.fps,
            timing=f"min={WS2811Timing.MIN_FRAME_TIME_MS:.2f}ms",
        )

    # === Strip Registration (for controllers) ===

    def add_zone_strip(self, strip: ZoneStrip) -> None:
        """Register a LED strip (ZoneStrip)."""

        if strip in self.zone_strips:
            return

        self.zone_strips.append(strip)
        log.info(f"FrameManager: added strip {strip}")

        # Initialize zone render states for all zones in this strip
        strip_zone_ids = strip.mapper.all_zone_ids()
        log.info(f"add_zone_strip: strip has {len(strip_zone_ids)} zones: {[z.name for z in strip_zone_ids]}")

        for zone_id in strip_zone_ids:
            if zone_id not in self.zone_render_states:
                zone_length = strip.mapper.get_zone_length(zone_id)
                self.zone_render_states[zone_id] = ZoneRenderState(
                    zone_id=zone_id,
                    pixels=[Color.black()] * zone_length,
                )
                log.debug(f"  Initialized render state for {zone_id.name} ({zone_length} pixels)")

        log.info(f"Added main strip: {strip} (total zone_render_states now has {len(self.zone_render_states)} zones)")
        
    def remove_zone_strip(self, strip: ZoneStrip) -> None:
        """Unregister a LED strip."""
        
        if strip in self.zone_strips:
            self.zone_strips.remove(strip)
            log.debug(f"Removed main strip: {strip}")

    # === Frame Submission API (Type-Specific) ===

    
    async def push_frame(self, frame):
        """
        Unified V2 API endpoint.
        Accepts SingleZoneFrame / MultiZoneFrame / PixelFrameV2
        and wraps them into MainStripFrame for the queue system.
        """

        from models.frame_v2 import (
            SingleZoneFrame, MultiZoneFrame, PixelFrameV2
        )

        log.debug(f"FrameManager.push_frame: received {type(frame).__name__} from {getattr(frame, 'source', '?')} "
            f"priority={getattr(frame, 'priority', '?')} zone={getattr(frame, 'zone_id', '?')}")

        async with self._lock:

            # --- SingleZoneFrame ----------------------------------
            if isinstance(frame, SingleZoneFrame):
                msf = MainStripFrame(
                    priority=frame.priority,
                    ttl=frame.ttl,
                    source=frame.source,
                    partial=True,
                    updates=cast(Dict[ZoneID, ZoneUpdateValue], {frame.zone_id: frame.color}),
                )
                self.main_queues[msf.priority.value].append(msf)
                log.debug(f"Queued SingleZoneFrame: {frame.zone_id.name} (priority={msf.priority.name})")
                return

            # --- MultiZoneFrame -----------------------------------
            if isinstance(frame, MultiZoneFrame):
                msf = MainStripFrame(
                    priority=frame.priority,
                    ttl=frame.ttl,
                    source=frame.source,
                    partial=True,
                    updates=cast(Dict[ZoneID, ZoneUpdateValue], frame.zone_colors),     # dict[ZoneID, Color]
                )
                self.main_queues[msf.priority.value].append(msf)
                return

            # --- PixelFrameV2 --------------------------------------
            if isinstance(frame, PixelFrameV2):
                msf = MainStripFrame(
                    priority=frame.priority,
                    ttl=frame.ttl,
                    source=frame.source,
                    partial=True,
                    updates=cast(Dict[ZoneID, ZoneUpdateValue], frame.zone_pixels),
                )
                self.main_queues[msf.priority.value].append(msf)
                return

            raise TypeError(f"Unsupported frame type: {type(frame)}")

    # === Control API ===

    def pause(self) -> None: self.paused = True

    def resume(self) -> None: self.paused = False

    def step_frame(self) -> None: self.step_requested = True

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
            "dma_skipped": self.dma_skipped,
            "pending_main": sum(len(q) for q in self.main_queues.values()),
            # "pending_preview": sum(len(q) for q in self.preview_queues.values()),
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
                # frame = await self._select_frame_by_priority()
                frame = await self._drain_frames_of_highest_priority()
                
                # Render atomically, but skip DMA if main frame hasn't changed
                # (Phase 2 optimization: 95% DMA reduction in static-only mode)
                if frame:
                    if frame is not self.last_rendered_main_frame:
                        # Frame changed (different object) → do full render with hardware DMA
                        self._render_atomic(frame)
                        self.last_rendered_main_frame = frame
                        self.frames_rendered += 1
                        self.frame_times.append(time.perf_counter())
                        # log.debug(
                        #     f"Frame rendered (DMA)",
                        #     frame_type=type(frame).__name__ if frame else None,
                        # )
                    else:
                        # Frame unchanged (same object) → skip DMA, LEDs already have correct pixels
                        self.dma_skipped += 1
                        log.debug("Frame unchanged, skipping DMA transfer")

            except Exception as e:
                log.error(f"Render error: {e}", exc_info=True)

            # Reset step flag
            self.step_requested = False
            self.last_show_time = time.perf_counter()

            # Frame rate control
            await asyncio.sleep(frame_delay)

    # === Frame Selection ===

    async def _drain_frames_of_highest_priority(self) -> Optional[MainStripFrame]:
        """
        Pobierz wszystkie nieprzeterminowane ramki z najwyższego niepustego priorytetu
        i zmerguj je w jedną MainStripFrame (updates dict).
        """
        async with self._lock:
            # Liczymy ile ramek czeka w każdej kolejce
            queue_status = {p: len(q) for p, q in self.main_queues.items()}
            has_frames = any(count > 0 for count in queue_status.values())
            if has_frames:
                log.debug(f"_drain: Queue status: {queue_status}")

            # znajdź najwyższy priorytet, który ma coś w kolejce
            for priority_value in sorted(self.main_queues.keys(), reverse=True):
                queue = self.main_queues[priority_value]
                if not queue:
                    continue

                merged_updates = {}
                ttl = 0.0
                source = None
                priority_enum = None
                frames_processed = 0
                frames_expired = 0

                # wyciągnij wszystko co jest w kolejce teraz (maxlen=2, ale ogólnie)
                while queue:
                    frame = queue.popleft()
                    frames_processed += 1
                    if frame.is_expired():
                        frames_expired += 1
                        # log.debug(f"_drain: Frame expired: {type(frame).__name__}")
                        continue

                    # frame może być różnych typów (MainStripFrame / wrappers)
                    # Normalizujemy: oczekujemy atrybutu .updates (zone->Color or zone->list)
                    updates = getattr(frame, "updates", None)
                    if updates:
                        # prosty overwrite: ostatnia wartość ma pierwszeństwo dla danego zone
                        for zid, val in updates.items():
                            merged_updates[zid] = val

                    # merge TTL/pole źródła/priorytetu - weź minimalne TTL / pierwszy source
                    ttl = max(ttl, getattr(frame, "ttl", 0.0))
                    if source is None:
                        source = getattr(frame, "source", None)
                    if priority_enum is None:
                        priority_enum = getattr(frame, "priority", None)

                if merged_updates:
                    # Build MainStripFrame from merged updates
                    msf = MainStripFrame(
                        priority=priority_enum or FramePriority.ANIMATION,
                        ttl=ttl or 0.1,
                        source=source or FrameSource.ANIMATION,
                        partial=True,
                        updates=merged_updates,
                    )
                    # log.debug(f"_drain: Drained {frames_processed} frames ({frames_expired} expired) from priority {priority_enum.name if priority_enum else '?'}, got {len(merged_updates)} zones")
                    return msf
                # else:
                    # log.debug(f"_drain: Processed {frames_processed} frames from priority {priority_value}, all expired or empty")
                # jeżeli wszystkie ramki wygasły, sprawdź następny priorytet
        return None        

    async def _select_frame_by_priority(self) -> Optional[MainStripFrame]:
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

    # === Rendering ===

    def _render_atomic(self, main_frame: Optional[MainStripFrame]) -> None:
        """
        Render frames to all registered strips atomically.

        Ensures main strip and preview panel are synchronized.
        """
        # Render main strip
        if main_frame:
            log.debug(f"_render_atomic: rendering frame with {len(getattr(main_frame, 'updates', {}))} zone updates")
            self._render_frame(main_frame)
        else:
             log.debug(f"_render_atomic: no frame to render")

    def _render_frame(self, frame: MainStripFrame) -> None:
        """High-level render pipeline."""
        updates = frame.as_zone_update()
        merged = self._merge_updates(frame, updates)

        if self._should_skip_dma(merged):
            return

        self._render_to_all_strips(merged)

        self.frames_rendered += 1
        self.frame_times.append(time.perf_counter())
        
    def _merge_updates(self, frame: MainStripFrame, updates):
        """Dispatch merging strategy."""
        if getattr(frame, "partial", False):
            return self._merge_partial_update(updates)
        return self._merge_full_update(updates)    
    
    def _merge_full_update(self, updates):
        """Merge full-frame updates into new zone_render_states."""
        merged = {}

        for zone_id, state in self.zone_render_states.items():
            if zone_id in updates:
                new_val = updates[zone_id]
                merged[zone_id] = self._expand_or_trim_zone(new_val, len(state.pixels))
            else:
                merged[zone_id] = list(state.pixels)

        # update zone render state
        for zid, pix in merged.items():
            self.zone_render_states[zid].pixels = pix

        return merged
    
    def _expand_or_trim_zone(self, val, expected_len):
        """Normalize Color or list[Color] to exact pixel count."""
        if isinstance(val, Color):
            return [val] * expected_len

        pix = list(val[:expected_len])
        if len(pix) < expected_len:
            pix += [Color.black()] * (expected_len - len(pix))
        return pix
    
    def _should_skip_dma(self, merged):
        """Compute hash of merged frame to skip redundant DMA transfers."""
        frame_hash = self._hash_merged_frame(merged)
        if frame_hash == self.last_rendered_frame_hash:
            self.dma_skipped += 1
            return True

        self.last_rendered_frame_hash = frame_hash
        return False
    
    def _render_to_all_strips(self, merged):
        """Render merged frame to every registered ZoneStrip."""
        for strip in self.zone_strips:
            try:
                strip_frame = self._prepare_strip_frame(strip, merged)
                self._validate_strip_frame(strip, strip_frame)
                self._apply_strip_frame(strip, strip_frame)
            except Exception as e:
                log.error(f"Render error on strip {strip}: {e}", exc_info=True)
    
        
    def _prepare_strip_frame(self, strip, merged):
        """Extract only zones belonging to this strip."""
        zone_ids = strip.mapper.all_zone_ids()

        return {
            z: merged.get(z, list(self.zone_render_states[z].pixels))
            for z in zone_ids
        }
    
    def _validate_strip_frame(self, strip, strip_frame):
        """Check lengths, mapping, and hardware buffer size."""
        pixel_count = getattr(strip, "pixel_count", None)
        zone_ids = list(strip_frame.keys())

        log.info(f"Rendering → {strip} ({pixel_count} px), zones={ [z.name for z in zone_ids] }")

        # zone length validation
        for z in zone_ids:
            expected = strip.mapper.get_zone_length(z)
            actual = len(strip_frame[z])
            if expected != actual:
                log.warn(f"LENGTH MISMATCH {z.name} on {strip}: expected {expected}, got {actual}")

            try:
                idx = strip.mapper.get_indices(z)
            except Exception:
                idx = []
            log.debug(f"Zone {z.name}: phys={len(idx)}, sample={idx[:6]}")

        # hardware frame sanity check
        try:
            hw = strip.hardware.get_frame()
            if len(hw) != pixel_count:
                log.warn(f"hardware.get_frame(): {len(hw)} != {pixel_count}")
        except Exception as ex:
            log.debug(f"hardware.get_frame() failed: {ex}", exc_info=True)
    
    def _apply_strip_frame(self, strip, strip_frame):
        """Send pixel data to hardware."""
        log.debug(
            f"Calling show_full_pixel_frame on {strip} with {len(strip_frame)} zones: "
            f"{[z.name for z in strip_frame.keys()]}"
        )
        strip.show_full_pixel_frame(strip_frame)
        log.debug(f"show_full_pixel_frame completed on {strip}")
    # ============================================================
    # Helpers
    # ============================================================

    def _merge_partial_update(self, updates):
        """
        Łączy częściową ramkę z pełnym stanem stref.
        """
        merged = {}

        for zone_id, state in self.zone_render_states.items():
            if zone_id in updates:
                new_val = updates[zone_id]
                if isinstance(new_val, Color):
                    merged[zone_id] = [new_val] * len(state.pixels)
                else:
                    pix = list(new_val[:len(state.pixels)])
                    if len(pix) < len(state.pixels):
                        pix += [Color.black()] * (len(state.pixels) - len(pix))
                    merged[zone_id] = pix
            else:
                merged[zone_id] = list(state.pixels)

        # Debug: log which zones are in merged
        log.debug(f"_merge_partial_update: updates has {len(updates)} zones {list(updates.keys())}, merged has {len(merged)} zones {list(merged.keys())}")

        # Aktualizujemy ZoneRenderState
        for zone_id, pix in merged.items():
            self.zone_render_states[zone_id].pixels = pix

        return merged

    @staticmethod
    def _hash_merged_frame(merged):
        """
        Tworzy szybki hash ramki do DMA skip.
        """
        h = 0
        for zone_id, pix in merged.items():
            for c in pix:
                h = (h * 1315423911) ^ hash(c.to_rgb())
        return h

    # ============================================================
    # Tools
    # ============================================================
                  
    def _apply_zone_state(self, normalized_frame, source):
        """
        Update ZoneRenderState with the full normalized per-zone pixel lists.
        """
        for zone_id, pixels in normalized_frame.items():
            zr = self.zone_render_states.get(zone_id)
            if zr:
                zr.update_pixels(pixels, source)

    def _normalize_to_zone_lengths(self, updates, mapper):
        """
        Normalize logical frame updates into full pixel lists based on actual
        physical zone lengths from mapper.

        updates:
            ZoneID -> Color   (FullStripFrame / ZoneFrame)
            ZoneID -> [Color] (PixelFrame)
        """
        expanded = {}

        for zone_id, value in updates.items():
            length = mapper.get_zone_length(zone_id)

            if length == 0:
                continue

            if isinstance(value, Color):
                # Logical single color → expand to full zone
                expanded[zone_id] = [value] * length

            else:
                # List of Colors → trim or pad
                pix = list(value[:length])
                if len(pix) < length:
                    pix += [Color.black()] * (length - len(pix))
                expanded[zone_id] = pix

        return expanded

    # === Cleanup ===

    def clear_all(self) -> None:
        """Clear all pending frames."""
        for queue in self.main_queues.values():
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


        if cleared_count > 0:
            log.debug(f"Cleared {cleared_count} frames below priority {min_priority.name}")

    def __repr__(self) -> str:
        metrics = self.get_metrics()
        return (
            f"FrameManager(fps={metrics['fps_actual']:.1f}/{metrics['fps_target']}, "
            f"rendered={metrics['frames_rendered']}, "
            f"skipped={metrics['dma_skipped']}, "
            f"dropped={metrics['dropped_frames']})"
        )
