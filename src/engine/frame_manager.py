"""
FrameManager — Centralized rendering system with priority queues and multiple led channel support.

Architecture:
  - Collects frames from multiple sources (animations, transitions, static)
  - Maintains separate priority queues for led channels
  - Selects highest-priority frame each render tick
  - Renders atomically to all registered led channels
  - Supports pause/step/FPS control for debugging

Priority System:
  IDLE (0) < MANUAL (10) < PULSE (20) < ANIMATION (30) < TRANSITION (40) < DEBUG (50)

Only the highest-priority frame is rendered. When high-priority sources stop,
rendering automatically falls back to lower priorities.
"""

from __future__ import annotations
import asyncio
import time
from collections import deque
from typing import Dict, List, Optional, Deque, cast, TYPE_CHECKING

from models.domain.output_frame import OutputFrame
from utils.logger import get_logger
from models.enums import FrameSource, LogCategory, FramePriority, ZoneID
from models.color import Color
from models.frame import (
    SingleZoneFrame, MultiZoneFrame, 
    PixelFrame, CompositeFrame, ZoneUpdateValue
)
from hardware.led.led_channel import LedChannel
from engine.zone_render_state import ZoneRenderState
from time import perf_counter

if TYPE_CHECKING:
    from services.app_clock import AppClock
    from services.frame_streamer import FrameStreamer

log = get_logger().for_category(LogCategory.FRAME_MANAGER)

class WS2811Timing:
    """
    WS2811 protocol timing requirements for 90-pixel led_channel.

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
    - Priority-based frame selection
    - Frame submission from multiple sources
    - Atomic rendering to multiple led channels
    - Pause/step/FPS control
    - Frame expiration (TTL)
    - Performance metrics
    """

    def __init__(
        self,
        fps: int = 60,
        app_clock: Optional["AppClock"] = None,
        frame_streamer: Optional["FrameStreamer"] = None
    ):
        """
        Initialize FrameManager.

        Args:
            fps: Target render frequency (1-240, default 60)
            app_clock: Global application clock for time synchronization
            frame_streamer: Frame streamer for Socket.IO output
        """

        self.fps = max(1, min(fps, 240))
        self.app_clock = app_clock
        self.frame_streamer = frame_streamer

        # DQueue system
        # maxlen=10 allows all zones to queue frames before draining
        # (we have max 10 zones, some animating concurrently)
        self.priority_queues: Dict[int, Deque[CompositeFrame]] = {
            p.value: deque(maxlen=10)
            for p in FramePriority
            if isinstance(p.value, int)
        }

        # Registered render targets
        self.led_channels: List[LedChannel] = [] 
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

        self.last_rendered_frame: Optional[CompositeFrame] = None
        self.last_rendered_frame_hash = None

        # Async lock for frame submission safety
        self._lock = asyncio.Lock()

        self._perf_acc = {
            "build": 0.0,
            "merge": 0.0,
            "hw": 0.0,
            "emit": 0.0,
        }
        self._perf_frames = 0
        self._perf_last_log = perf_counter()


        log.info(
            "FrameManager initialized",
            fps=self.fps,
            timing=f"min={WS2811Timing.MIN_FRAME_TIME_MS:.2f}ms",
        )

    # === Led Channel Registration (for controllers) ===

    def register_led_channel(self, led_channel: LedChannel) -> None:
        """Register a led channel."""

        if led_channel in self.led_channels:
            log.warn(f"Skipping registering led channel in FrameManager - already registered")
            return

        self.led_channels.append(led_channel)
           
        # Initialize zone render states for all zones in this led_channel
        led_channel_zone_ids = led_channel.mapper.all_zone_ids()
        log.info(f"Registering led_channel with {len(led_channel_zone_ids)} zones ({[z.name for z in led_channel_zone_ids]}) registered in FrameManager")

        for zone_id in led_channel_zone_ids:
            if zone_id not in self.zone_render_states:
                zone_length = led_channel.mapper.get_zone_length(zone_id)
                self.zone_render_states[zone_id] = ZoneRenderState(
                    zone_id=zone_id,
                    pixels=[Color.black()] * zone_length,
                )
                log.debug(f"Initialized black render state for zone {zone_id.name} ({zone_length} pixels)")

        log.info(f"Registered led channel: {led_channel} (total zone_render_states now has {len(self.zone_render_states)} zones)")
        
    def unregister_led_channel(self, led_channel: LedChannel) -> None:
        """Unregister a led channel."""
        
        if led_channel in self.led_channels:
            self.led_channels.remove(led_channel)
            log.debug(f"Removed led channel: {led_channel}")

    # === Frame Submission API (Type-Specific) ===
    
    async def push_frame(self, frame):
        """
        Unified API endpoint.
        Accepts SingleZoneFrame / MultiZoneFrame / PixelFrame
        and wraps them into CompositeFrame for the queue system.
        """

        # log.debug(f"FrameManager.push_frame: received {type(frame).__name__} from {getattr(frame, 'source', '?')} "
        #    f"priority={getattr(frame, 'priority', '?')} zone={getattr(frame, 'zone_id', '?')}")

        # --- SingleZoneFrame ----------------------------------
        if isinstance(frame, SingleZoneFrame):
            msf = CompositeFrame(
                priority=frame.priority,
                ttl=frame.ttl,
                source=frame.source,
                updates=cast(Dict[ZoneID, ZoneUpdateValue], {frame.zone_id: frame.color}),
            )
            
        # --- MultiZoneFrame -----------------------------------
        elif isinstance(frame, MultiZoneFrame):
            msf = CompositeFrame(
                priority=frame.priority,
                ttl=frame.ttl,
                source=frame.source,
                updates=cast(Dict[ZoneID, ZoneUpdateValue], frame.zone_colors),     # dict[ZoneID, Color]
            )
        
        # --- PixelFrame --------------------------------------
        elif isinstance(frame, PixelFrame):
            msf = CompositeFrame(
                priority=frame.priority,
                ttl=frame.ttl,
                source=frame.source,
                updates=cast(Dict[ZoneID, ZoneUpdateValue], frame.zone_pixels),
            )
        
        else:
            raise TypeError(f"Unsupported frame type: {type(frame)}")
 
        self.priority_queues[msf.priority.value].append(msf)

    # === Control API ===

    def pause(self) -> None: 
        self.paused = True

    def resume(self) -> None: 
        self.paused = False

    def step_frame(self) -> None: 
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

        log.info(
            "FrameManager stopped",
            frames_rendered=self.frames_rendered,
            dropped_frames=self.dropped_frames,
        )

    async def shutdown(self) -> None:
        """Cleanup and shutdown FrameManager resources."""
        await self.stop()
        
        log.info("FrameManager shutdown complete")

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
            "pending": sum(len(q) for q in self.priority_queues.values()),
        }


    # === Core Render Loop ===

    async def _render_loop(self) -> None:
        """Main render loop @ target FPS."""
        log.info(f"Render loop @ {self.fps} FPS (delay={1000/self.fps:.2f}ms)")

        frame_period = 1.0 / self.fps
        min_frame_time = max(frame_period, WS2811Timing.MIN_FRAME_TIME_MS / 1000)

        # Absolute timeline: each frame targets an exact time, not relative to previous frame end
        next_frame_time = time.perf_counter()

        while self.running:
            # Handle pause/step
            if self.paused and not self.step_requested:
                await asyncio.sleep(0.01)
                continue

            # === SLEEP UNTIL NEXT FRAME (RPi-optimized) ===
            while True:
                now = time.perf_counter()
                remaining = next_frame_time - now

                if remaining <= 0:
                    break  # Frame is due (or overdue)
                elif remaining > 0.003:
                    # Far from target: sleep 1ms chunks
                    await asyncio.sleep(0.001)
                elif remaining > 0.001:
                    # Close: yield to event loop (let animations run!)
                    await asyncio.sleep(0)
                else:
                    # Final 1ms: minimal busy-wait for precision
                    # (longer busy-wait blocks event loop → starves animation tasks)
                    while time.perf_counter() < next_frame_time:
                        pass
                    break

            # === RENDER FRAME ===
            try:
                t0 = perf_counter()
                composite_frame = await self._build_composite_frame()
                t1 = perf_counter()
                self._perf_acc["build"] += (t1 - t0)

                # Render atomically, but skip DMA if main frame hasn't changed
                # (Phase 2 optimization: 95% DMA reduction in static-only mode)
                if composite_frame is not None:
                    # Frame changed (different object) → do full render with hardware DMA
                    await self._render_frame(composite_frame)

            except Exception as e:
                log.error(f"Render error: {e}", exc_info=True)

            finally:
                self.step_requested = False

                # Advance to next frame on absolute timeline (no drift accumulation)
                next_frame_time += min_frame_time

                # Update last_show_time for compatibility (e.g., metrics, external readers)
                self.last_show_time = time.perf_counter()
                
                now = perf_counter()
                if now - self._perf_last_log >= 1.0 and self._perf_frames > 0:
                    f = self._perf_frames
                    log.warn(
                        message="PERF 1s | fps=%d | build=%.2fms | merge=%.2fms | hw=%.2fms | emit=%.2fms",
                        f=f,
                        build=(self._perf_acc["build"] / f) * 1000,
                        merge=(self._perf_acc["merge"] / f) * 1000,
                        hw=(self._perf_acc["hw"] / f) * 1000,
                        emit=(self._perf_acc["emit"] / f) * 1000,
                    )
                    self._perf_acc = {k: 0.0 for k in self._perf_acc}
                    self._perf_frames = 0
                    self._perf_last_log = now

    # === Frame Selection ===

    async def _build_composite_frame(self) -> Optional[CompositeFrame]:
        """
        Drain and merge frames from all priority queues.

        Strategy:
        1. Collect ANIMATION frames (continuous animation source)
        2. Overlay higher priorities (PULSE, TRANSITION, DEBUG)
        3. Fill gaps with lower priorities (MANUAL, IDLE) for zones without animations

        Result: Complete frame with animations, overlays, and fallbacks merged intelligently.
        """
        async with self._lock:
            queues_snapshot = {
                priority: deque(queue)
                for priority, queue in self.priority_queues.items()
            }
            
            for queue in self.priority_queues.values():
                queue.clear()
            
        merged_updates: Dict[ZoneID, ZoneUpdateValue] = {}
        highest_priority: Optional[FramePriority] = None
        ttl = 0.0
        source: Optional[FrameSource] = None

        # 1. Always collect ANIMATION first (base layer - continuous animations)
        anim_queue = queues_snapshot.get(FramePriority.ANIMATION.value)
        if anim_queue:
            while anim_queue:
                frame = anim_queue.popleft()
                if frame.is_expired():
                    continue
                
                merged_updates.update(frame.updates)
                ttl = max(ttl, frame.ttl)
                source = source or frame.source
                highest_priority = FramePriority.ANIMATION

        # 2. Apply overlays (PULSE, DEBUG, TRANSITION - higher priority than ANIMATION)
        for priority_value in sorted(queues_snapshot.keys(), reverse=True):
            if priority_value <= FramePriority.ANIMATION.value:
                continue  # Will handle lower priorities separately

            queue = queues_snapshot[priority_value]
            while queue:
                frame = queue.popleft()
                if frame.is_expired():
                    continue
                
                merged_updates.update(frame.updates) # Override ANIMATION for this zone
                ttl = max(ttl, frame.ttl)
                source = source or frame.source
                highest_priority = frame.priority

        # 3. Fill gaps with lower priorities (MANUAL for static zones, IDLE fallback)
        for priority_value in sorted(queues_snapshot.keys()):
            if priority_value >= FramePriority.ANIMATION.value:
                continue  # Already handled above

            queue = queues_snapshot[priority_value]
            while queue:
                frame = queue.popleft()
                if frame.is_expired():
                    continue
                
                # Only fill zones that don't have updates yet
                for zid, val in frame.updates.items():
                    merged_updates.setdefault(zid, val)
                    
                    # if zid not in merged_updates:
                    #     merged_updates[zid] = val
                ttl = max(ttl, frame.ttl)
                source = source or frame.source
                # Update highest_priority if this is our first frame
                highest_priority = highest_priority or frame.priority

        if not merged_updates or not source:
            return None

        return CompositeFrame(
            priority=highest_priority or FramePriority.ANIMATION,
            ttl=ttl or 0.1,
            source=source,
            updates=merged_updates,
        )        

    async def _select_frame_by_priority(self) -> Optional[CompositeFrame]:
        """
        Select highest-priority non-expired frame from main queues.
        Priority order: DEBUG > TRANSITION > PULSE > ANIMATION > MANUAL > IDLE

        Returns:
            CompositeFrame with highest priority, or None if all expired/empty
        """
        async with self._lock:
            # Iterate from highest to lowest priority
            for priority_value in sorted(self.priority_queues.keys(), reverse=True):
                queue = self.priority_queues[priority_value]
                while queue:
                    frame = queue.popleft()
                    if not frame.is_expired():
                        return frame
                    # Expired frame discarded, try next

        return None

    def _build_output_frame(self) -> OutputFrame:
        """
        Build an immutable OutputFrame representing the current rendered state.
        Must be called AFTER merge + normalization.
        """
        # Use global app clock for time synchronization
        t = self.app_clock.now() if self.app_clock else time.perf_counter()

        # Build snapshot - create NEW lists (immutable)
        zones: Dict[ZoneID, List[Color]] = {
            zone_id: list(state.pixels)
            for zone_id, state in self.zone_render_states.items()
        }

        return OutputFrame(t=t, zones=zones)

    async def _emit_output_frame(self, output_frame: OutputFrame) -> None:
        """
        Emit output frame to registered consumers (streaming, recording, etc.).
        """
        if self.frame_streamer:
            await self.frame_streamer.emit(output_frame)

    # === Rendering ===

    async def _render_frame(self, frame: CompositeFrame) -> None:
        """High-level render pipeline."""
        t_merge0 = perf_counter()
        updates = frame.updates
        merged = self._merge_updates(frame, updates)
        t_merge1 = perf_counter()
        self._perf_acc["merge"] += (t_merge1 - t_merge0)
        

        if self._should_skip_dma(merged):
            return


        t_hw0 = perf_counter()
        self._render_to_hardware(merged)
        t_hw1 = perf_counter()
        self._perf_acc["hw"] += (t_hw1 - t_hw0)

        self.frames_rendered += 1
        self.frame_times.append(time.perf_counter())


        t_emit0 = perf_counter()
        output_frame = self._build_output_frame()
        if self.frame_streamer:
            self.frame_streamer.push(output_frame)
        t_emit1 = perf_counter()
        self._perf_acc["emit"] += (t_emit1 - t_emit0)
        
        # Build output frame for streaming/recording
        # output_frame = self._build_output_frame()
        #await self._emit_output_frame(output_frame)
        
        self._perf_frames += 1
        
    def _merge_updates(self, frame: CompositeFrame, updates: Dict[ZoneID, ZoneUpdateValue]):
        """Merge frame updates into zone_render_states."""
        return self._merge_full_update(updates)
    
    # def _expand_or_trim_zone(self, val, expected_len):
    #     """Normalize Color or list[Color] to exact pixel count."""
    #     if isinstance(val, Color):
    #         return [val] * expected_len

    #     pix = list(val[:expected_len])
    #     if len(pix) < expected_len:
    #         pix += [Color.black()] * (expected_len - len(pix))
    #     return pix
    
    def _should_skip_dma(self, merged):
        """Compute hash of merged frame to skip redundant DMA transfers."""
        frame_hash = self._hash_merged_frame(merged)
        if frame_hash == self.last_rendered_frame_hash:
            self.dma_skipped += 1
            return True

        self.last_rendered_frame_hash = frame_hash
        return False
    
    def _render_to_hardware(self, merged):
        """Render merged frame to every registered LedChannel."""
        for led_channel in self.led_channels:
            try:
                led_channel_frame = self._prepare_led_channel_frame(led_channel, merged)
                self._validate_led_channel_frame(led_channel, led_channel_frame)
                self._apply_led_channel_frame(led_channel, led_channel_frame)
            except Exception as e:
                log.error(f"Render error on led_channel {led_channel}: {e}", exc_info=True)
    
        
    def _prepare_led_channel_frame(self, led_channel: LedChannel, merged):
        """Extract only zones belonging to this led_channel."""
        zone_ids = led_channel.mapper.all_zone_ids()

        return {
            z: merged.get(z, list(self.zone_render_states[z].pixels))
            for z in zone_ids
        }
    
    def _validate_led_channel_frame(self, led_channel: LedChannel, led_channel_frame):
        """Check lengths, mapping, and hardware buffer size."""
        pixel_count = getattr(led_channel, "pixel_count", None)
        zone_ids = list(led_channel_frame.keys())

        # log.debug(f"Rendering → {led_channel} ({pixel_count} px), zones={ [z.name for z in zone_ids] }")

        # zone length validation
        for z in zone_ids:
            expected = led_channel.mapper.get_zone_length(z)
            actual = len(led_channel_frame[z])
            if expected != actual:
                log.warn(f"LENGTH MISMATCH {z.name} on {led_channel}: expected {expected}, got {actual}")

            try:
                idx = led_channel.mapper.get_indices(z)
            except Exception:
                idx = []
            # log.debug(f"Zone {z.name}: phys={len(idx)}, sample={idx[:6]}")

        # hardware frame sanity check
        try:
            hw = led_channel.hardware.get_frame()
            if len(hw) != pixel_count:
                log.warn(f"hardware.get_frame(): {len(hw)} != {pixel_count}")
        except Exception as ex:
            log.debug(f"hardware.get_frame() failed: {ex}", exc_info=True)
    
    def _apply_led_channel_frame(self, led_channel: LedChannel, led_channel_frame: Dict[ZoneID, List[Color]]):
        """Send pixel data to hardware."""
        
        for zone_id, pixels in led_channel_frame.items():
            if not pixels:
                continue

            # take first pixel from zone
            c = pixels[0]
            (r, g, b) = c.to_rgb()
            
        led_channel.show_full_pixel_frame(led_channel_frame)
        # log.debug(f"show_full_pixel_frame completed on {led_channel}")
    
    
    # ============================================================
    # Helpers
    # ============================================================

    def _normalize_zone_pixels(self, val, expected_len) -> List[Color]:
        if isinstance(val, Color):
            return [val] * expected_len
        pix = list(val[:expected_len])
        if len(pix) < expected_len:
            pix += [Color.black()] * (expected_len - len(pix))
        return pix

    def _merge_full_update(self, updates):
        """
        Merge updates into zone_render_states, preserving previous state for missing zones.

        Note: By the time this is called, _build_composite_frame() has already composed
        all sources (animation + static + overlays) into a single CompositeFrame.
        The frame is effectively "full" by construction — missing zones mean no source
        produced a frame for them this tick, so preserving previous state is correct.

        The partial/full distinction from BaseFrame is lost during CompositeFrame
        conversion (CompositeFrame has no partial field) and is irrelevant here
        because the 3-phase merge in _build_composite_frame already handles
        source priority and gap filling.
        """
        merged = {}

        for zone_id, state in self.zone_render_states.items():
            if zone_id in updates:
                merged[zone_id] = self._normalize_zone_pixels(updates[zone_id], len(state.pixels))
            else:
                merged[zone_id] = list(state.pixels)

        for zid, pix in merged.items():
            self.zone_render_states[zid].pixels = pix

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

    # === Cleanup ===

    def clear_all(self) -> None:
        """Clear all pending frames."""
        for queue in self.priority_queues.values():
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
        for priority_value, queue in list(self.priority_queues.items()):
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
