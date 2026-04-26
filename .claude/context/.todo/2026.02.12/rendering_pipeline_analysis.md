# Deep Analysis: Diuna Rendering Pipeline & FPS Metrics System Design

**Date:** 2026-02-12
**Analyzed by:** Claude Opus 4.6 + 3 specialized agents (rpi-hardware-expert, architecture-expert, backend-expert)

## Context

This document provides a comprehensive analysis of the Diuna LED rendering pipeline — from frame production through priority merging to hardware output and Socket.IO streaming. It identifies bugs, architectural flaws, and design strengths, then proposes a precise FPS calculation/metrics system and targeted repairs.

---

## 1. RENDERING PIPELINE OVERVIEW

### Complete Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│  FRAME PRODUCERS (async tasks, run at max speed)             │
│                                                              │
│  AnimationEngine._run_loop()  ──┐                            │
│    ├─ BreatheAnimation.step()   │  await sleep(0) = ~1000+   │
│    ├─ SnakeAnimation.step()     │  frames/sec per zone       │
│    ├─ ColorSnakeAnimation.step()│                            │
│    └─ ColorFadeAnimation.step() │                            │
│                                 │                            │
│  StaticModeController ──────────┤  Event-driven (on change)  │
│  SelectedZoneIndicator ─────────┤  ~48 steps/0.5s cycle      │
│  TransitionService ─────────────┤  15-30 steps burst         │
│  FramePlaybackController ───────┘  Manual (keyboard)         │
└──────────────────────────────────────────────────────────────┘
                         │
                    push_frame()
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  PRIORITY QUEUES (deque maxlen=10 per priority level)        │
│                                                              │
│    DEBUG (50)      → deque[CompositeFrame]                   │
│    TRANSITION (40) → deque[CompositeFrame]                   │
│    PULSE (30)      → deque[CompositeFrame]                   │
│    ANIMATION (20)  → deque[CompositeFrame]                   │
│    MANUAL (10)     → deque[CompositeFrame]                   │
│    IDLE (0)        → deque[CompositeFrame]                   │
└──────────────────────────────────────────────────────────────┘
                         │
               _render_loop() @ 60 FPS
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
   _build_composite_frame()    Smart sleep strategy
   (3-phase merge)             (1ms chunks → yield → busy-wait)
              │
              ▼
┌──────────────────────────────────────────────────────────────┐
│  _render_frame() PIPELINE                                    │
│                                                              │
│  1. _merge_updates() → normalize Color/List[Color] to       │
│     List[Color] per zone, update zone_render_states          │
│  2. _should_skip_dma() → hash frame, skip if unchanged      │
│  3. _render_to_hardware() → for each LedChannel:            │
│       _prepare_led_channel_frame() → filter zones            │
│       _validate_led_channel_frame() → check lengths          │
│       _apply_led_channel_frame() → show_full_pixel_frame()   │
│  4. _build_output_frame() → snapshot zone_render_states      │
│  5. frame_streamer.push() → queue for Socket.IO              │
└──────────────────────────────────────────────────────────────┘
                    │                        │
                    ▼                        ▼
           LedChannel.show_full_     FrameStreamer._loop()
           pixel_frame()              @ 30 FPS
                    │                        │
                    ▼                        ▼
           WS281xStrip.apply_frame() Socket.IO emit
           + pixel_strip.show()      "output_frame"
           (DMA ~2.7ms)             to /frames namespace
```

---

## 2. CLASS-BY-CLASS ANALYSIS

### 2.1 Frame Types (`src/models/frame.py`)

| Type | Fields | Used By | Priority | TTL |
|------|--------|---------|----------|-----|
| `SingleZoneFrame` | `zone_id`, `color` | Breathe, ColorFade, Static, Pulse | MANUAL/ANIMATION/PULSE | 0.1-10s |
| `MultiZoneFrame` | `zone_colors: Dict[ZoneID, Color]` | Static init (batch) | MANUAL | 10s |
| `PixelFrame` | `zone_pixels: Dict[ZoneID, List[Color]]` | Snake, ColorSnake, Transition, Debug | ANIMATION/TRANSITION/DEBUG | 0.12-10s |
| `CompositeFrame` | `updates: Dict[ZoneID, Union[Color, List[Color]]]` | FrameManager internal only | any | any |

### 2.2 FrameManager (`src/engine/frame_manager.py`, 745 lines)

**Responsibilities**: Frame queuing, priority merge, render loop timing, DMA skip, hardware dispatch, streaming output.

**Render loop timing**: Absolute timeline with 3-stage sleep (1ms chunks > yield > busy-wait). Targets 60 FPS = 16.67ms period, minimum 2.75ms for WS2811 DMA.

**Priority merge** (`_build_composite_frame`):
1. Collect ANIMATION base layer
2. Overlay PULSE/TRANSITION/DEBUG (overrides animation zones)
3. Fill gaps with MANUAL/IDLE (static zones)

### 2.3 AnimationEngine (`src/animations/engine.py`)

**Pattern**: One asyncio.Task per zone. Task calls `animation.step()` in a tight loop with `await asyncio.sleep(0)`. Forwards frames to FrameManager immediately.

### 2.4 ZoneRenderState (`src/engine/zone_render_state.py`)

**Purpose**: Ephemeral per-zone pixel buffer. Source of truth for "what's currently displayed".

### 2.5 FrameStreamer (`src/services/frame_streamer.py`)

**Pattern**: Deque(maxlen=2) buffer, async loop at 30 FPS. Takes latest frame, serializes to JSON, emits via Socket.IO.

### 2.6 Animations

All inherit `BaseAnimation`, implement `async def step() -> SingleZoneFrame | PixelFrame | None`.

| Animation | Frame Type | Movement Model | Speed Param Used? |
|-----------|-----------|----------------|-------------------|
| Breathe | SingleZoneFrame | Time-based (sin wave from elapsed) | YES (controls period) |
| ColorFade | SingleZoneFrame | Time-based (elapsed / period) | YES (controls period) |
| Snake | PixelFrame | **Position-based (++per step)** | **NO (TODO in code)** |
| ColorSnake | PixelFrame | **Position-based (++per step)** | **NO (TODO in code)** |

---

## 3. IDENTIFIED BUGS & FLAWS

### BUG-1: Clock Mismatch in Frame Expiration (CRITICAL)

**File**: `src/models/frame.py:33-38` vs `src/models/frame.py:113-116`

`BaseFrame` uses `time.time()` for timestamp and expiration check:
```python
timestamp: float = field(default_factory=time.time)
def is_expired(self) -> bool:
    return (time.time() - self.timestamp) > self.ttl
```

`CompositeFrame` uses `time.monotonic()`:
```python
created_at: float = field(default_factory=time.monotonic)
def is_expired(self) -> bool:
    return (time.monotonic() - self.created_at) > self.ttl
```

**Impact**: `BaseFrame.is_expired()` is never actually called (frames are converted to CompositeFrame before queuing). But `BaseFrame.timestamp` field is wasted memory. More importantly, if NTP adjusts the wall clock, `time.time()` jumps — `time.monotonic()` is correct for TTL. This is a **correctness issue** and **API inconsistency**.

**Fix**: Standardize on `time.monotonic()` everywhere.

---

### BUG-2: Race Condition in push_frame vs _build_composite_frame (MEDIUM)

**File**: `src/engine/frame_manager.py:184` vs `src/engine/frame_manager.py:392`

`push_frame()` appends to queue **without acquiring** `self._lock`:
```python
async def push_frame(self, frame):
    ...
    self.priority_queues[msf.priority.value].append(msf)  # No lock!
```

`_build_composite_frame()` **does acquire** `self._lock` to snapshot+clear queues:
```python
async with self._lock:
    queues_snapshot = {priority: deque(queue) for ...}
    for queue in self.priority_queues.values():
        queue.clear()
```

**Impact**: A frame can be pushed between snapshot and clear, causing it to be lost. In practice, deque operations are GIL-protected in CPython and this is single-threaded asyncio, so the race is unlikely. But it's architecturally incorrect.

**Fix**: Either remove the lock entirely (single-threaded asyncio doesn't need it) or make push_frame also use the lock.

---

### BUG-3: Animation Speed Coupled to Frame Production Rate (HIGH)

**Files**: `src/animations/snake.py:70`, `src/animations/color_snake.py:110`

Snake animations advance `_position += 1` on every `step()` call. Since `step()` runs as fast as possible (~thousands/sec), the snake moves at **thousands of positions per second** — far faster than intended.

The TODO comments confirm this is known:
```python
# TODO: Decouple movement speed from frame rate
# Should render at 60 FPS but move snake position based on speed parameter
```

**Impact**: Snake speed is uncontrollable and hardware-dependent. On faster hardware, snakes move faster.

**Fix**: Use elapsed-time-based position calculation:
```python
async def step(self):
    elapsed = time.monotonic() - self._start_time
    speed_factor = self._calculate_delay()
    self._position = int(elapsed / speed_factor) % pixel_count
```

---

### BUG-4: Massive Frame Overproduction & Silent Dropping (MEDIUM)

**File**: `src/animations/engine.py:232`, `src/engine/frame_manager.py:104`

Animations run `await asyncio.sleep(0)` producing ~1000+ frames/sec per zone. Queues have `maxlen=10`. When deque is full, oldest frames are silently dropped by Python's deque.

**Impact**: ~94% of computed frames are wasted (1000 produced, ~60 consumed). CPU cycles spent on:
- `animation.step()` computation (pixel arrays, trig functions)
- `CompositeFrame` construction
- `deque.append()` (silently drops oldest)

**Metrics impact**: No way to know actual production rate, drop rate, or queue pressure.

**Fix**: Either throttle animation production to ~60-120 FPS (2x render target), or add metrics tracking production/drop rates.

---

### BUG-5: `_perf_frames` Not Incremented on DMA Skip (LOW)

**File**: `src/engine/frame_manager.py:521-522,545`

When `_should_skip_dma()` returns True, `_render_frame()` returns early at line 522, skipping `self._perf_frames += 1` at line 545. This makes the PERF log undercount frames in static mode.

**Fix**: Move `_perf_frames += 1` before the DMA skip check.

---

### BUG-6 (FIXED): `_merge_partial_update` was dead code

**File**: `src/engine/frame_manager.py`

`_merge_partial_update` was identical to `_merge_full_update` — both preserved previous state for missing zones. The `partial` flag from `BaseFrame` was never propagated to `CompositeFrame` (lost during `push_frame()` conversion), so `_merge_partial_update` was unreachable.

**Resolution**: Removed `_merge_partial_update` and the dead dispatch in `_merge_updates()`. This is NOT a regression — by the time `_merge_updates` is called, `_build_composite_frame()` has already composed all sources via the 3-phase merge, making the frame effectively "full" by construction. Preserving previous state for missing zones is correct because missing zones mean no source produced a frame this tick.

---

### BUG-7: `dropped_frames` Counter Never Incremented (LOW)

**File**: `src/engine/frame_manager.py:123`

`self.dropped_frames = 0` is initialized but never incremented anywhere. Late frames are handled by advancing the absolute timeline, but the counter isn't updated.

**Fix**: Detect and count late frames in the render loop.

---

### BUG-8: Dead Code in `_apply_led_channel_frame` (TRIVIAL)

**File**: `src/engine/frame_manager.py:628-631`

```python
for zone_id, pixels in led_channel_frame.items():
    if not pixels: continue
    c = pixels[0]
    (r, g, b) = c.to_rgb()  # Extracted but never used
```

**Fix**: Remove dead code.

---

## 4. DESIGN STRENGTHS

1. **Priority-based compositing**: Elegant 3-phase merge allows concurrent producers without coordination. Transitions naturally override animations, pulse overlays naturally override animations for specific zones.

2. **DMA skip optimization**: Frame hashing prevents redundant hardware writes — 95% DMA reduction in static mode. Critical for RPi GPIO/DMA efficiency.

3. **Absolute timeline**: `next_frame_time += min_frame_time` prevents drift accumulation. Even if one frame takes longer, subsequent frames stay on schedule.

4. **RPi-optimized sleep strategy**: 3-stage sleep (1ms → yield → busy-wait) works around kernel timer granularity (~10ms) while preserving event loop responsiveness for animation tasks.

5. **Clean separation of concerns**: Producers know nothing about hardware. FrameManager handles priority, timing, and dispatch. LedChannel handles zone-to-pixel mapping. WS281xStrip handles color order and DMA.

6. **Zone render state tracking**: Separate ephemeral render state from persisted domain state enables frame change detection and fallback logic without polluting the domain model.

---

## 5. DESIGN WEAKNESSES

1. **No frame metrics at all**: No production rate tracking, no queue pressure, no drop counting, no per-stage timing exposed to API/frontend.

2. **Massive CPU waste from overproduction**: Animations compute frames ~16x faster than needed. On RPi4, this is real CPU cost (pixel array allocation, trig, Color construction).

3. **WS2811Timing hardcoded**: `PIXEL_COUNT = 90` doesn't reflect actual strip configuration. Different channels may have different pixel counts, affecting DMA timing.

4. **No streaming backpressure**: FrameStreamer has no awareness of connected clients. Serializes frames even when nobody is listening.

5. **Unused ZoneRenderState features**: `brightness`, `mode`, `dirty`, `update_pixels()` are defined but never used by FrameManager. Dead abstraction.

6. **No configurable FPS targets**: Render FPS (60) and stream FPS (30) are hardcoded/init-time. No API to change them at runtime or query actual rates per stage.

---

## 6. PROPOSED FPS METRICS SYSTEM

### 6.1 Architecture: `RenderMetrics` Class

A dedicated metrics collector embedded in FrameManager that precisely tracks frames at every pipeline stage.

**New file**: `src/engine/render_metrics.py`

```
RenderMetrics
├── Production metrics (per source: ANIMATION, STATIC, TRANSITION, PULSE, DEBUG)
│   ├── frames_produced: int
│   ├── frames_dropped_by_queue: int  (deque overflow)
│   └── production_fps: float (rolling 1s window)
│
├── Render metrics
│   ├── frames_built: int (_build_composite_frame succeeded)
│   ├── frames_rendered: int (sent to hardware)
│   ├── frames_dma_skipped: int (hash match)
│   ├── frames_dropped_late: int (overdue > 2x period)
│   ├── render_fps: float (rolling 1s window)
│   └── render_actual_fps: float (hardware writes only)
│
├── Streaming metrics
│   ├── frames_streamed: int (emitted to Socket.IO)
│   ├── frames_stream_dropped: int (queue overflow)
│   └── stream_fps: float (rolling 1s window)
│
├── Timing metrics (rolling window)
│   ├── build_time_ms: avg/p95/max
│   ├── merge_time_ms: avg/p95/max
│   ├── hw_time_ms: avg/p95/max
│   ├── emit_time_ms: avg/p95/max
│   ├── total_frame_time_ms: avg/p95/max
│   └── sleep_accuracy_ms: avg/p95 (actual vs target wake time)
│
└── Configuration
    ├── target_render_fps: int (settable at runtime)
    ├── target_stream_fps: int (settable at runtime)
    └── max_render_fps: int (hardware limit)
```

### 6.2 Integration Points

1. **`push_frame()`** — increment `frames_produced[source]`. When deque drops a frame (detect via len check before/after append), increment `frames_dropped_by_queue`.

2. **`_render_loop()`** — record sleep accuracy (target wake vs actual wake). Detect late frames (remaining < -period) → increment `frames_dropped_late`.

3. **`_build_composite_frame()`** — increment `frames_built`. Record build time.

4. **`_render_frame()`** — increment `frames_rendered` or `frames_dma_skipped`. Record merge/hw/emit times.

5. **`FrameStreamer._loop()`** — increment `frames_streamed`. Track stream FPS.

6. **API endpoint** — `GET /api/v1/system/render-metrics` returns full metrics snapshot.

7. **Socket.IO** — Periodic emit of metrics to frontend (every 1s on `/system` namespace).

### 6.3 Configurable FPS Targets

```python
# Runtime API
frame_manager.set_render_fps(fps: int)    # 1-240, affects render loop period
frame_streamer.set_stream_fps(fps: int)   # 1-60, affects streaming interval

# REST API
PUT /api/v1/system/render-fps    {"fps": 30}
PUT /api/v1/system/stream-fps    {"fps": 15}
GET /api/v1/system/render-metrics
```

### 6.4 Rolling Window Implementation

Use a fixed-size `deque(maxlen=N)` of timestamps per metric. FPS = `len(deque) / (deque[-1] - deque[0])`. Window size = target FPS * 2 (covers 2 seconds).

For timing percentiles (p95, max), use a circular buffer of recent values (last 300 frames = 5s @ 60 FPS).

---

## 7. PROPOSED REPAIRS (Priority Order)

### Phase 1: Bug Fixes (No Architecture Changes)

| # | Fix | Files | Effort |
|---|-----|-------|--------|
| 1 | Standardize on `time.monotonic()` in BaseFrame | `src/models/frame.py` | Small |
| 2 | Remove dead code in `_apply_led_channel_frame` | `src/engine/frame_manager.py:628-631` | Trivial |
| 3 | Fix `_perf_frames` not counted on DMA skip | `src/engine/frame_manager.py:521-545` | Small |
| 4 | Remove or unify `_merge_partial_update` (identical to full) | `src/engine/frame_manager.py` | Small |
| 5 | Increment `dropped_frames` on late frames | `src/engine/frame_manager.py:324` | Small |
| 6 | Remove unused `_select_frame_by_priority()` method | `src/engine/frame_manager.py:467-485` | Trivial |
| 7 | Remove dead `emit()` method from FrameStreamer | `src/services/frame_streamer.py:68-97` | Trivial |

### Phase 2: Animation Speed Fix

| # | Fix | Files | Effort |
|---|-----|-------|--------|
| 8 | Decouple snake position from frame rate using elapsed time | `src/animations/snake.py`, `src/animations/color_snake.py` | Medium |
| 9 | Add optional production throttle to AnimationEngine (sleep to ~120 FPS instead of sleep(0)) | `src/animations/engine.py:232` | Small |

### Phase 3: Metrics System

| # | Fix | Files | Effort |
|---|-----|-------|--------|
| 10 | Create `RenderMetrics` class | New: `src/engine/render_metrics.py` | Medium |
| 11 | Integrate metrics into FrameManager | `src/engine/frame_manager.py` | Medium |
| 12 | Integrate metrics into FrameStreamer | `src/services/frame_streamer.py` | Small |
| 13 | Add REST endpoint for metrics | `src/api/routes/` | Small |
| 14 | Add Socket.IO periodic metrics broadcast | `src/api/socketio/` | Small |
| 15 | Add runtime FPS control API | `src/engine/frame_manager.py`, `src/services/frame_streamer.py` | Small |

### Phase 4: Cleanup

| # | Fix | Files | Effort |
|---|-----|-------|--------|
| 16 | Remove unused ZoneRenderState fields (`brightness`, `mode`) or implement them | `src/engine/zone_render_state.py` | Small |
| 17 | Make WS2811Timing dynamic based on actual pixel count | `src/engine/frame_manager.py` | Small |
| 18 | Add streaming backpressure (skip serialization when no clients) | `src/services/frame_streamer.py` | Small |
| 19 | Remove all commented-out code in engine.py | `src/animations/engine.py` | Trivial |

---

## 8. VERIFICATION PLAN

### Testing Bug Fixes
- Run existing tests: `pytest tests/framesV2/`
- Verify `time.monotonic()` change doesn't break TTL behavior
- Verify DMA skip still works after perf_frames fix

### Testing Animation Speed Fix
- Run snake animation, verify speed parameter actually controls movement speed
- Verify movement is consistent regardless of CPU load
- Compare visual output before/after at speed=50

### Testing Metrics System
- Start application, verify `GET /api/v1/system/render-metrics` returns valid JSON
- Run animation, confirm `render_fps` reads ~60, `production_fps` reads animation rate
- Change render FPS via API, confirm actual FPS changes
- Connect/disconnect frontend, verify stream metrics update

### Hardware Verification
- Confirm no visual regression on LED strips after changes
- Monitor CPU usage — should decrease after animation throttle (Phase 2)
- Verify PERF log accuracy after fixes

---

## 9. CRITICAL FILES

| File | Role | Lines |
|------|------|-------|
| `src/engine/frame_manager.py` | Core render engine | 745 |
| `src/models/frame.py` | Frame types | 120 |
| `src/animations/engine.py` | Animation lifecycle | 580 |
| `src/animations/base.py` | Animation base class | 137 |
| `src/animations/snake.py` | Snake animation | 81 |
| `src/animations/color_snake.py` | Color snake animation | 117 |
| `src/engine/zone_render_state.py` | Render state buffer | 91 |
| `src/services/frame_streamer.py` | Socket.IO streaming | 124 |
| `src/models/enums.py` | FramePriority, FrameSource | 188 |
| New: `src/engine/render_metrics.py` | Metrics collector | ~150 est |
