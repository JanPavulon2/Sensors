# Frame Rendering Flow - Diuna System

**Date:** 2026-02-12
**Status:** Current (FrameManager V3 + FrameStreamer + AppClock)
**Version:** FrameManager V3

---

## 1. Frame Class Architecture

### 1.1 Type Hierarchy

```
BaseFrame (abstract)
    ├── SingleZoneFrame  - one zone → one Color
    ├── MultiZoneFrame   - many zones → one Color each
    └── PixelFrame       - many zones → List[Color] each

CompositeFrame (internal)  - unified internal representation used by FrameManager
OutputFrame (output)       - immutable snapshot for streaming/recording
```

### 1.2 Frame Metadata

Every frame (BaseFrame) contains:
- `priority: FramePriority` - rendering priority (0-50)
- `source: FrameSource` - frame source (ANIMATION, STATIC, TRANSITION, etc.)
- `timestamp: float` - creation time (time.time()) — note: unused, see Known Issues
- `ttl: float` - frame lifetime in seconds (default: 0.1s)
- `partial: bool` - whether frame is partial (merge with previous state)

CompositeFrame uses `time.monotonic()` for `created_at` and TTL expiration.

### 1.3 OutputFrame (final frame)

```python
@dataclass
class OutputFrame:
    t: float                              # global animation time from AppClock
    zones: Dict[ZoneID, List[Color]]      # full state of all zones (pixel-level)
```

**Characteristics:**
- **Immutable** - represents state snapshot at time `t`
- **Complete** - contains ALL zones from all LedChannels
- **Pixel-level** - each zone is a full List[Color] for every pixel
- **Streaming-ready** - serialized and emitted via FrameStreamer to Socket.IO

---

## 2. Complete Rendering Flow

### Phase 1: Frame Creation (PRODUCERS)

```
Animation.step() → SingleZoneFrame/PixelFrame
    ├─ priority = ANIMATION (20)
    ├─ source = ANIMATION
    ├─ partial = False (snake, color_snake) or True (color_fade)
    └─ ttl = 0.12s (pixel) or 0.2s (zone-level)

StaticModeController → SingleZoneFrame / MultiZoneFrame
    ├─ priority = MANUAL (10)
    ├─ source = STATIC
    └─ ttl = 10.0s (long-lived, persistent)

TransitionService → PixelFrame
    ├─ priority = TRANSITION (40)
    ├─ source = TRANSITION
    └─ ttl = 0.1s (default)

SelectedZoneIndicator → SingleZoneFrame
    ├─ priority = PULSE (30)
    ├─ source = PULSE
    └─ ttl = 0.15-0.25s

FramePlaybackController → PixelFrame
    ├─ priority = DEBUG (50)
    ├─ source = DEBUG
    └─ ttl = 10.0s (manual stepping)
```

### Phase 2: Submission (QUEUE)

```python
await frame_manager.push_frame(frame)
```

**What happens:**
1. `push_frame()` receives `SingleZoneFrame | MultiZoneFrame | PixelFrame`
2. Converts to `CompositeFrame`:
   - `SingleZoneFrame` → `CompositeFrame(updates={zone_id: color})`
   - `MultiZoneFrame` → `CompositeFrame(updates=zone_colors)`
   - `PixelFrame` → `CompositeFrame(updates=zone_pixels)`
3. Appends to priority queue: `self.priority_queues[priority.value].append(cf)`

**Priority queues:**
```
priority_queues = {
    0: deque(maxlen=10),   # IDLE
    10: deque(maxlen=10),  # MANUAL (static)
    20: deque(maxlen=10),  # ANIMATION
    30: deque(maxlen=10),  # PULSE (indicators)
    40: deque(maxlen=10),  # TRANSITION
    50: deque(maxlen=10),  # DEBUG
}
```

### Phase 3: Render Loop (60 FPS)

```python
async def _render_loop(self):
    frame_period = 1.0 / self.fps  # 16.67ms
    min_frame_time = max(frame_period, WS2811Timing.MIN_FRAME_TIME_MS / 1000)
    next_frame_time = time.perf_counter()  # Absolute timeline

    while self.running:
        # Handle pause/step (for frame-by-frame debug)
        if self.paused and not self.step_requested:
            await asyncio.sleep(0.01)
            continue

        # === RPi-OPTIMIZED SMART SLEEP ===
        while True:
            now = time.perf_counter()
            remaining = next_frame_time - now

            if remaining <= 0:
                break  # Frame due (or overdue)
            elif remaining > 0.003:
                await asyncio.sleep(0.001)  # Far: 1ms chunks
            elif remaining > 0.001:
                await asyncio.sleep(0)       # Close: yield to event loop
            else:
                while time.perf_counter() < next_frame_time:
                    pass                     # Final 1ms: busy-wait
                break

        # === BUILD + RENDER ===
        composite_frame = await self._build_composite_frame()
        if composite_frame is not None:
            await self._render_frame(composite_frame)

        # Advance absolute timeline (no drift accumulation)
        next_frame_time += min_frame_time
```

**Why 3-stage sleep?**
- `asyncio.sleep()` on RPi has ~10ms kernel timer granularity
- Sleeping 16.67ms would actually sleep ~20ms → capping at ~17 FPS
- 1ms chunks keep us close, yield lets animations run, busy-wait gives precision

### Phase 4: Frame Building (MERGE)

```python
async def _build_composite_frame() -> Optional[CompositeFrame]:
```

**3-phase merge strategy:**

1. **Collect ANIMATION base layer** (priority=20)
   - All non-expired frames from ANIMATION queue
   - Merge updates: `merged_updates.update(frame.updates)`
   - This is the continuous base layer

2. **Overlay higher priorities** (30, 40, 50)
   - PULSE (30) - selected zone indicator
   - TRANSITION (40) - fade/crossfade transitions
   - DEBUG (50) - frame-by-frame playback
   - Override animation zones: `merged_updates.update(frame.updates)`

3. **Fill gaps with lower priorities** (0, 10)
   - MANUAL (10) - static zones
   - IDLE (0) - fallback (black)
   - Fill only zones without updates: `merged_updates.setdefault(zid, val)`

**Result:**
```python
CompositeFrame(
    priority=highest_priority,
    source=first_source,
    ttl=max(all_ttls),
    updates={
        FLOOR: [Color, ...],   # from ANIMATION (pixel-level snake)
        CIRCLE: Color(...),    # from ANIMATION (zone-level breathe)
        LAMP: Color(...),      # from PULSE (overlay - edit indicator)
        GATE: Color(...),      # from MANUAL (gap fill - static zone)
    }
)
```

### Phase 5: Render Pipeline

```python
async def _render_frame(frame: CompositeFrame):
    # 1. Merge with zone_render_states (normalize all to List[Color])
    merged = self._merge_updates(frame, frame.updates)
    # Result: Dict[ZoneID, List[Color]] - all zones, pixel-level

    # 2. Check if frame changed (skip redundant DMA)
    if self._should_skip_dma(merged):
        return  # LEDs already have correct pixels

    # 3. Render to hardware
    self._render_to_hardware(merged)

    # 4. Track metrics
    self.frames_rendered += 1
    self.frame_times.append(time.perf_counter())

    # 5. Build + push OutputFrame to FrameStreamer
    output_frame = self._build_output_frame()  # Uses AppClock for timestamp
    self.frame_streamer.push(output_frame)      # Queued for 30 FPS streaming
```

### Phase 6: Merge Strategy

```python
def _merge_updates(frame, updates):
    """Normalize all zone updates to List[Color] and update zone_render_states."""
    merged = {}

    for zone_id, state in zone_render_states.items():
        if zone_id in updates:
            merged[zone_id] = _normalize_zone_pixels(updates[zone_id], len(state.pixels))
        else:
            merged[zone_id] = list(state.pixels)  # Preserve previous state

    # Update zone_render_states (source of truth)
    for zone_id, pixels in merged.items():
        zone_render_states[zone_id].pixels = pixels

    return merged

def _normalize_zone_pixels(val, expected_len) -> List[Color]:
    """Color → repeated list, List[Color] → trimmed/padded to exact length."""
    if isinstance(val, Color):
        return [val] * expected_len
    pix = list(val[:expected_len])
    if len(pix) < expected_len:
        pix += [Color.black()] * (expected_len - len(pix))
    return pix
```

**Why there's no partial/full distinction here:**

The `partial` flag on `BaseFrame` is **not propagated** to `CompositeFrame` — it's lost during `push_frame()` conversion. But this is correct by design: by the time `_merge_updates()` is called, `_build_composite_frame()` has already composed all sources (animation + static + overlays) into a single frame via the 3-phase merge. The result is always effectively "full" — every active zone has a value. Missing zones mean no source produced a frame for them this tick, so preserving previous render state is the correct behavior.

The old `_merge_partial_update` method was removed as dead code — it was identical to `_merge_full_update` and unreachable (CompositeFrame has no `partial` field).

### Phase 7: DMA Skip Optimization

```python
def _should_skip_dma(merged):
    frame_hash = _hash_merged_frame(merged)

    if frame_hash == last_rendered_frame_hash:
        dma_skipped += 1
        return True  # Skip DMA - LEDs already have correct pixels

    last_rendered_frame_hash = frame_hash
    return False

@staticmethod
def _hash_merged_frame(merged):
    """Fast multiplicative hash over all zone pixels."""
    h = 0
    for zone_id, pix in merged.items():
        for c in pix:
            h = (h * 1315423911) ^ hash(c.to_rgb())
    return h
```

**Savings:** ~95% DMA transfer reduction in static-only mode

### Phase 8: Hardware Rendering

```python
def _render_to_hardware(merged):
    for led_channel in self.led_channels:
        # 1. Extract zones belonging to this LedChannel
        led_channel_frame = _prepare_led_channel_frame(led_channel, merged)

        # 2. Validate lengths + mapping
        _validate_led_channel_frame(led_channel, led_channel_frame)

        # 3. Send to hardware (DMA transfer)
        _apply_led_channel_frame(led_channel, led_channel_frame)
```

**LedChannel rendering:**
```python
def show_full_pixel_frame(zone_pixels_dict):
    # 1. Read current hardware buffer
    full_frame = hardware.get_frame()

    # 2. Map logical zone pixels → physical strip indices
    for zone_id, pixels in zone_pixels_dict.items():
        indices = mapper.get_indices(zone_id)  # Handles reversal
        for logical_idx, color in enumerate(pixels):
            phys_idx = indices[logical_idx]
            full_frame[phys_idx] = color

    # 3. Atomic DMA transfer (single strip.show() call)
    hardware.apply_frame(full_frame)
```

### Phase 9: OutputFrame Streaming

```python
def _build_output_frame() -> OutputFrame:
    t = self.app_clock.now()  # Global synchronized clock

    zones = {
        zone_id: list(state.pixels)  # Immutable copy
        for zone_id, state in zone_render_states.items()
    }

    return OutputFrame(t=t, zones=zones)
```

**FrameStreamer** (`src/services/frame_streamer.py`):
```python
class FrameStreamer:
    """Throttled Socket.IO output at 30 FPS."""

    def __init__(self, sio, target_fps=30):
        self._queue: deque[OutputFrame] = deque(maxlen=2)  # Latest-only buffer
        self._interval = 1.0 / target_fps

    def push(self, frame: OutputFrame):
        self._queue.append(frame)  # Non-blocking, drops old frames

    async def _loop(self):
        while self._running:
            if self._queue:
                frame = self._queue.pop()  # Latest frame only
                await sio.emit("output_frame", self._serialize(frame), namespace="/frames")
            await asyncio.sleep(self._interval)

    def _serialize(self, frame) -> dict:
        return {
            "t": frame.t,
            "zones": {
                zone_id.name: [list(c.to_rgb()) for c in pixels]
                for zone_id, pixels in frame.zones.items()
            }
        }
```

**Frontend receives:**
```json
{
  "t": 123.456,
  "zones": {
    "FLOOR": [[255, 0, 0], [255, 0, 0], ...],
    "CIRCLE": [[0, 255, 0], ...]
  }
}
```

---

## 3. Rendering Priorities

```python
class FramePriority(Enum):
    IDLE = 0          # Fallback (black)
    MANUAL = 10       # Static colors set by user
    ANIMATION = 20    # Running animations (BASE LAYER)
    PULSE = 30        # Selected zone indicator (edit mode)
    TRANSITION = 40   # Fade/crossfade effects
    DEBUG = 50        # Frame-by-frame playback (highest)
```

**Merge rules:**
- ANIMATION (20) is the BASE LAYER — always collected first
- PULSE (30) overlays on specific zones (edit indicator overrides animation)
- TRANSITION (40) overrides everything except DEBUG
- MANUAL (10) fills gaps for zones without animations
- IDLE (0) fallback for zones with no source at all

---

## 4. Animation Production Model

### Per-Zone Architecture

Each animation is one instance per zone, running in its own asyncio.Task:

```python
# AnimationEngine._run_loop()
async def _run_loop(zone_id, animation):
    while True:
        frame = await animation.step()
        if frame is not None:
            await frame_manager.push_frame(frame)
        await asyncio.sleep(0)  # Yield only — no FPS throttling here
```

**Key design:** Animations produce frames as fast as possible. FrameManager controls the actual render rate at 60 FPS. The `deque(maxlen=10)` queue acts as a latest-frame buffer — when full, oldest frames are silently dropped.

### Animation Types

| Animation | Returns | Movement Model | Notes |
|-----------|---------|----------------|-------|
| BreatheAnimation | `SingleZoneFrame` | Time-based (`sin(elapsed/period)`) | Speed param controls period |
| ColorFadeAnimation | `SingleZoneFrame` | Time-based (`elapsed/period % 1.0`) | Speed param controls period |
| SnakeAnimation | `PixelFrame` | Position-based (`_position += 1` per step) | Speed param NOT used (known issue) |
| ColorSnakeAnimation | `PixelFrame` | Position-based (`_position += 1` per step) | Speed param NOT used (known issue) |

---

## 5. Zone Render State

```python
@dataclass
class ZoneRenderState:
    zone_id: ZoneID
    pixels: List[Color]            # Currently rendered pixel state
    source: Optional[FrameSource]  # Which source last updated
    last_update_ts: float          # When last rendered
```

**Purpose:**
- Stores **current rendered state** of each zone (ephemeral, not persisted)
- Used for merge (missing zones preserve previous state from render buffer)
- Initialized to BLACK when LedChannel is registered
- Updated after each render by `_merge_updates()`
- Separate from domain `ZoneState` (persisted in `state.json`)

---

## 6. Timing & Performance

### WS2811 Constraints

```python
class WS2811Timing:
    DATA_RATE_HZ = 800_000
    BIT_TIME_US = 1.25
    RESET_TIME_US = 50
    BITS_PER_PIXEL = 24
    PIXEL_COUNT = 90          # Note: hardcoded, should be dynamic

    DMA_TRANSFER_MS = 2.7     # DMA transfer time for 90 pixels
    RESET_TIME_MS = 0.05      # Protocol reset time
    MIN_FRAME_TIME_MS = 2.75  # Minimum between show() calls

    TARGET_FPS = 60
    PRACTICAL_MAX_FPS = 150
    THEORETICAL_MAX_FPS = ~363
```

**Enforcement:** The render loop uses absolute timeline with `min_frame_time = max(frame_period, MIN_FRAME_TIME_MS / 1000)` to ensure WS2811 timing constraints are never violated.

### Performance Budget (per frame @ 60 FPS)

```
Total budget: 16.67ms (1/60s)

Typical breakdown (from PERF log):
  build:  0.15ms  - Drain priority queues, merge frames
  merge:  0.08ms  - Normalize zones, update render states
  hw:     2.80ms  - Zone mapping + DMA transfer
  emit:   0.05ms  - Build OutputFrame, push to streamer
  ──────────────
  Total:  3.08ms  (18.5% of budget)

  Remaining: ~13.6ms for event loop, animation tasks, API handlers
```

### Metrics

```python
get_metrics() -> {
    "fps_target": 60,
    "fps_actual": 59.8,
    "frames_rendered": 3580,
    "dropped_frames": 0,       # Note: counter exists but never incremented
    "dma_skipped": 3420,       # 95% reduction in static mode
    "pending": 0,
}
```

---

## 7. Known Issues

### Active Bugs

1. **Clock mismatch**: `BaseFrame` uses `time.time()`, `CompositeFrame` uses `time.monotonic()` — should standardize on monotonic
2. **Snake speed uncontrolled**: `_position += 1` per step() call regardless of speed parameter — runs at thousands of positions/sec
3. **Frame overproduction**: Animations produce ~1000+ frames/sec per zone, only ~60 consumed — wastes CPU
4. **`dropped_frames` never incremented**: Counter initialized but no code increments it
5. **`_perf_frames` undercounted**: Not incremented when DMA is skipped (early return)
6. **Dead code in `_apply_led_channel_frame`**: Extracts first pixel RGB but never uses it

### Design Gaps

1. **No production metrics**: Cannot track how many frames each source produces or drops
2. **No runtime FPS control API**: Render and stream FPS only configurable at init time
3. **No streaming backpressure**: FrameStreamer serializes even with no connected clients
4. **WS2811Timing hardcoded pixel count**: Should be dynamic per LED channel

---

## 8. Summary

### What Works

- Priority-based frame queues with 3-phase merge (base + overlay + gap fill)
- DMA skip optimization (~95% reduction in static mode)
- RPi-optimized absolute-timeline render loop with 3-stage sleep
- Multi-LedChannel rendering with zone-to-pixel mapping
- WS2811 timing enforcement (min 2.75ms between DMA transfers)
- OutputFrame creation with AppClock timestamps
- Socket.IO streaming via FrameStreamer at 30 FPS
- Frame-by-frame debug mode (pause/step with DEBUG priority)

### What Needs Implementation

- RenderMetrics system (per-stage frame counting and FPS tracking)
- Runtime FPS control API (render + stream targets)
- Animation speed decoupling from frame rate (snake animations)
- Animation production throttle (reduce CPU waste)
- Streaming backpressure (skip when no clients)

---

**Last Updated:** 2026-02-12
**Author:** Claude + JP2
**Status:** Current — streaming implemented, metrics system planned
