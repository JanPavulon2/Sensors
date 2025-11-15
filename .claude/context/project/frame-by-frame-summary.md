---
Last Updated: 2025-11-15
Updated By: @architecture-expert-sonnet
Changes: Summary and architectural analysis for frame-by-frame mode
---

# Frame-By-Frame Mode - Complete Analysis & Implementation Plan

## Executive Summary

We are implementing a **frame-by-frame animation debugging mode** that allows stepping through animation frames one at a time using keyboard control (A/D for prev/next, SPACE for play/pause).

**Status**: Architecture and specification complete. Ready for implementation by engineering agent.

**Impact**: Medium - Non-intrusive feature using existing FrameManager pause capability.

**Timeline**: 3-4 hours implementation + testing

---

## What We Discovered

### 1. Excellent Architectural Foundation ✅

The codebase has a **sophisticated multi-layered rendering system** that makes frame-by-frame debugging elegant:

**Layer 0 (Hardware)**: ZoneStrip, PreviewPanel
- Direct GPIO control via rpi_ws281x
- Hardware abstraction done correctly

**Layer 1 (Frames)**: Frame models with priority queues
- FullStripFrame, ZoneFrame, PixelFrame, PreviewFrame
- Priority-based selection (IDLE < MANUAL < PULSE < ANIMATION < TRANSITION < DEBUG)
- TTL-based expiration prevents ghost pixels

**Layer 2 (Rendering)**: FrameManager
- Centralized rendering with atomic frame submission
- **Already supports pause/resume!** (needed for frame stepping)
- Maintains separate queues for main strip and preview panel

**Layer 3 (Animation)**: AnimationEngine
- Async generator pattern for animation frames
- Live parameter updates
- Transition service for smooth crossfades

**Layer 4 (Controllers)**: StaticModeController, AnimationModeController
- Business logic cleanly separated
- Event-driven architecture via EventBus

**Implication**: Frame-by-frame mode can be implemented as a **non-intrusive controller** that uses existing pause/resume. No core architectural changes needed.

### 2. Issues Blocking Implementation 🔴

#### Bug #1: SnakeAnimation Zero Division

**File**: `src/animations/snake.py:130`

**Error**:
```
ZeroDivisionError: integer modulo by zero
pos = (self.current_position - i) % self.total_pixels
```

**Root Cause**:
```python
zones = []  # anim_test.py passes empty list
self.total_pixels = sum(self.zone_pixel_counts.values())  # = 0
```

**Line 130**: `pos = (self.current_position - i) % 0` → crash

**Fix**: Add validation in SnakeAnimation.__init__():
```python
if self.total_pixels == 0:
    raise ValueError(
        "SnakeAnimation requires at least one zone with pixels. "
        f"Got {len(zones)} zones."
    )
```

**Severity**: CRITICAL (blocks all tests)

---

#### Bug #2: FramePlaybackController API Mismatch

**File**: `src/controllers/led_controller/frame_playback_controller.py:56`

**Wrong**:
```python
self.frame_manager.submit_zone_frame(frame.zone_id, frame.pixels)
```

**Expected API**:
```python
submit_zone_frame(zone_colors: Dict[ZoneID, (r,g,b)], priority, source)
```

**Fix**:
```python
self.frame_manager.submit_frame(
    frame,
    priority=FramePriority.DEBUG,
    source=FrameSource.DEBUG
)
```

**Severity**: MEDIUM (prevents old playback controller from working)

---

### 3. Architecture Insights 💡

#### Why Frame-By-Frame is Elegant

The system uses **priority-based rendering**:
```
Priority Levels (highest wins):
- DEBUG (50)      ← Frame-by-frame frames here
- TRANSITION (40) ← Never active during debug
- ANIMATION (30)  ← Paused during frame stepping
- PULSE (20)      ← Not active in animation mode
- MANUAL (10)     ← Not active in animation mode
- IDLE (0)        ← Background
```

**How it works**:
1. Load animation frames into FrameByFrameController
2. Submit frames with DEBUG priority (50)
3. Call `frame_manager.pause()` to stop animation
4. FrameManager automatically selects DEBUG frames (highest priority)
5. When pressing SPACE for play, call `frame_manager.resume()`
6. Animation resumes naturally (highest priority in queue)

**No conflicts, no race conditions, no explicit cleanup needed!**

#### Frame Models Enable Clean Conversion

Animation yields tuples:
```python
(zone_id, r, g, b)              # Zone-based
(zone_id, pixel_idx, r, g, b)   # Pixel-based
(r, g, b)                       # Full strip
```

FrameByFrameController converts to Frame objects:
```python
if len(frame_data) == 3:        # (r, g, b)
    → FullStripFrame(color=...)
elif len(frame_data) == 4:      # (zone_id, r, g, b)
    → ZoneFrame(zone_colors=...)
elif len(frame_data) == 5:      # (zone_id, pixel_idx, r, g, b)
    → PixelFrame(zone_pixels=...)
```

**Clean type conversion via factory method pattern.**

---

## Implementation Roadmap

### Phase 1: Core Controller (2 hours)

**Create**: `src/controllers/led_controller/frame_by_frame_controller.py`

**Methods**:
```python
class FrameByFrameController:
    __init__(frame_manager, animation_engine, zone_service, logger)

    async load_animation(animation_id, **params) → int
        # Preload animation frames into _frames list
        # Return frame count

    async show_current_frame() → bool
        # Submit current frame to FrameManager (DEBUG priority)
        # Pause animation rendering
        # Log frame details

    async next_frame() → bool
        # Advance _current_index and render

    async previous_frame() → bool
        # Decrement _current_index and render

    async play(fps=30) → None
        # Start auto-playback loop

    async pause() → None
        # Stop auto-playback

    async toggle_play() → None
        # Play ↔ Pause

    async _playback_loop(fps) → None
        # Internal: Auto-playback loop

    def _convert_to_frame(frame_data) → Frame
        # Convert tuple to Frame object

    def _log_frame_info() → None
        # Detailed frame logging
```

**Deliverables**:
- ✅ Class skeleton
- ✅ load_animation() implementation
- ✅ Frame stepping (next/previous)
- ✅ Play/pause toggle
- ✅ Frame logging

---

### Phase 2: Interactive Session (1 hour)

**Add to FrameByFrameController**:
```python
async def run_interactive() → None
    # Keyboard loop with termios
    # Controls: A=prev, D=next, SPACE=play/pause, Q=quit
    # Logging of user actions
```

**Features**:
- Raw stdin input (no echo, no buffering)
- Non-blocking character reading
- Proper terminal restoration (finally block)
- Comprehensive logging

---

### Phase 3: Integration (1 hour)

**Integrate into LEDController**:
```python
class LEDController:
    def __init__(self, ...):
        self.frame_by_frame_controller = FrameByFrameController(...)

    async def handle_frame_by_frame_mode(self):
        # Load current animation
        # Run interactive session
        # Resume normal operation
```

**Trigger**:
- New button binding (e.g., long-press on button)
- Or debug CLI command
- Or special key sequence

---

### Phase 4: Bug Fixes (0.5 hours)

1. Fix SnakeAnimation zero division
2. Fix FramePlaybackController API mismatch
3. Verify anim_test.py uses real zones

---

### Phase 5: Testing (1 hour)

**Unit Tests**:
- Frame loading
- Navigation (wrapping)
- Play/pause toggle
- Frame conversion

**Integration Tests**:
- Load real animations (SNAKE, BREATHE, etc.)
- Step through frames
- Verify FrameManager pause works
- Check frame rendering to hardware

**Manual Tests**:
- Run frame-by-frame with SnakeAnimation
- Test all keyboard controls
- Verify logging output
- Test play/pause at various points

---

## Implementation Details for Coding Agent

### Template: FrameByFrameController.__init__()

```python
def __init__(self,
             frame_manager: FrameManager,
             animation_engine: AnimationEngine,
             zone_service: ZoneService,
             logger: Logger):
    """Initialize frame-by-frame controller."""
    self.frame_manager = frame_manager
    self.animation_engine = animation_engine
    self.zone_service = zone_service
    self.logger = logger

    # State
    self._frames: List[Frame] = []
    self._current_index: int = 0
    self._playing: bool = False
    self._play_task: Optional[asyncio.Task] = None
    self._animation_id: Optional[AnimationID] = None
    self._animation_params: Dict[str, Any] = {}

    # Metrics
    self._frame_times: List[float] = []
    self._load_start_time: float = 0

    self.logger.debug("FrameByFrameController initialized")
```

### Template: Frame Conversion

```python
def _convert_to_frame(self, frame_data) -> Frame:
    """Convert animation tuple to Frame object."""
    if len(frame_data) == 3 and isinstance(frame_data[0], int):
        # (r, g, b) - Full strip
        return FullStripFrame(
            color=frame_data,
            priority=FramePriority.DEBUG,
            source=FrameSource.DEBUG,
            ttl=1.0  # Don't expire
        )
    elif len(frame_data) == 4:
        # (zone_id, r, g, b) - Zone-based
        zone_id, r, g, b = frame_data
        return ZoneFrame(
            zone_colors={zone_id: (r, g, b)},
            priority=FramePriority.DEBUG,
            source=FrameSource.DEBUG,
            ttl=1.0
        )
    elif len(frame_data) == 5:
        # (zone_id, pixel_idx, r, g, b) - Pixel-based
        zone_id, pixel_idx, r, g, b = frame_data
        # Build pixel list
        pixels = [(0, 0, 0)] * (pixel_idx + 1)
        pixels[pixel_idx] = (r, g, b)
        return PixelFrame(
            zone_pixels={zone_id: pixels},
            priority=FramePriority.DEBUG,
            source=FrameSource.DEBUG,
            ttl=1.0
        )
    else:
        raise ValueError(
            f"Unknown frame format: {frame_data} "
            f"(length {len(frame_data)})"
        )
```

### Template: Logging Frame Info

```python
def _log_frame_info(self) -> None:
    """Log detailed frame information."""
    if not self._frames:
        return

    frame = self._frames[self._current_index]

    # Header
    self.logger.info(
        f"Frame {self._current_index + 1}/{len(self._frames)}",
        animation=self._animation_id.name if self._animation_id else "?",
        status="PAUSED" if not self._playing else "PLAYING"
    )

    # Frame-specific details
    if isinstance(frame, FullStripFrame):
        r, g, b = frame.color
        self.logger.debug(
            "Full Strip",
            color=f"RGB({r}, {g}, {b})",
            hex=f"#{r:02x}{g:02x}{b:02x}"
        )

    elif isinstance(frame, ZoneFrame):
        self.logger.debug("Zone Colors:")
        for zone_id, (r, g, b) in sorted(frame.zone_colors.items()):
            self.logger.debug(
                f"  {zone_id.name}: RGB({r}, {g}, {b})"
            )

    elif isinstance(frame, PixelFrame):
        self.logger.debug("Pixel Data:")
        for zone_id, pixels in sorted(frame.zone_pixels.items()):
            lit_count = sum(1 for r, g, b in pixels if any([r, g, b]))
            self.logger.debug(
                f"  {zone_id.name}: {len(pixels)} pixels ({lit_count} lit)"
            )
```

### Important Notes

**Use asyncio.Lock() for state changes**:
```python
# If concurrent access possible:
self._state_lock = asyncio.Lock()

async def next_frame(self):
    async with self._state_lock:
        self._current_index = (self._current_index + 1) % len(self._frames)
```

**Use asyncio.Event() for coordination**:
```python
# Signal when playback completes:
self._playback_done = asyncio.Event()

async def _playback_loop(self, fps):
    ...
    finally:
        self._playback_done.set()
```

**Handle cancellation gracefully**:
```python
async def _playback_loop(self, fps):
    try:
        while self._playing:
            ...
    except asyncio.CancelledError:
        self.logger.debug("Playback cancelled")
        # Cleanup here
```

---

## Key Design Decisions

### 1. Offline Frame Preload (Not Live Capture)

**Chosen**: Preload all frames into `_frames` list before interactive session

**Rationale**:
- Deterministic behavior (frame list doesn't change during stepping)
- Better debugging (can rewind, inspect, analyze)
- No animation loop interference
- Simpler implementation

**Alternative**: Live capture from animation (not chosen)
- Would require pausing animation mid-stream
- Complex synchronization with AnimationEngine
- Less clear debugging semantics

### 2. DEBUG Priority (50) for Frame Submission

**Chosen**: Submit frames with FramePriority.DEBUG

**Rationale**:
- Highest priority (50) overrides everything (TRANSITION=40, ANIMATION=30)
- FrameManager automatically selects it
- Clean separation: debug frames vs. animation frames

**Alternative**: Custom override in FrameManager (not chosen)
- Adds complexity to core system
- Priority system already handles it elegantly

### 3. Keyboard Input via stdin

**Chosen**: Termios + tty.setcbreak() for raw input

**Rationale**:
- Works on SSH sessions (unlike evdev)
- Simple (no external dependencies)
- Proven in existing anim_test.py
- Easy to add to any controller

**Alternative**: evdev (not chosen)
- Requires hardware keyboard device
- Fails on SSH/remote

### 4. Play Loops with asyncio.sleep()

**Chosen**: Auto-playback loop calls `await asyncio.sleep(frame_delay)`

**Rationale**:
- Respects frame rate (60 FPS default, adjustable)
- Yields control to other tasks
- Can be cancelled cleanly via `_play_task.cancel()`

**Alternative**: Use FrameManager FPS directly (not chosen)
- Would require internal FrameManager loop modification
- Decouples frame stepping from playback

---

## Testing Checklist

### Unit Tests
- [ ] Frame loading (preload_animation)
- [ ] Frame navigation (next/previous with wrapping)
- [ ] Play/pause toggle
- [ ] Frame conversion (tuple → Frame object)
- [ ] Empty frames list handling

### Integration Tests
- [ ] Load SnakeAnimation with real zones
- [ ] Load BreatheAnimation
- [ ] Load ColorCycleAnimation
- [ ] Step through 10 frames
- [ ] Play for 2 seconds
- [ ] Pause and verify FrameManager is paused
- [ ] Resume and verify animation continues

### Hardware Tests
- [ ] Frame renders to physical LEDs
- [ ] Colors match expected values
- [ ] No flickering during stepping
- [ ] Preview panel updates (if supported)

### Manual Tests
- [ ] Keyboard input (A, D, SPACE, Q)
- [ ] Wrapping (previous at frame 0 → last)
- [ ] Logging output (frame info, controls)
- [ ] Performance (no stutter, responsive)

---

## Performance Expectations

**Frame Loading** (SnakeAnimation, 10-second @60 FPS):
- 600 frames × ~10 KB per frame = ~6 MB memory
- Load time: ~2-3 seconds
- Acceptable on Raspberry Pi 4

**Frame Stepping**:
- Render time: <1 ms (FrameManager pause + frame submission)
- User perceives: Instant response

**Auto-Playback**:
- 30 FPS default (33 ms per frame)
- 60 FPS optional (16.6 ms per frame)
- No stuttering expected

---

## Future Enhancements

**Phase 2 (Low Priority)**:
- [ ] Frame scrubber (jump to specific frame by index)
- [ ] Speed control (2x, 0.5x playback)
- [ ] Frame export (save as JSON/CSV for analysis)
- [ ] Thermal imaging overlay (debug color accuracy)

**Phase 3**:
- [ ] Multi-animation comparison (view two animations side-by-side)
- [ ] Frame-by-frame diff (highlight changed pixels)
- [ ] Animation rewind with slowdown
- [ ] Snapshot capture (save frame data)

---

## Conclusion

**What we have**:
- ✅ Excellent architectural foundation
- ✅ Clear design pattern (priority-based rendering)
- ✅ Existing FrameManager pause capability
- ✅ Complete specification document
- ✅ Implementation templates

**What's blocking us**:
- 🔴 SnakeAnimation zero division bug
- 🔴 FramePlaybackController API mismatch

**What's next**:
1. Fix the two bugs
2. Implement FrameByFrameController (3-4 hours)
3. Test with real animations
4. Integrate into main controller

**Estimated Implementation Time**: 4-5 hours total

**Architectural Impact**: Minimal (uses existing systems, no core changes)

**User Impact**: High (enables deep animation debugging)

---

## Document References

**For Implementation Agent**:
- Read: `.claude/context/project/frame-by-frame-implementation.md` (complete spec)
- Refer: `.claude/context/architecture/rendering-system.md` (system architecture)
- Check: `.claude/context/project/todo.md` (bug list)

**For Code References**:
- `src/animations/base.py` - BaseAnimation interface
- `src/animations/snake.py` - Example async generator
- `src/engine/frame_manager.py` - FrameManager API
- `src/models/frame.py` - Frame models
- `src/anim_test.py` - Keyboard input reference

