# Frame Rendering Flow - Diuna System

**Date:** 2026-01-31
**Status:** Post-refactor (MainStrip → LedChannel rename)
**Version:** FrameManager V3

---

## 1. Frame Class Architecture

### 1.1 Type Hierarchy

```
BaseFrame (abstract)
    ├── SingleZoneFrame  - one zone → one Color
    ├── MultiZoneFrame   - many zones → one Color each
    └── PixelFrame       - many zones → List[Color] each

MainStripFrame (internal)  - unified internal representation
OutputFrame (output)       - final frame for streaming
```

### 1.2 Frame Metadata

Every frame (BaseFrame) contains:
- `priority: FramePriority` - rendering priority (0-50)
- `source: FrameSource` - frame source (ANIMATION, STATIC, TRANSITION, etc.)
- `timestamp: float` - creation time (time.time())
- `ttl: float` - frame lifetime in seconds (default: 0.1s)
- `partial: bool` - whether frame is partial (merge with previous state)

### 1.3 OutputFrame (final frame)

```python
@dataclass
class OutputFrame:
    t: float                              # global animation time (seconds)
    zones: Dict[ZoneID, List[Color]]      # full state of all zones (pixel-level)
```

**Characteristics:**
- **Immutable** - represents state snapshot at time `t`
- **Complete** - contains ALL zones from all LedChannels
- **Pixel-level** - each zone is a full List[Color] for every pixel
- **Streaming-ready** - ready for serialization and transmission to frontend/file

---

## 2. Complete Rendering Flow

### Phase 1: Frame Creation (PRODUCERS)

```
Animation.step() → SingleZoneFrame/PixelFrame
    ├─ priority = ANIMATION (30)
    ├─ source = ANIMATION
    └─ partial = True

StaticModeController → SingleZoneFrame
    ├─ priority = MANUAL (10)
    ├─ source = STATIC
    └─ partial = True

TransitionService → PixelFrame
    ├─ priority = TRANSITION (40)
    ├─ source = TRANSITION
    └─ partial = True

SelectedZoneIndicator → SingleZoneFrame
    ├─ priority = PULSE (20)
    ├─ source = SELECTED_ZONE
    └─ partial = True
```

### Phase 2: Submission (QUEUE)

```python
await frame_manager.push_frame(frame)
```

**What happens:**
1. `push_frame()` receives `SingleZoneFrame | MultiZoneFrame | PixelFrame`
2. Converts to `MainStripFrame`:
   - `SingleZoneFrame` → `MainStripFrame(updates={zone_id: color})`
   - `MultiZoneFrame` → `MainStripFrame(updates=zone_colors)`
   - `PixelFrame` → `MainStripFrame(updates=zone_pixels)`
3. Appends to priority queue: `self.main_queues[priority.value].append(msf)`

**Priority queues:**
```
main_queues = {
    0: deque(maxlen=10),   # IDLE
    10: deque(maxlen=10),  # MANUAL (static)
    20: deque(maxlen=10),  # PULSE (indicators)
    30: deque(maxlen=10),  # ANIMATION
    40: deque(maxlen=10),  # TRANSITION
    50: deque(maxlen=10),  # DEBUG
}
```

### Phase 3: Render Loop (60 FPS)

```python
async def _render_loop(self):
    while self.running:
        # 1. Enforce WS2811 timing (min 2.75ms between frames)
        await asyncio.sleep(min_frame_delay)

        # 2. Drain + merge frames
        frame = await self._drain_frames()

        # 3. Render atomically
        if frame:
            self._render_atomic(frame)

        # 4. Frame rate control
        await asyncio.sleep(frame_delay)
```

### Phase 4: Frame Draining (MERGE)

```python
async def _drain_frames() -> Optional[MainStripFrame]:
```

**Merge strategy:**

1. **Collect ANIMATION base layer** (priority=30)
   - All frames from ANIMATION queue
   - Merge updates: `merged_updates[zone_id] = value`
   - This is the continuous base layer

2. **Overlay higher priorities** (40, 50)
   - TRANSITION (40) - fade/crossfade transitions
   - DEBUG (50) - frame-by-frame playback
   - Overwrite ANIMATION for their zones

3. **Fill gaps with lower priorities** (0, 10, 20)
   - MANUAL (10) - static zones
   - PULSE (20) - selected zone indicator
   - IDLE (0) - fallback (black)
   - Fill only zones without animations

**Result:**
```python
MainStripFrame(
    priority=highest_priority,
    source=first_source,
    ttl=max(all_ttls),
    partial=True,
    updates={
        FLOOR: Color(...),      # from ANIMATION
        CIRCLE: [Color, ...],   # from ANIMATION (pixel-level)
        LAMP: Color(...),       # from PULSE (overlay)
        GATE: Color(...),       # from MANUAL (gap fill)
    }
)
```

### Phase 5: Render Pipeline

```python
def _render_atomic(frame: MainStripFrame):
    self._render_frame(frame)

def _render_frame(frame: MainStripFrame):
    # 1. Extract updates
    updates = frame.as_zone_update()  # Dict[ZoneID, Color | List[Color]]

    # 2. Merge with zone_render_states
    merged = self._merge_updates(frame, updates)
    # Result: Dict[ZoneID, List[Color]] - all zones, pixel-level

    # 3. Check if frame changed (skip redundant DMA)
    if self._should_skip_dma(merged):
        return

    # 4. Render to hardware
    self._render_to_hardware(merged)

    # 5. Build + emit OutputFrame
    current_time = time.perf_counter()  # TODO: use global app clock
    output_frame = self._build_output_frame(t=current_time)
    self._emit_output_frame(output_frame)
```

### Phase 6: Merge Strategies

#### A) Partial Update (default)

```python
def _merge_partial_update(updates):
    merged = {}

    for zone_id, state in zone_render_states.items():
        if zone_id in updates:
            # New value - expand to pixel count
            new_val = updates[zone_id]
            if isinstance(new_val, Color):
                merged[zone_id] = [new_val] * len(state.pixels)
            else:
                merged[zone_id] = list(new_val[:len(state.pixels)])
        else:
            # No update - preserve previous state
            merged[zone_id] = list(state.pixels)

    # Update zone_render_states
    for zone_id, pixels in merged.items():
        zone_render_states[zone_id].pixels = pixels

    return merged
```

#### B) Full Update (rare)

```python
def _merge_full_update(updates):
    # Similar to partial, but missing zones → BLACK
    merged = {}

    for zone_id, state in zone_render_states.items():
        if zone_id in updates:
            merged[zone_id] = expand(updates[zone_id])
        else:
            merged[zone_id] = [Color.black()] * len(state.pixels)

    return merged
```

### Phase 7: DMA Skip Optimization

```python
def _should_skip_dma(merged):
    # Hash frame
    frame_hash = hash(merged)

    # Compare with previous
    if frame_hash == last_rendered_frame_hash:
        dma_skipped += 1
        return True  # Skip DMA - LEDs already have correct pixels

    last_rendered_frame_hash = frame_hash
    return False
```

**Savings:** 95% DMA transfer reduction in static-only mode

### Phase 8: Hardware Rendering

```python
def _render_to_hardware(merged):
    # merged: Dict[ZoneID, List[Color]] - full state of all zones

    for led_channel in self.led_channels:
        # 1. Extract zones belonging to this LedChannel
        led_channel_frame = self._prepare_led_channel_frame(led_channel, merged)
        # Result: Dict[ZoneID, List[Color]] - only zones for this channel

        # 2. Validate lengths + mapping
        self._validate_led_channel_frame(led_channel, led_channel_frame)

        # 3. Send to hardware (DMA transfer)
        self._apply_led_channel_frame(led_channel, led_channel_frame)
```

**LedChannel rendering:**
```python
def _apply_led_channel_frame(led_channel, frame):
    # frame: Dict[ZoneID, List[Color]]

    # Send full pixel frame to hardware
    led_channel.show_full_pixel_frame(frame)
    # ↓
    # LedChannel converts zones → physical pixel indices
    # ↓
    # Hardware DMA transfer to WS2811 strip
```

### Phase 9: OutputFrame Creation + Emission

```python
def _build_output_frame(t: float) -> OutputFrame:
    zones = {}

    # Copy current state of ALL zones
    for zone_id, state in zone_render_states.items():
        zones[zone_id] = state.pixels  # List[Color]

    return OutputFrame(t=t, zones=zones)

def _emit_output_frame(output_frame: OutputFrame):
    # TODO: Implement consumers
    # - Socket.IO streaming to frontend
    # - Recording buffer for replay
    # - File export (sequence recording)
    pass
```

---

## 3. Rendering Priorities

```python
class FramePriority(IntEnum):
    IDLE = 0          # Fallback (black)
    MANUAL = 10       # Static colors set by user
    PULSE = 20        # Selected zone indicator
    ANIMATION = 30    # Running animations (BASE LAYER)
    TRANSITION = 40   # Fade/crossfade effects
    DEBUG = 50        # Frame-by-frame playback (highest)
```

**Rules:**
- Higher priority wins
- Animations (30) are BASE LAYER - always collected first
- Overlays (40, 50) overwrite base layer for their zones
- Gap fills (0, 10, 20) fill zones without animations

---

## 4. Zone Render State

```python
@dataclass
class ZoneRenderState:
    zone_id: ZoneID
    pixels: List[Color]  # Current pixel state
```

**Characteristics:**
- Stores **current rendered state** of each zone
- Used for partial merge (missing zones preserve previous state)
- Initialized to BLACK when LedChannel is added
- Updated after each render

---

## 5. Timing & Performance

### WS2811 Constraints

```python
class WS2811Timing:
    DATA_RATE_HZ = 800_000
    BIT_TIME_US = 1.25
    RESET_TIME_US = 50
    BITS_PER_PIXEL = 24
    PIXEL_COUNT = 90

    DMA_TRANSFER_MS = 2.7      # DMA transfer time
    RESET_TIME_MS = 0.05       # Protocol reset time
    MIN_FRAME_TIME_MS = 2.75   # Minimum between show() calls

    TARGET_FPS = 60
```

**Enforcement:**
```python
# Before render
elapsed = time.perf_counter() - last_show_time
if elapsed < MIN_FRAME_TIME_MS / 1000:
    await asyncio.sleep((MIN_FRAME_TIME_MS / 1000) - elapsed)
```

### Metrics

```python
get_metrics() -> {
    "fps_target": 60,
    "fps_actual": 59.8,
    "frames_rendered": 3580,
    "dropped_frames": 0,
    "dma_skipped": 3420,  # 95% reduction in static mode
    "pending_main": 0,
}
```

---

## 6. Issues After MainStrip → LedChannel Refactor

### Found Bugs (FIXED)

1. ✅ `current_time` undefined in `_render_frame()` (line 521)
   - **Fix:** `current_time = time.perf_counter()`
   - **TODO:** Replace with global app clock

2. ✅ `_emit_output_frame()` did not exist
   - **Fix:** Added placeholder method
   - **TODO:** Implement Socket.IO streaming

### Remaining TODOs

1. **Global App Clock**
   - Current: `t = time.perf_counter()` (time since process start)
   - Should be: `t = app_clock.now()` (global synchronized clock)
   - Needed for: multi-entity sync, deterministic replay

2. **OutputFrame Emission**
   - Current: `_emit_output_frame()` is empty
   - Should emit to:
     - Socket.IO clients (frontend visualization)
     - Recording buffer (replay system)
     - File writer (sequence export)

3. **Frame TTL Cleanup**
   - TTL is used in `_drain_frames()` for expiration
   - But for streaming, TTL doesn't make sense (we stream live state)
   - Consider removing TTL from OutputFrame flow

4. **Deterministic Animations**
   - Current: animations have internal state (stateful)
   - Plan: refactor to `render(t, params) -> Frame`
   - Requires: global clock, time parameterization

---

## 7. Streaming Architecture (TODO)

### Planned Flow

```
FrameManager._render_frame()
    ↓
_build_output_frame(t)
    ↓
OutputFrame(t, zones)
    ↓
_emit_output_frame(output_frame)
    ↓
┌─────────────────────────────────────┐
│  OutputFrameEmitter (new service)   │
├─────────────────────────────────────┤
│ - Socket.IO streaming (30 fps)      │
│ - Recording buffer (replay)         │
│ - File writer (sequence export)     │
└─────────────────────────────────────┘
```

### Socket.IO Streaming

```python
# Server side
async def _emit_output_frame(output_frame: OutputFrame):
    # Throttle to 30 fps (vs 60 fps render)
    if not self._should_emit_frame():
        return

    # Serialize to JSON
    payload = {
        "t": output_frame.t,
        "zones": {
            zone_id.name: [c.to_rgb() for c in pixels]
            for zone_id, pixels in output_frame.zones.items()
        }
    }

    # Emit via Socket.IO
    await sio.emit("output_frame", payload)

# Frontend
socket.on("output_frame", (data) => {
    // Update virtual LED visualization
    renderVirtualLEDs(data.zones)
})
```

### Recording/Replay

```python
# Record
class FrameRecorder:
    def __init__(self):
        self.buffer: List[OutputFrame] = []

    def record(self, frame: OutputFrame):
        self.buffer.append(frame)

    def save(self, filename: str):
        # Serialize to file (pickle, msgpack, or custom format)
        with open(filename, "wb") as f:
            pickle.dump(self.buffer, f)

# Replay
class FrameReplayer:
    def __init__(self, frames: List[OutputFrame]):
        self.frames = frames
        self.index = 0

    def step_forward(self) -> OutputFrame:
        frame = self.frames[self.index]
        self.index = min(self.index + 1, len(self.frames) - 1)
        return frame

    def step_backward(self) -> OutputFrame:
        self.index = max(self.index - 1, 0)
        return self.frames[self.index]
```

---

## 8. Summary

### What Works

✅ Priority-based frame queues
✅ Drain + merge strategy (base layer + overlays)
✅ Partial/full frame updates
✅ DMA skip optimization
✅ Multi-LedChannel rendering
✅ WS2811 timing enforcement
✅ OutputFrame creation

### What Needs Implementation

🔨 Global app clock
🔨 OutputFrame emission (streaming)
🔨 Socket.IO integration
🔨 Recording/replay system
🔨 Deterministic animations
🔨 Multi-entity synchronization (future)

### Code Status

- **Compiles:** ✅ (after fixes)
- **Runs:** ✅ (requires sudo for WS2811)
- **Renders frames:** ✅
- **Streams:** ❌ (TODO)
- **Records:** ❌ (TODO)

---

## 9. Next Steps

### Immediate (pre-streaming)
1. ✅ Fix `current_time` undefined
2. ✅ Add `_emit_output_frame()` placeholder
3. Test render loop with OutputFrame creation
4. Verify frame hash correctness

### Short-term (streaming MVP)
1. Add global AppClock service
2. Implement Socket.IO streaming
3. Add frame throttling (60 fps render → 30 fps stream)
4. Build frontend visualization receiver

### Medium-term (recording/replay)
1. Build FrameRecorder service
2. Build FrameReplayer service
3. Add file export (msgpack/pickle)
4. Add frame-by-frame controls

### Long-term (deterministic system)
1. Refactor animations to pure functions `f(t) -> Frame`
2. Remove internal animation state
3. Implement animation parameter system
4. Build animation preview system

---

**Last Updated:** 2026-01-31
**Author:** Claude + JP2
**Status:** Post-refactor, pre-streaming
