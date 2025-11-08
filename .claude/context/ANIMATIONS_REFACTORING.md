# Animation System Refactoring Plan

**Version**: 1.0
**Created**: 2025-11-07
**Status**: Planning Phase
**Target**: Version 0.2

---

## Table of Contents

1. [Goals & Motivation](#1-goals--motivation)
2. [Target Architecture](#2-target-architecture)
3. [Implementation Phases](#3-implementation-phases)
4. [Atomic Frame Models](#4-atomic-frame-models)
5. [FrameManager Design](#5-framemanager-design)
6. [Preview System Redesign](#6-preview-system-redesign)
7. [Migration Strategy](#7-migration-strategy)
8. [Testing Strategy](#8-testing-strategy)
9. [Potential Risks](#9-potential-risks)
10. [Success Metrics](#10-success-metrics)

---

## 1. Goals & Motivation

### 1.1 Primary Goals

✅ **Eliminate flickering** - Single source of truth for frame rendering
✅ **Prevent race conditions** - Priority-based frame queuing
✅ **Synchronize preview** - Main strip and preview panel render in lockstep
✅ **Enable debugging** - Pause/step frame-by-frame mode
✅ **Support future features** - WebSocket streaming, game mode, recording

### 1.2 Key Problems to Solve

**Problem 1: Multiple Direct Renderers**
- AnimationEngine, TransitionService, StaticModeController all call `strip.show()` directly
- No coordination → race conditions and flickering

**Problem 2: No Priority System**
- Transition can be interrupted by animation frame
- Pulsing conflicts with manual color changes
- Debug overlays impossible

**Problem 3: Preview Out of Sync**
- Preview panel updated separately from main strip
- Animations don't automatically update preview
- Parameter previews require manual controller code

**Problem 4: No Central Control**
- Cannot pause rendering globally
- Cannot step through frames for debugging
- Cannot broadcast frames to external systems (WebSocket)

### 1.3 Non-Goals (Out of Scope)

❌ Change animation API (keep `async def run()` generators)
❌ Rewrite existing animations
❌ Add new animations (focus on infrastructure)
❌ Change hardware setup (GPIO pins, LED counts)
❌ Modify domain models (AnimationCombined, ZoneCombined)

---

## 2. Target Architecture

### 2.1 Centralized Rendering

```
┌─────────────────────────────────────────────────────────────┐
│                     FRAME SOURCES                            │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  Animations  │ Transitions  │   Static     │   Preview      │
│   (Engine)   │  (Service)   │  (Pulse)     │  (Params)      │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────┘
       │              │              │                │
       │              │              │                │
       └──────────────┴──────────────┴────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │    FRAME MANAGER      │
              │  (Central Renderer)   │
              │                       │
              │  • Priority Queues    │
              │  • Frame Selection    │
              │  • Ticker (60 Hz)     │
              │  • Pause/Step Mode    │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   HARDWARE RENDERING  │
              │                       │
              │  • ZoneStrip.show()   │
              │  • PreviewPanel.show()│
              │  • Synchronized       │
              └───────────────────────┘
```

### 2.2 Priority System

```python
class FramePriority(IntEnum):
    IDLE = 0           # Black screen / idle state
    MANUAL = 10        # Manual color settings
    PULSE = 20         # Edit mode pulsing
    ANIMATION = 30     # Running animations
    TRANSITION = 40    # Crossfades (highest)
    DEBUG = 50         # Debug overlays (future)
```

**Rules**:
- Only **highest priority** frame is rendered at any time
- Lower priority frames are **discarded** if higher priority exists
- When high-priority source stops, next priority takes over automatically

### 2.3 Frame Flow

```
Animation yields (zone_id, r, g, b)
    ↓
AnimationEngine wraps in PixelFrame(priority=ANIMATION, source=ANIMATION)
    ↓
FrameManager.submit_pixel_frame(frame)
    ↓
Frame added to main_queues[ANIMATION]
    ↓
Ticker selects highest priority frame
    ↓
FrameManager renders to ZoneStrip + PreviewPanel
    ↓
Hardware shows synchronized output
```

### 2.4 Dual Strip Rendering

**Main Strip** (89 pixels):
- Renders full animation/static frames
- Separate queues per priority

**Preview Panel** (8 pixels):
- Renders parameter previews OR animation preview
- Same priority system
- Synchronized with main strip (same tick)

---

## 3. Implementation Phases

### Phase 1: Atomic Frame Models ✅ READY
**Duration**: 1 day
**Risk**: Low

**Tasks**:
1. Replace `src/models/frame.py` with atomic frame classes:
   - `FullStripFrame` - Single color for entire strip
   - `ZoneFrame` - Per-zone colors
   - `PixelFrame` - Per-pixel colors
   - `PreviewFrame` - 8-pixel preview
2. Add `FramePriority` and `FrameSource` enums to `models/enums.py`
3. All frames inherit from `BaseFrame` with TTL, timestamp, priority

**Deliverables**:
- `src/models/frame.py` - New atomic frame classes
- `src/models/enums.py` - Extended with FramePriority, FrameSource

### Phase 2: Preview Panel Methods ✅ READY
**Duration**: 1 day
**Risk**: Low

**Tasks**:
1. Add high-level rendering methods to `PreviewPanel`:
   - `render_bar(value, max_value, color)` - Bar indicator
   - `render_solid(color)` - Solid color fill
   - `render_gradient(color, intensity)` - Intensity gradient
   - `render_multi_color(colors)` - Multi-color display
   - `render_pattern(pattern)` - Custom pattern
2. Keep existing methods (`show_frame`, `set_pixel`, etc.)
3. Add docstrings with usage examples

**Deliverables**:
- `src/components/preview_panel.py` - Extended with 5 new methods

### Phase 3: FrameManager Core ⚠️ COMPLEX + ⚡ **HARDWARE CRITICAL**
**Duration**: 3-4 days
**Risk**: Medium

**Tasks**:
1. Refactor `src/engine/frame_manager.py`:
   - Add dual priority queues (main_queues, preview_queues)
   - Implement `_select_highest_priority_frame()`
   - Add type-specific rendering methods
   - Implement pause/step mode
2. Add RenderTarget and PreviewTarget protocols
3. Update ticker loop to render both strips atomically
4. Add frame expiration (TTL) handling
5. **🔧 Hardware-specific additions**:
   - WS2811 reset time enforcement (50µs minimum between frames)
   - DMA transfer time tracking (2.7ms per frame @ 90 pixels)
   - Frame drop detection (buffer overflow protection)
   - Actual FPS measurement (not just target FPS)

**Deliverables**:
- `src/engine/frame_manager.py` - Complete refactor (350-450 lines with hardware safety)
- `src/engine/render_protocol.py` - Protocol definitions

**Hardware Safety Checks to Add**:
```python
# 1. Enforce minimum inter-frame delay
MIN_RESET_TIME = 0.00005  # 50µs WS2811 reset requirement
last_show_time = time.time()

async def _render_loop(self):
    while self.running:
        # ... frame selection ...

        # Enforce WS2811 timing
        elapsed = time.time() - self.last_show_time
        if elapsed < MIN_RESET_TIME:
            await asyncio.sleep(MIN_RESET_TIME - elapsed)

        self._render_all_zones()  # Calls strip.show() ONCE
        self.last_show_time = time.time()

        # Track actual FPS
        self.frame_times.append(time.time())

        await asyncio.sleep(1.0 / self.fps)

# 2. Frame drop detection
if len(self.pending_frames) > 10:
    dropped = len(self.pending_frames) - 5
    for _ in range(dropped):
        self.pending_frames.popleft()
    self.dropped_frames += dropped
    log.warn(f"Frame buffer overflow - dropped {dropped} frames")

# 3. Actual FPS monitoring
def get_actual_fps(self) -> float:
    if len(self.frame_times) < 2:
        return 0
    duration = self.frame_times[-1] - self.frame_times[0]
    return len(self.frame_times) / duration
```

### Phase 4: AnimationEngine Integration ⚠️ CRITICAL
**Duration**: 2-3 days
**Risk**: High

**Tasks**:
1. Remove all direct `strip.set_*()` calls from `AnimationEngine`
2. Implement frame type detection (3-tuple, 4-tuple, 5-tuple)
3. Wrap animation frames in appropriate Frame objects
4. Add dual loop support (`_run_main_loop` + `_run_preview_loop`)
5. Update `start()` method to launch both loops
6. Test with all existing animations

**Deliverables**:
- `src/animations/engine.py` - Refactored rendering
- All animations work with new system

### Phase 5: TransitionService Integration ⚠️ CRITICAL + ⚡ **TIMING SAFETY**
**Duration**: 2 days
**Risk**: Medium-High

**Tasks**:
1. Remove direct `strip.set_pixel_color_absolute()` calls
2. Submit frames to FrameManager with `FramePriority.TRANSITION`
3. Convert absolute pixel arrays to zone-based format
4. Keep `_transition_lock` for internal coordination
5. Test all transition types (crossfade, fade_in, fade_out)
6. **🔧 Add WS2811 timing protection** to prevent protocol violations

**Deliverables**:
- `src/services/transition_service.py` - FrameManager integration with timing safety

**Critical Hardware Fix**:
```python
async def crossfade(self, from_frame, to_frame, config):
    """Crossfade with WS2811 timing protection"""

    # CRITICAL: Enforce minimum step delay
    # WS2811 requires 50µs reset + 2.7ms DMA transfer = 2.75ms minimum
    MIN_FRAME_TIME = 0.00275  # 2.75ms

    step_delay = config.duration_ms / 1000 / config.steps

    # Prevent timing violations
    if step_delay < MIN_FRAME_TIME:
        # Reduce step count to maintain timing safety
        safe_steps = int(config.duration_ms / 1000 / MIN_FRAME_TIME)
        log.warn(f"Transition too fast: reduced steps {config.steps} → {safe_steps}")
        config.steps = max(1, safe_steps)
        step_delay = config.duration_ms / 1000 / config.steps

    async with self._transition_lock:
        for step in range(config.steps + 1):
            # ... interpolate colors ...

            # Submit to FrameManager (not direct strip.show())
            frame = PixelFrame(
                priority=FramePriority.TRANSITION,
                source=FrameSource.TRANSITION,
                zone_pixels=interpolated_frame
            )
            self.frame_manager.submit_pixel_frame(frame)

            await asyncio.sleep(step_delay)  # Now guaranteed >= 2.75ms
```

**Why This Matters**:
- Current code allows `step_delay < 50µs` which violates WS2811 reset time
- At 90 pixels, frame corruption is more visible than at 45 pixels
- Fast transitions (duration_ms=10) could create 0.033ms delays → **data corruption**

### Phase 6: Static Mode Controller Update 🔧 MODERATE
**Duration**: 2 days
**Risk**: Low-Medium

**Tasks**:
1. Remove direct preview panel calls from parameter adjustment
2. Use new `preview_panel.render_*()` methods
3. Update pulsing to submit frames to FrameManager
4. Test parameter preview for brightness, color, preset

**Deliverables**:
- `src/controllers/led_controller/static_mode_controller.py` - Updated

### Phase 7: Animation Mode Controller Update 🔧 MODERATE
**Duration**: 1-2 days
**Risk**: Low

**Tasks**:
1. Use new `preview_panel.render_*()` methods for parameter preview
2. Remove manual preview updates
3. Test parameter preview for speed, intensity, length

**Deliverables**:
- `src/controllers/led_controller/animation_mode_controller.py` - Updated

### Phase 8: Testing & Validation ✅ CRITICAL
**Duration**: 2-3 days
**Risk**: Medium

**Tasks**:
1. Test all animations (breathe, snake, color_fade, etc.)
2. Test transitions (mode switch, animation switch, power toggle)
3. Test parameter previews (all params in both modes)
4. Test edge cases (rapid mode switches, parameter changes during animation)
5. Performance testing (FPS stability, memory usage)
6. Hardware testing on Raspberry Pi

**Deliverables**:
- Validated system on actual hardware
- Performance benchmarks
- Bug fixes

---

## 4. Atomic Frame Models

### 4.1 Design Principles

**Atomic Types**: Each frame type is a separate class (no union types in one class)
**Immutable**: Frames are created once, not modified
**Typed**: Strong typing with dataclasses
**Expirable**: TTL prevents memory bloat and stale frames

### 4.2 Frame Class Hierarchy

```python
@dataclass
class BaseFrame:
    """Base for all frame types"""
    priority: FramePriority
    source: FrameSource
    timestamp: float = field(default_factory=time.time)
    ttl: float = 0.1  # 100ms expiration

    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl
```

### 4.3 Main Strip Frames

```python
@dataclass
class FullStripFrame(BaseFrame):
    """
    Single color for entire strip (all zones same color)

    Use Case: ColorCycleAnimation - entire strip cycles through hues
    Yield Format: (r, g, b)
    """
    color: Tuple[int, int, int]


@dataclass
class ZoneFrame(BaseFrame):
    """
    Per-zone colors (each zone can have different color)

    Use Case: BreatheAnimation - zones breathe with individual colors
    Yield Format: (zone_id, r, g, b)
    """
    zone_colors: Dict[ZoneID, Tuple[int, int, int]]


@dataclass
class PixelFrame(BaseFrame):
    """
    Per-pixel colors (pixel-level control)

    Use Case: SnakeAnimation - snake moves pixel by pixel
    Yield Format: (zone_id, pixel_index, r, g, b)
    """
    zone_pixels: Dict[ZoneID, List[Tuple[int, int, int]]]
```

### 4.4 Preview Frame

```python
@dataclass
class PreviewFrame(BaseFrame):
    """
    Preview panel frame (always 8 pixels)

    Use Cases:
    - Animation preview (synchronized mini-animation)
    - Parameter preview (brightness bar, color fill, etc.)
    """
    pixels: List[Tuple[int, int, int]]  # Always length 8

    def __post_init__(self):
        if len(self.pixels) != 8:
            raise ValueError(f"Preview must have 8 pixels, got {len(self.pixels)}")
```

### 4.5 Type Aliases

```python
# Type aliases for clarity
MainStripFrame = FullStripFrame | ZoneFrame | PixelFrame
AnyFrame = MainStripFrame | PreviewFrame
```

---

## 5. FrameManager Design

### 5.1 Core Responsibilities

1. **Frame Collection**: Accept frames from multiple sources
2. **Priority Selection**: Choose highest priority frame each tick
3. **Synchronized Rendering**: Render main + preview atomically
4. **Lifecycle Management**: Start/stop ticker, pause/step modes
5. **Expiration Handling**: Discard expired frames (TTL)

### 5.2 Architecture

```python
class FrameManager:
    def __init__(self, fps: int = 60):
        # Dual queue system
        self.main_queues: Dict[FramePriority, deque[MainStripFrame]] = {
            p: deque(maxlen=2) for p in FramePriority
        }
        self.preview_queues: Dict[FramePriority, deque[PreviewFrame]] = {
            p: deque(maxlen=2) for p in FramePriority
        }

        # Registered targets
        self.main_strips: List[RenderTarget] = []      # ZoneStrip
        self.preview_strips: List[PreviewTarget] = []  # PreviewPanel

        # State
        self.running = False
        self.paused = False
        self.step_requested = False
        self.fps = fps
```

### 5.3 Frame Submission API

```python
# Type-specific submission methods
def submit_full_strip_frame(self, frame: FullStripFrame) -> None: ...
def submit_zone_frame(self, frame: ZoneFrame) -> None: ...
def submit_pixel_frame(self, frame: PixelFrame) -> None: ...
def submit_preview_frame(self, frame: PreviewFrame) -> None: ...
```

### 5.4 Ticker Loop

```python
async def _ticker_loop(self) -> None:
    """Main render loop @ 60 Hz"""
    while self.running:
        if not self.paused or self.step_requested:
            # Select highest priority frames
            main_frame = self._select_highest_priority_frame(self.main_queues)
            preview_frame = self._select_highest_priority_frame(self.preview_queues)

            # Render both atomically
            if main_frame:
                self._render_main_frame(main_frame)
            if preview_frame:
                self._render_preview_frame(preview_frame)

            self.step_requested = False

        await asyncio.sleep(1.0 / self.fps)
```

### 5.5 Priority Selection Algorithm

```python
def _select_highest_priority_frame(
    self,
    queues: Dict[FramePriority, deque]
) -> Optional[MainStripFrame | PreviewFrame]:
    """Select frame with highest priority from queues"""

    # Iterate priorities from highest to lowest
    for priority in sorted(FramePriority, reverse=True):
        queue = queues[priority]
        if queue:
            # Pop frames until we find non-expired one
            while queue:
                frame = queue.pop()
                if not frame.is_expired():
                    return frame  # Found valid frame!
            # All frames in this priority expired, try next priority

    return None  # No valid frames in any queue
```

### 5.6 Type-Specific Rendering

```python
def _render_main_frame(self, frame: MainStripFrame) -> None:
    """Render to all main strips (type dispatch)"""
    for strip in self.main_strips:
        if isinstance(frame, FullStripFrame):
            self._render_full_strip(frame, strip)
        elif isinstance(frame, ZoneFrame):
            self._render_zone_frame(frame, strip)
        elif isinstance(frame, PixelFrame):
            self._render_pixel_frame(frame, strip)

def _render_full_strip(self, frame: FullStripFrame, strip: RenderTarget):
    """Render single color to all zones"""
    r, g, b = frame.color
    for zone_name in strip.zones.keys():
        strip.set_zone_color(zone_name, r, g, b, show=False)
    strip.show()  # Single hardware update

def _render_zone_frame(self, frame: ZoneFrame, strip: RenderTarget):
    """Render per-zone colors"""
    for zone_id, (r, g, b) in frame.zone_colors.items():
        strip.set_zone_color(zone_id.name, r, g, b, show=False)
    strip.show()

def _render_pixel_frame(self, frame: PixelFrame, strip: RenderTarget):
    """Render per-pixel colors"""
    for zone_id, pixels in frame.zone_pixels.items():
        for pixel_idx, (r, g, b) in enumerate(pixels):
            if (r, g, b) != (None, None, None):  # Support sparse updates
                strip.set_pixel_color(zone_id.name, pixel_idx, r, g, b, show=False)
    strip.show()

def _render_preview_frame(self, frame: PreviewFrame):
    """Render to all preview strips"""
    for strip in self.preview_strips:
        strip.show_frame(frame.pixels)
```

### 5.7 Debug Features

```python
def pause(self) -> None:
    """Pause rendering (for debugging)"""
    self.paused = True

def resume(self) -> None:
    """Resume rendering"""
    self.paused = False

def step_frame(self) -> None:
    """Render single frame when paused (frame-by-frame mode)"""
    if self.paused:
        self.step_requested = True

def set_fps(self, fps: int) -> None:
    """Change FPS at runtime"""
    self.fps = max(1, min(fps, 120))
```

---

## 6. Preview System Redesign

### 6.1 Preview Panel High-Level Methods

Add to `PreviewPanel` class:

```python
def render_bar(self, value: int, max_value: int = 100, color: Tuple[int, int, int] = (255, 255, 255)):
    """Bar indicator (N pixels lit = percentage)"""

def render_solid(self, color: Tuple[int, int, int]):
    """Solid color (all pixels same color)"""

def render_gradient(self, color: Tuple[int, int, int], intensity: float):
    """Color with intensity modulation (0.0-1.0)"""

def render_multi_color(self, colors: List[Tuple[int, int, int]]):
    """Multiple colors (one per pixel, for zone preview)"""

def render_pattern(self, pattern: List[Tuple[int, int, int]]):
    """Custom pattern (for snake length, etc.)"""
```

### 6.2 Preview Modes

**Mode 1: Parameter Preview** (highest priority when adjusting):
```python
# Brightness adjustment
frame = PreviewFrame(
    priority=FramePriority.MANUAL,
    source=FrameSource.PREVIEW,
    pixels=[(255, 255, 255)] * 6 + [(0, 0, 0)] * 2  # 75% brightness
)
frame_manager.submit_preview_frame(frame)
```

**Mode 2: Zone Colors Preview** (static mode idle):
```python
# Show all zone colors
colors = [zone.get_rgb() for zone in zones[:8]]
frame = PreviewFrame(
    priority=FramePriority.MANUAL,
    source=FrameSource.PREVIEW,
    pixels=colors
)
frame_manager.submit_preview_frame(frame)
```

**Mode 3: Animation Preview** (animation running):
```python
# Synchronized mini-animation
async for preview_pixels in animation.run_preview(8):
    frame = PreviewFrame(
        priority=FramePriority.ANIMATION,
        source=FrameSource.ANIMATION,
        pixels=preview_pixels
    )
    frame_manager.submit_preview_frame(frame)
```

### 6.3 Preview Synchronization

Animations run **two parallel loops**:

```python
class AnimationEngine:
    async def start(self, animation_id, **params):
        # Start both loops
        self.main_task = asyncio.create_task(self._run_main_loop())
        self.preview_task = asyncio.create_task(self._run_preview_loop())

    async def _run_main_loop(self):
        """Main strip animation"""
        async for frame_data in self.current_animation.run():
            # Wrap in appropriate frame type and submit
            ...

    async def _run_preview_loop(self):
        """Preview panel animation (synchronized)"""
        async for preview_pixels in self.current_animation.run_preview(8):
            frame = PreviewFrame(
                priority=FramePriority.ANIMATION,
                source=FrameSource.ANIMATION,
                pixels=preview_pixels
            )
            self.frame_manager.submit_preview_frame(frame)
```

**Key**: Both `run()` and `run_preview()` use **same timing** (shared `start_time`, `frame_delay`) → perfect sync.

---

## 7. Migration Strategy

### 7.1 Backward Compatibility

**During Migration**:
- Keep existing methods on ZoneStrip/PreviewPanel
- Add new FrameManager alongside old direct calls
- Phase out direct calls incrementally

**Example**:
```python
# OLD (still works during migration)
strip.set_zone_color("LAMP", 255, 0, 0)

# NEW (after migration)
frame = ZoneFrame(
    priority=FramePriority.MANUAL,
    source=FrameSource.STATIC,
    zone_colors={ZoneID.LAMP: (255, 0, 0)}
)
frame_manager.submit_zone_frame(frame)
```

### 7.2 Incremental Rollout

**Week 1**: Phases 1-2 (Models + Preview Methods)
- No breaking changes
- Extensions only

**Week 2**: Phase 3 (FrameManager Core)
- Refactor FrameManager
- Still runs alongside old system

**Week 3**: Phases 4-5 (AnimationEngine + TransitionService)
- **Critical**: Remove direct strip calls
- High risk of bugs, extensive testing needed

**Week 4**: Phases 6-7 (Controllers)
- Lower risk
- Update parameter preview logic

**Week 5**: Phase 8 (Testing)
- Validation on hardware
- Bug fixes

### 7.3 Rollback Plan

**If critical bugs found**:
1. Revert to previous commit (git)
2. Keep new frame models (non-breaking)
3. Re-implement incrementally with more testing

**Feature flag approach**:
```python
USE_FRAME_MANAGER = os.getenv("DIUNA_USE_FRAME_MANAGER", "false") == "true"

if USE_FRAME_MANAGER:
    frame_manager.submit_zone_frame(frame)
else:
    strip.set_zone_color(zone_id, r, g, b)  # Fallback
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Frame Models**:
- Test TTL expiration
- Test frame validation (e.g., PreviewFrame must have 8 pixels)
- Test priority ordering

**FrameManager**:
- Test priority selection algorithm
- Test frame expiration
- Test pause/step mode
- Test dual queue rendering

### 8.2 Integration Tests

**AnimationEngine**:
- Test all 6 animations work with FrameManager
- Test parameter updates during animation
- Test animation switching with transitions

**TransitionService**:
- Test crossfade with FrameManager
- Test fade_in / fade_out
- Test transition locking

**Controllers**:
- Test parameter adjustment updates preview
- Test mode switching
- Test pulsing

### 8.3 Hardware Tests

**On Raspberry Pi** (90 pixels, WS2811 @ 12V):

**Visual Inspection**:
- ✅ No flickering during mode switches
- ✅ No color corruption during transitions
- ✅ Smooth animation (no visible stuttering)
- ✅ Pulsing doesn't conflict with static colors
- ✅ All 90 pixels respond (no dead zones)
- ✅ Correct color order (BRG for WS2811)
- ✅ Zone reversal works correctly

**Performance Testing**:
```python
# Add FPS counter to FrameManager
def measure_fps():
    """Run for 60 seconds, log FPS every 5 seconds"""
    for i in range(12):
        await asyncio.sleep(5)
        actual_fps = frame_manager.get_actual_fps()
        log.info(f"FPS measurement {i+1}/12: {actual_fps:.2f} Hz")

# Expected results:
# Pi 4: 59-61 FPS (stable)
# Pi 3: 55-60 FPS (minor jitter)
# Pi Zero: 35-45 FPS (acceptable for ambient lighting)
```

**Timing Validation**:
```python
# Verify WS2811 timing constraints
def test_frame_timing():
    """Measure actual inter-frame delays"""
    delays = []
    for _ in range(100):
        start = time.time()
        strip.show()
        end = time.time()
        delays.append(end - start)

    min_delay = min(delays)
    max_delay = max(delays)
    avg_delay = sum(delays) / len(delays)

    # Expected: min >= 2.75ms (2.7ms DMA + 50µs reset)
    assert min_delay >= 0.00275, f"Timing violation: {min_delay*1000:.3f}ms < 2.75ms"
    log.info(f"Frame timing: min={min_delay*1000:.2f}ms, avg={avg_delay*1000:.2f}ms, max={max_delay*1000:.2f}ms")
```

**Stress Tests**:
1. **10-minute full white test**:
   - Monitor IC temperature (should stay < 70°C)
   - Check power supply voltage (should stay > 11.5V)
   - Verify no brightness reduction at far zones
   - Confirm no thermal throttling (CPU temp < 80°C)

2. **Rapid parameter changes**:
   - Spin encoder continuously for 30 seconds
   - Monitor frame drops (should be 0)
   - Check FPS stability (should maintain 60±2 Hz)

3. **Mode switch spam**:
   - Toggle STATIC ↔ ANIMATION 50 times rapidly
   - Verify no crashes, memory leaks, or stuck states
   - Check transition smoothness (no black flashes)

4. **Animation switch spam**:
   - Cycle through all 5 animations 20 times
   - Verify crossfades work every time
   - Monitor memory usage (should be stable)

**Power Supply Verification**:
```bash
# Measure actual current draw
# 1. Full white (worst case)
# Expected: 5.4A peak, 65W @ 12V
# 2. Typical animation (mixed colors)
# Expected: 2-3A average, 30W @ 12V
# 3. Idle (black screen)
# Expected: 0.2A, 2.4W (IC quiescent current)
```

**Memory Leak Detection**:
```python
import tracemalloc

tracemalloc.start()
initial_memory = tracemalloc.get_traced_memory()

# Run for 1 hour with animations
await asyncio.sleep(3600)

final_memory = tracemalloc.get_traced_memory()
growth = (final_memory[0] - initial_memory[0]) / 1024 / 1024

# Expected: < 5MB growth (minor Python overhead)
assert growth < 5.0, f"Memory leak detected: {growth:.2f}MB growth"
```

**Responsiveness Testing**:
```python
# Measure encoder → LED update latency
def test_input_latency():
    """User rotates encoder, measure time to LED update"""
    # Attach timestamp logger to encoder callback
    latencies = []

    for _ in range(50):  # 50 encoder rotations
        encoder_time = time.time()
        # ... encoder callback fires ...
        led_update_time = time.time()
        latency = led_update_time - encoder_time
        latencies.append(latency)

    avg_latency = sum(latencies) / len(latencies) * 1000  # Convert to ms
    max_latency = max(latencies) * 1000

    # Expected: avg < 20ms, max < 50ms
    assert avg_latency < 20, f"Too slow: {avg_latency:.2f}ms average latency"
    assert max_latency < 50, f"Jitter too high: {max_latency:.2f}ms max latency"
```

### 8.4 Edge Case Tests

- Rapid mode switches (STATIC ↔ ANIMATION repeatedly)
- Rapid parameter adjustments (encoder spam)
- Power toggle during animation
- Animation switch during transition
- Preview during animation parameter change

---

## 9. Potential Risks

### 9.1 Performance Risks

**Risk**: Frame queues grow unbounded
**Mitigation**: `deque(maxlen=2)` per priority, TTL expiration

**Risk**: 60 Hz ticker can't keep up
**Mitigation**: Profile with `asyncio` debug mode, adaptive FPS if needed

**Risk**: Memory leaks from expired frames
**Mitigation**: TTL auto-expiration, max queue size

### 9.2 Functional Risks

**Risk**: Animations stop working after migration
**Mitigation**: Extensive testing Phase 8, rollback plan ready

**Risk**: Preview out of sync
**Mitigation**: Dual loop design (same timing for main + preview)

**Risk**: Transitions interrupted by animations
**Mitigation**: Priority system ensures transitions always win

### 9.3 Development Risks

**Risk**: Refactor takes longer than estimated
**Mitigation**: Phased approach, can pause between phases

**Risk**: Breaking changes cause instability
**Mitigation**: Feature flag, incremental rollout, thorough testing

---

## 10. Success Metrics

### 10.1 Functional Metrics

✅ **Zero flickering** during:
- Mode switches (STATIC ↔ ANIMATION)
- Animation switches
- Power toggles
- Parameter adjustments

✅ **Preview synchronization**:
- Preview panel matches main strip state
- Animation previews synchronized with main animation
- Parameter previews accurate (brightness bar = actual brightness)

✅ **No race conditions**:
- Transitions complete uninterrupted
- Pulsing doesn't conflict with manual updates
- Animations don't flicker during parameter changes

### 10.2 Performance Metrics

✅ **Stable FPS**: 60 Hz ± 2 Hz (measured over 60 seconds)
✅ **Low latency**: User input → visual update < 50ms
✅ **Memory stable**: No growth over 1 hour operation
✅ **CPU usage**: < 40% on Raspberry Pi 4

**Hardware-Specific Targets** (90 pixels):

| Raspberry Pi Model | Target FPS | Expected CPU | Notes |
|---|---|---|---|
| **Pi Zero / Zero W** | 30-40 FPS | 70-90% | Single core bottleneck, acceptable for ambient lighting |
| **Pi 3B / 3B+** | 50-60 FPS | 35-55% | Adequate, minor jitter during GC |
| **Pi 4 (2GB+)** | 60 FPS stable | 20-30% | Recommended, smooth operation |
| **Pi 5** | 60 FPS stable | 12-18% | Excellent headroom, future-proof |

**Physical Limits**:
- **Theoretical max FPS**: 363 FPS (2.75ms per frame: 2.7ms DMA + 50µs reset)
- **Python practical limit**: 100-150 FPS (asyncio overhead)
- **Target 60 FPS provides**: 40% headroom for system tasks, GC pauses, WiFi interrupts

**Timing Budget per 16.6ms Frame** (@60 FPS):
```
DMA transfer:       2.7ms  (16%)  ← Hardware, unavoidable
WS2811 reset:       0.05ms (0.3%) ← Hardware, unavoidable
Frame generation:   3-5ms  (20%)  ← Animation calculations
FrameManager:       1-2ms  (8%)   ← Priority selection, rendering
System overhead:    2-3ms  (15%)  ← Python GC, scheduler, WiFi
Buffer:             5-7ms  (40%)  ← Jitter absorption
Total:              16.6ms (100%)
```

**Jitter Sources** (expect ±1-3ms variance):
- Garbage collection: 10-50ms every 30-60s
- WiFi interrupts: 1-5ms sporadic
- SD card writes: 50-200ms when logging/saving state
- Encoder interrupts: <100µs (negligible)

### 10.3 Code Quality Metrics

✅ **Reduced complexity**: Remove 15+ direct `strip.show()` calls
✅ **Single responsibility**: FrameManager owns all rendering
✅ **Testability**: FrameManager can be unit tested in isolation
✅ **Extensibility**: Easy to add new frame sources (WebSocket, game mode)

### 10.4 Developer Experience

✅ **Debuggability**: Pause/step mode works
✅ **Visibility**: Can inspect current frame in FrameManager
✅ **Documentation**: This document + inline comments
✅ **Ease of change**: Adding new animation doesn't require changing FrameManager

---

## 11. Hardware-Specific Implementation Notes

### 11.1 WS2811 Timing Constants

**Add to FrameManager or constants file**:
```python
# Hardware timing constants for WS2811 @ 90 pixels
class WS2811Timing:
    """WS2811 protocol timing requirements"""

    # Protocol timing
    DATA_RATE_HZ = 800_000  # 800kHz
    BIT_TIME_US = 1.25      # 1.25µs per bit
    RESET_TIME_US = 50      # 50µs minimum reset pulse

    # Frame timing (90 pixels)
    BITS_PER_PIXEL = 24
    PIXEL_COUNT = 90
    TOTAL_BITS = BITS_PER_PIXEL * PIXEL_COUNT  # 2,160 bits

    # DMA transfer time
    DMA_TRANSFER_MS = (TOTAL_BITS * BIT_TIME_US) / 1000  # 2.7ms
    RESET_TIME_MS = RESET_TIME_US / 1000  # 0.05ms
    MIN_FRAME_TIME_MS = DMA_TRANSFER_MS + RESET_TIME_MS  # 2.75ms

    # FPS calculations
    THEORETICAL_MAX_FPS = 1000 / MIN_FRAME_TIME_MS  # 363 FPS
    PRACTICAL_MAX_FPS = 150  # Python overhead limit
    TARGET_FPS = 60  # Optimal balance

    @classmethod
    def validate_step_delay(cls, delay_ms: float) -> bool:
        """Check if step delay is safe for WS2811"""
        return delay_ms >= cls.MIN_FRAME_TIME_MS

    @classmethod
    def adjust_steps_for_timing(cls, duration_ms: float, requested_steps: int) -> int:
        """Adjust step count to maintain safe timing"""
        step_delay = duration_ms / requested_steps
        if step_delay < cls.MIN_FRAME_TIME_MS:
            safe_steps = int(duration_ms / cls.MIN_FRAME_TIME_MS)
            return max(1, safe_steps)
        return requested_steps
```

### 11.2 Recommended Pi Configuration

**For optimal LED control performance**:

```bash
# /boot/config.txt optimizations
# 1. Disable audio (frees up PWM channel)
dtparam=audio=off

# 2. Set CPU governor to performance
# Add to /etc/rc.local
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 3. Increase GPU memory (helps with DMA)
gpu_mem=128

# 4. Disable WiFi power management (reduces jitter)
# Add to /etc/rc.local
sudo iwconfig wlan0 power off

# 5. Reduce SD card writes (extend card life)
# Add to /etc/fstab
tmpfs /tmp tmpfs defaults,noatime,nosuid,size=50m 0 0
tmpfs /var/tmp tmpfs defaults,noatime,nosuid,size=50m 0 0
tmpfs /var/log tmpfs defaults,noatime,nosuid,mode=0755,size=50m 0 0
```

**Python optimizations**:
```python
# In main application startup
import gc

# More aggressive garbage collection (reduces pause duration)
gc.set_threshold(700, 10, 10)  # Default is (700, 10, 10)

# Or disable during critical sections
gc.disable()
# ... run animations ...
gc.enable()
```

### 11.3 Hardware Debugging Tools

**Add diagnostic endpoints for hardware validation**:

```python
class HardwareDiagnostics:
    """Diagnostic tools for LED hardware"""

    def __init__(self, frame_manager, strip):
        self.frame_manager = frame_manager
        self.strip = strip

    async def test_pattern_all_zones(self, duration_seconds: int = 5):
        """Cycle through zones one by one (dead zone detection)"""
        for zone_name in self.strip.zones.keys():
            log.info(f"Testing zone: {zone_name}")
            # Set zone to full white
            self.strip.set_zone_color(zone_name, 255, 255, 255)
            await asyncio.sleep(duration_seconds)
            # Clear
            self.strip.set_zone_color(zone_name, 0, 0, 0)

    async def test_timing_accuracy(self, iterations: int = 100):
        """Measure actual frame timing vs expected"""
        delays = []

        for _ in range(iterations):
            start = time.perf_counter()
            self.strip.show()
            end = time.perf_counter()
            delays.append((end - start) * 1000)  # Convert to ms

        results = {
            'min_ms': min(delays),
            'max_ms': max(delays),
            'avg_ms': sum(delays) / len(delays),
            'expected_min_ms': WS2811Timing.MIN_FRAME_TIME_MS,
            'violations': sum(1 for d in delays if d < WS2811Timing.MIN_FRAME_TIME_MS)
        }

        log.info(f"Timing test: {results}")
        return results

    async def test_fps_stability(self, duration_seconds: int = 60):
        """Measure FPS over time"""
        fps_samples = []

        for i in range(duration_seconds // 5):
            await asyncio.sleep(5)
            fps = self.frame_manager.get_actual_fps()
            fps_samples.append(fps)
            log.info(f"FPS sample {i+1}: {fps:.2f} Hz")

        return {
            'avg_fps': sum(fps_samples) / len(fps_samples),
            'min_fps': min(fps_samples),
            'max_fps': max(fps_samples),
            'variance': max(fps_samples) - min(fps_samples)
        }

    def test_color_accuracy(self):
        """Test BRG color order for WS2811"""
        test_colors = {
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'white': (255, 255, 255),
            'cyan': (0, 255, 255),
            'magenta': (255, 0, 255),
            'yellow': (255, 255, 0)
        }

        for name, (r, g, b) in test_colors.items():
            log.info(f"Testing color: {name} = ({r}, {g}, {b})")
            self.strip.set_zone_color('LAMP', r, g, b)
            input(f"Verify {name} is correct. Press Enter to continue...")
```

### 11.4 Production Monitoring

**Add to application for production deployment**:

```python
class ProductionMetrics:
    """Track production health metrics"""

    def __init__(self):
        self.frame_drops = 0
        self.timing_violations = 0
        self.last_fps_check = time.time()
        self.fps_history = deque(maxlen=60)  # 5 minutes @ 5s intervals

    def log_frame_drop(self, count: int = 1):
        """Record frame drop event"""
        self.frame_drops += count
        if self.frame_drops % 10 == 0:
            log.warn(f"Total frame drops: {self.frame_drops}")

    def log_timing_violation(self, actual_ms: float, expected_ms: float):
        """Record timing violation"""
        self.timing_violations += 1
        log.error(f"Timing violation #{self.timing_violations}: {actual_ms:.3f}ms < {expected_ms:.3f}ms")

    async def monitor_loop(self, frame_manager):
        """Background monitoring task"""
        while True:
            await asyncio.sleep(5)

            fps = frame_manager.get_actual_fps()
            self.fps_history.append(fps)

            # Alert if FPS drops significantly
            if fps < 50:
                log.warn(f"Low FPS detected: {fps:.2f} Hz")

            # Periodic summary
            if time.time() - self.last_fps_check > 300:  # Every 5 minutes
                avg_fps = sum(self.fps_history) / len(self.fps_history)
                log.info(f"5-min avg FPS: {avg_fps:.2f} Hz, drops: {self.frame_drops}, violations: {self.timing_violations}")
                self.last_fps_check = time.time()
```

### 11.5 Recovery Strategies

**Handle hardware failures gracefully**:

```python
class HardwareRecovery:
    """Automatic recovery from hardware failures"""

    @staticmethod
    async def recover_from_stuck_dma():
        """Attempt to recover from stuck DMA state"""
        log.error("DMA appears stuck, attempting recovery...")

        try:
            # 1. Stop all rendering
            frame_manager.pause()

            # 2. Clear strip
            strip.clear()
            await asyncio.sleep(0.1)

            # 3. Reinitialize (if possible)
            # Note: Full reinit requires restart in most cases

            # 4. Resume
            frame_manager.resume()
            log.info("DMA recovery successful")
            return True

        except Exception as e:
            log.error(f"DMA recovery failed: {e}")
            return False

    @staticmethod
    def detect_stuck_animation():
        """Detect if animation loop has frozen"""
        # Check if frames are still arriving
        last_frame_age = time.time() - frame_manager.last_show_time

        if last_frame_age > 1.0:  # No frame for 1 second
            log.error(f"Animation loop appears frozen (no frame for {last_frame_age:.1f}s)")
            return True
        return False
```

### 11.6 Thermal Management (Optional)

**For enclosed installations**:

```python
class ThermalMonitor:
    """Monitor and respond to thermal conditions"""

    def __init__(self, temp_threshold_c: float = 75.0):
        self.threshold = temp_threshold_c
        self.throttled = False

    def get_cpu_temp(self) -> float:
        """Read CPU temperature"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_millicelsius = int(f.read().strip())
                return temp_millicelsius / 1000.0
        except Exception as e:
            log.error(f"Failed to read CPU temp: {e}")
            return 0.0

    async def monitor_loop(self, frame_manager):
        """Background thermal monitoring"""
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds

            temp = self.get_cpu_temp()

            if temp > self.threshold and not self.throttled:
                log.warn(f"CPU temp {temp:.1f}°C exceeds threshold {self.threshold}°C - reducing brightness")
                # Reduce global brightness by 20%
                # (Implementation depends on your brightness control)
                self.throttled = True

            elif temp < self.threshold - 5 and self.throttled:
                log.info(f"CPU temp {temp:.1f}°C normalized - restoring brightness")
                self.throttled = False
```

---

## 12. Post-Refactoring Validation Checklist

### Phase-by-Phase Validation

After completing each phase, validate:

**✅ Phase 1 (Frame Models)**:
- [ ] All frame types serialize/deserialize correctly
- [ ] TTL expiration works as expected
- [ ] Priority enum ordering is correct (highest = TRANSITION)
- [ ] Frame validation catches invalid data (e.g., PreviewFrame with 7 pixels)

**✅ Phase 3 (FrameManager)**:
- [ ] Single `strip.show()` per tick confirmed (add assertion)
- [ ] Priority selection algorithm works (test with mixed priorities)
- [ ] Frame drops trigger warnings (test with >10 pending frames)
- [ ] FPS measurement is accurate (compare to external timer)
- [ ] Pause/step mode works (test with debugger attached)
- [ ] WS2811 timing constraints enforced (measure with oscilloscope if possible)

**✅ Phase 4 (AnimationEngine)**:
- [ ] All 5 animations render correctly (visual check)
- [ ] Preview panel synchronized with main strip
- [ ] Live parameter updates work (no animation restart needed)
- [ ] Animation switching is smooth (no flicker)
- [ ] Memory stable after 100 animation switches

**✅ Phase 5 (TransitionService)**:
- [ ] Crossfades are smooth (no color jumps)
- [ ] Timing violations prevented (check logs for warnings)
- [ ] Transitions can't be interrupted by animations
- [ ] Fade in/out work correctly
- [ ] Lock prevents concurrent transitions

**✅ Phases 6-7 (Controllers)**:
- [ ] Parameter preview updates instantly
- [ ] Pulsing doesn't conflict with other updates
- [ ] Mode switches are clean (no stuck states)
- [ ] All preview modes work (brightness, color, gradient, etc.)

**✅ Phase 8 (Integration Testing)**:
- [ ] No flickering in any scenario
- [ ] 60 FPS maintained (±2 Hz) over 10 minutes
- [ ] Memory stable over 1 hour operation
- [ ] CPU usage < 30% on Pi 4 (< 60% on Pi 3)
- [ ] Input latency < 50ms (encoder → LED update)
- [ ] All 90 pixels respond correctly
- [ ] Color accuracy verified (BRG order correct)

---

## 13. Known Hardware Limitations & Workarounds

### 13.1 Non-Real-Time OS

**Limitation**: Linux is not real-time, asyncio can have jitter.

**Impact**: Occasional frame delays (1-5ms jitter normal, up to 50ms during GC).

**Workarounds**:
- Target 60 FPS (not 120+) to leave headroom
- Disable WiFi power management
- Reduce SD card writes (use tmpfs for logs)
- Consider `nice -20` for LED process (highest priority)

### 13.2 Single DMA Channel

**Limitation**: rpi_ws281x uses one DMA channel, can't drive multiple strips independently.

**Current Solution**: ✅ Two separate strips on different GPIO pins (18 + 19) with separate PixelStrip instances.

**Why It Works**:
- GPIO 18 = PWM0 channel 0
- GPIO 19 = PCM (separate peripheral)
- Each has independent DMA engine

**Constraint**: Can't add a third strip without external controller (e.g., Teensy).

### 13.3 Precise Timing with Python

**Limitation**: Python interpreter overhead makes sub-millisecond precision difficult.

**Impact**: Can't reliably generate custom WS2811 pulses in pure Python.

**Solution**: ✅ rpi_ws281x library handles timing in C with DMA (correct approach).

### 13.4 GPIO Cleanup on Hard Crash

**Limitation**: No way to cleanup GPIO on kernel panic or power loss.

**Workarounds**:
- Hardware: Add pull-down resistor on data line (LEDs go black on disconnect)
- Software: Watchdog timer auto-restarts app if frozen
- Hardware: External watchdog circuit resets Pi if unresponsive

---

## Next Steps

1. ✅ **Review this plan** with team/stakeholders
2. 🔄 **Start Phase 1** - Atomic frame models (1 day)
3. 🔄 **Iterate through phases** - Follow incremental rollout
4. 📊 **Measure success** - Track metrics during testing
5. 🚀 **Deploy to production** - After validation on hardware

**Estimated Total Time**: 4-5 weeks
**Risk Level**: Medium-High (critical refactoring)
**Reward**: Clean architecture, extensibility, no flickering, production-grade reliability

**Hardware Validation Required**:
- Test on actual Raspberry Pi (not just development machine)
- Use oscilloscope to verify timing if experiencing issues
- Monitor temperature during 10-minute full-white test
- Validate with actual 90-pixel setup (not simulation)

---

**Related Documents**:
- [ANIMATION_RENDERING_SYSTEM.md](./ANIMATION_RENDERING_SYSTEM.md) - Current architecture with hardware details
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Overall system architecture
- [CLAUDE.md](../CLAUDE.md) - Development guidelines

**Hardware References**:
- [WS2811 Datasheet](https://www.solarbotics.com/download.php?file=2808) - Official protocol specs
- [rpi_ws281x GitHub](https://github.com/jgarff/rpi_ws281x) - Library documentation and issues
- [Tim's WS2812 Protocol Analysis](https://cpldcpu.wordpress.com/2014/01/14/light_ws2812-library-v2-0-part-i-understanding-the-ws2812/) - Deep dive into timing
