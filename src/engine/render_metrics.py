"""
Render Metrics Collector — Lightweight instrumentation for the rendering pipeline.

Architecture:
  - Pre-allocated ring buffers (array.array) for zero-GC timing data
  - Boolean guard on every hot-path method: `if not self.enabled: return`
  - Single writer (render loop), single reader (MetricsStreamer at 1 Hz)
  - ~100 KB total memory footprint

Usage:
  collector = RenderMetricsCollector()
  collector.enabled = True  # Enable collection (off by default)

  # Hot path — context managers for pipeline stage timing:
  with collector.measure_frame_build_time():
      composite_frame = await self._build_composite_frame()

  # Hot path — counters:
  collector.record_dma_skip()
  collector.record_frame_submitted(zone_id, source)

  # Aggregation (called by MetricsStreamer at 1 Hz):
  snapshot = collector.get_snapshot()
"""

from __future__ import annotations

import time
from array import array
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Generator, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models.enums import FrameSource, ZoneID


# Ring buffer size: 10 seconds @ 60 FPS
RING_SIZE = 600

# Smaller ring for per-animation data (5 seconds)
ANIM_RING_SIZE = 300


class RingBuffer:
    """
    Fixed-size ring buffer using array.array — zero allocation after init.

    Memory: RING_SIZE * 8 bytes (doubles) = ~4.8 KB per buffer.
    All push/read operations are O(1) except mean/max which are O(n).
    """

    __slots__ = ('_buf', '_idx', '_count', '_size')

    def __init__(self, size: int = RING_SIZE):
        self._buf = array('d', [0.0] * size)
        self._idx = 0
        self._count = 0
        self._size = size

    def push(self, value: float) -> None:
        self._buf[self._idx] = value
        self._idx = (self._idx + 1) % self._size
        if self._count < self._size:
            self._count += 1

    def mean(self) -> float:
        if self._count == 0:
            return 0.0
        total = 0.0
        # Iterate only valid entries
        if self._count < self._size:
            for i in range(self._count):
                total += self._buf[i]
        else:
            for i in range(self._size):
                total += self._buf[i]
        return total / self._count

    def max_val(self) -> float:
        if self._count == 0:
            return 0.0
        m = self._buf[0]
        end = self._count if self._count < self._size else self._size
        for i in range(1, end):
            if self._buf[i] > m:
                m = self._buf[i]
        return m

    def last_n(self, n: int) -> List[float]:
        """Return last N values as a new list. Only use in aggregation (allocates)."""
        if self._count == 0:
            return []
        count = min(n, self._count)
        result: List[float] = []
        start = (self._idx - count) % self._size
        for i in range(count):
            result.append(self._buf[(start + i) % self._size])
        return result

    def reset(self) -> None:
        for i in range(self._size):
            self._buf[i] = 0.0
        self._idx = 0
        self._count = 0


@dataclass
class ZoneMetrics:
    """Per-zone metrics counters."""
    frames_produced: int = 0
    frames_rendered: int = 0
    frames_expired: int = 0
    change_count: int = 0
    static_count: int = 0
    last_source: Optional[str] = None


class RenderMetricsCollector:
    """
    Lightweight metrics collection for the render pipeline.

    CRITICAL: Methods called from _render_loop must be O(1) with no allocation.
    Only the aggregation method (get_snapshot) may allocate.
    """

    def __init__(self) -> None:
        self.enabled: bool = False

        # Pipeline stage timing ring buffers
        self.build_times = RingBuffer(RING_SIZE)
        self.merge_times = RingBuffer(RING_SIZE)
        self.write_to_hardware_times = RingBuffer(RING_SIZE)
        self.emit_times = RingBuffer(RING_SIZE)
        self.render_cycle_times = RingBuffer(RING_SIZE)

        # FPS measurement
        self._frame_timestamps = RingBuffer(RING_SIZE)
        self.target_fps: int = 60

        # Global counters
        self.total_frames_rendered: int = 0
        self.total_dma_skipped: int = 0
        self.total_frames_expired: int = 0
        self.total_frames_submitted: int = 0

        # Per-zone metrics (registered once at startup)
        self.zone_metrics: Dict[str, ZoneMetrics] = {}

        # Per-animation counters
        # Key: "ZONE_NAME:AnimClassName"
        self.animation_frame_counts: Dict[str, int] = defaultdict(int)
        self.animation_step_times: Dict[str, RingBuffer] = {}

    # =========================================================================
    # Pipeline stage time measurement
    #
    # Context managers that time the code inside their `with` block.
    # @contextmanager turns a generator into a context manager:
    #   1. Code before `yield` runs on entering `with` (starts timer)
    #   2. The `with` block body executes
    #   3. Code after `yield` runs on exiting `with` (records elapsed time)
    #
    # Usage:
    #   with collector.measure_frame_build_time():
    #       composite_frame = await self._build_composite_frame()
    # =========================================================================

    @contextmanager
    def _measure_time(self, target_buffer: RingBuffer) -> Generator[None, None, None]:
        """Shared timing logic — measures elapsed time and pushes to target ring buffer."""
        if not self.enabled:
            yield
            return
        start = time.perf_counter()
        yield
        target_buffer.push(time.perf_counter() - start)

    def measure_frame_build_time(self) -> contextmanager:
        """Measure composite frame construction time."""
        return self._measure_time(self.build_times)

    def measure_frame_merge_time(self) -> contextmanager:
        """Measure zone render state merge time."""
        return self._measure_time(self.merge_times)

    def measure_frame_write_to_hardware_time(self) -> contextmanager:
        """Measure LED hardware write (DMA transfer) time."""
        return self._measure_time(self.write_to_hardware_times)

    def measure_frame_emit_time(self) -> contextmanager:
        """Measure Socket.IO output frame emit time."""
        return self._measure_time(self.emit_times)

    @contextmanager
    def measure_frame_render_cycle_time(self) -> Generator[None, None, None]:
        """Measure total render cycle time (build + merge + write + emit) and record timestamp."""
        if not self.enabled:
            yield
            return
        start = time.perf_counter()
        yield
        end = time.perf_counter()
        self.render_cycle_times.push(end - start)
        self._frame_timestamps.push(end)
        self.total_frames_rendered += 1

    def record_dma_skip(self) -> None:
        if not self.enabled:
            return
        self.total_dma_skipped += 1

    def record_frame_expired(self) -> None:
        if not self.enabled:
            return
        self.total_frames_expired += 1

    def record_frame_submitted(self, zone_id: "ZoneID", source: "FrameSource") -> None:
        if not self.enabled:
            return
        self.total_frames_submitted += 1
        zm = self.zone_metrics.get(zone_id.name)
        if zm is not None:
            zm.frames_produced += 1
            zm.last_source = source.name

    def record_zone_rendered(self, zone_id: "ZoneID", changed: bool) -> None:
        if not self.enabled:
            return
        zm = self.zone_metrics.get(zone_id.name)
        if zm is not None:
            zm.frames_rendered += 1
            if changed:
                zm.change_count += 1
            else:
                zm.static_count += 1

    def record_zone_frame_expired(self, zone_id: "ZoneID") -> None:
        if not self.enabled:
            return
        zm = self.zone_metrics.get(zone_id.name)
        if zm is not None:
            zm.frames_expired += 1

    def record_animation_step(
        self, zone_id: "ZoneID", anim_name: str, step_time_s: float
    ) -> None:
        if not self.enabled:
            return
        key = f"{zone_id.name}:{anim_name}"
        self.animation_frame_counts[key] += 1
        ring = self.animation_step_times.get(key)
        if ring is None:
            ring = RingBuffer(ANIM_RING_SIZE)
            self.animation_step_times[key] = ring
        ring.push(step_time_s)

    # =========================================================================
    # Registration (called once at startup)
    # =========================================================================

    def register_zone(self, zone_id: "ZoneID") -> None:
        if zone_id.name not in self.zone_metrics:
            self.zone_metrics[zone_id.name] = ZoneMetrics()

    def set_target_fps(self, fps: int) -> None:
        """
        Called by FrameManager.set_fps() when the target FPS changes at runtime.

        Resets the frame-timestamp ring buffer so the measured FPS converges
        to the new value within 2 frames instead of waiting for old timestamps
        to age out of the sliding window (which could take minutes at low FPS).
        """
        self.target_fps = fps
        self._frame_timestamps.reset()

    # =========================================================================
    # Aggregation (called by MetricsStreamer at 1 Hz — may allocate)
    # =========================================================================

    def get_actual_fps(self) -> float:
        """
        Calculate actual FPS using a 3-second sliding time window.

        Using a time window (rather than a fixed sample count) means the
        measurement converges within ~3 seconds after any FPS change.
        A count-based window (e.g. last_n(120)) would take minutes to
        converge when switching from 60 FPS down to 1 FPS, because the
        ring buffer stays full of old high-frequency timestamps.
        """
        now = time.perf_counter()
        window_start = now - 3.0

        # Pull enough recent samples to cover 3 s at maximum FPS (240 fps × 3 s = 720,
        # capped by ring size RING_SIZE=600).
        all_samples = self._frame_timestamps.last_n(RING_SIZE)
        recent = [t for t in all_samples if t >= window_start]

        if len(recent) < 2:
            # Window is nearly empty (very low FPS or just started).
            # Fall back to the last two timestamps to avoid showing 0 indefinitely.
            fallback = self._frame_timestamps.last_n(2)
            if len(fallback) < 2:
                return 0.0
            duration = fallback[-1] - fallback[0]
            return (1 / duration) if duration > 0 else 0.0

        duration = recent[-1] - recent[0]
        if duration <= 0:
            return 0.0
        return (len(recent) - 1) / duration

    def get_snapshot(self) -> dict:
        """Build a complete metrics snapshot for streaming to frontend."""
        return {
            "fps": {
                "actual": round(self.get_actual_fps(), 1),
            },
            "pipeline": {
                "build_avg_ms": round(self.build_times.mean() * 1000, 3),
                "merge_avg_ms": round(self.merge_times.mean() * 1000, 3),
                "write_to_hardware_avg_ms": round(self.write_to_hardware_times.mean() * 1000, 3),
                "emit_avg_ms": round(self.emit_times.mean() * 1000, 3),
                "render_cycle_avg_ms": round(self.render_cycle_times.mean() * 1000, 3),
                "build_max_ms": round(self.build_times.max_val() * 1000, 3),
                "merge_max_ms": round(self.merge_times.max_val() * 1000, 3),
                "write_to_hardware_max_ms": round(self.write_to_hardware_times.max_val() * 1000, 3),
                "emit_max_ms": round(self.emit_times.max_val() * 1000, 3),
                "render_cycle_max_ms": round(self.render_cycle_times.max_val() * 1000, 3),
                # Historical data for sparklines (last 60 samples)
                "build_history": [round(v * 1000, 2) for v in self.build_times.last_n(60)],
                "write_to_hardware_history": [round(v * 1000, 2) for v in self.write_to_hardware_times.last_n(60)],
                "render_cycle_history": [round(v * 1000, 2) for v in self.render_cycle_times.last_n(60)],
            },
            "counters": {
                "frames_rendered": self.total_frames_rendered,
                "dma_skipped": self.total_dma_skipped,
                "frames_expired": self.total_frames_expired,
                "frames_submitted": self.total_frames_submitted,
                "redundant_ratio": round(
                    self.total_dma_skipped
                    / max(1, self.total_frames_rendered + self.total_dma_skipped),
                    3,
                ),
            },
            "zones": {
                zone_name: {
                    "produced": zm.frames_produced,
                    "rendered": zm.frames_rendered,
                    "expired": zm.frames_expired,
                    "change_count": zm.change_count,
                    "static_count": zm.static_count,
                    "change_ratio": round(
                        zm.change_count / max(1, zm.change_count + zm.static_count),
                        3,
                    ),
                    "last_source": zm.last_source,
                }
                for zone_name, zm in self.zone_metrics.items()
            },
            "animations": {
                key: {
                    "frames_produced": count,
                    "avg_step_ms": round(
                        self.animation_step_times[key].mean() * 1000, 3
                    )
                    if key in self.animation_step_times
                    else 0,
                    "max_step_ms": round(
                        self.animation_step_times[key].max_val() * 1000, 3
                    )
                    if key in self.animation_step_times
                    else 0,
                }
                for key, count in self.animation_frame_counts.items()
            },
            "timestamp": time.perf_counter(),
        }

    def reset(self) -> None:
        """Reset all counters and ring buffers."""
        self.total_frames_rendered = 0
        self.total_dma_skipped = 0
        self.total_frames_expired = 0
        self.total_frames_submitted = 0

        self.build_times.reset()
        self.merge_times.reset()
        self.write_to_hardware_times.reset()
        self.emit_times.reset()
        self.render_cycle_times.reset()
        self._frame_timestamps.reset()

        for zm in self.zone_metrics.values():
            zm.frames_produced = 0
            zm.frames_rendered = 0
            zm.frames_expired = 0
            zm.change_count = 0
            zm.static_count = 0

        self.animation_frame_counts.clear()
        self.animation_step_times.clear()
