---
Last Updated: 2025-11-15
Updated By: @architecture-expert-sonnet
Changes: Complete frame-by-frame mode specification and implementation plan
---

# Frame-By-Frame Animation Mode - Implementation Plan

## 1. Overview

**Goal**: Enable stepping through animation frames one at a time using keyboard input, with live logging and debug information.

**Use Cases**:
- Deep animation debugging (verify exact frame colors)
- Slow-motion playback (understand animation behavior)
- Frame capture for documentation
- Performance analysis (measure rendering per frame)

**Design Principle**: Build on top of existing `FramePlaybackController` and `FrameManager` infrastructure.

---

## 2. Current State Analysis

### 2.1 What We Have

✅ **FramePlaybackController** (`src/controllers/led_controller/frame_playback_controller.py`):
- Offline frame capture: `preload_animation(anim_id, **params)`
- Frame storage: `_frames` list
- Playback controls: `next_frame()`, `previous_frame()`, `play()`, `stop()`
- Current frame access: `current_frame()`

✅ **FrameManager** (`src/engine/frame_manager.py`):
- Priority queue system
- Pause/step capabilities
- FPS control
- Frame submission API

✅ **Keyboard Input** (`anim_test.py`):
- Working stdin-based keyboard handler
- Can detect arrow keys
- Can detect 'q' for quit

### 2.2 What's Broken

❌ **SnakeAnimation Zero Division Error**:
```python
# src/animations/snake.py:130
pos = (self.current_position - i) % self.total_pixels
# ERROR: total_pixels = 0 (zones list is empty in test!)
```

**Root Cause**: `anim_test.py` line 40 passes empty zones list:
```python
zones = []  # ← EMPTY! Should be populated
```

**Impact**: SnakeAnimation can't initialize; crashes on `__init__`.

❌ **FramePlaybackController Design Issues**:
1. Designed for offline frame capture (preload entire animation)
2. Not integrated with live event handling system
3. Doesn't interact with FrameManager's pause/step
4. Frame submission uses old API (`submit_zone_frame(zone_id, pixels)`)

### 2.3 What We Need

**New Component**: `FrameByFrameController` (orchestrates the feature)
- Manages frame-by-frame playback state
- Handles keyboard input (A/D for prev/next, SPACE for play/pause)
- Coordinates with FrameManager (pause/resume rendering)
- Provides logging/debugging output
- Integrates with animation lifecycle

**Enhanced FrameManager**:
- Already has pause/step capability
- Just needs to be used by controller

**Enhanced Logging**:
- Frame info: index, zone colors, pixel data
- Performance metrics: time per frame, total animation duration
- State info: paused/playing, current animation

---

## 3. Architecture - FrameByFrameController

### 3.1 Class Design

**Location**: `src/controllers/led_controller/frame_by_frame_controller.py` (NEW)

```python
class FrameByFrameController:
    """
    Frame-by-frame animation debugging and playback controller.

    Manages stepping through animation frames one at a time with keyboard control.
    Integrates with FrameManager to pause/resume rendering.

    Features:
    - Frame stepping (next/previous)
    - Play/pause toggle
    - Live frame information logging
    - Animation preloading
    - Keyboard input handling

    Keyboard Controls:
    - [A]: Previous frame
    - [D]: Next frame
    - [SPACE]: Play / Pause
    - [Q]: Quit

    Usage:
        controller = FrameByFrameController(
            frame_manager=frame_manager,
            animation_engine=animation_engine,
            zone_service=zone_service,
            logger=logger
        )

        # Load animation into frame buffer
        await controller.load_animation(AnimationID.SNAKE, speed=50)

        # Start frame-by-frame session
        await controller.run_interactive()
```

### 3.2 Core Methods

**Initialization & Setup**:
```python
def __init__(self,
             frame_manager: FrameManager,
             animation_engine: AnimationEngine,
             zone_service: ZoneService,
             logger: Logger):
    """
    Initialize frame-by-frame controller.

    Args:
        frame_manager: FrameManager for pause/resume
        animation_engine: AnimationEngine to create animation instances
        zone_service: ZoneService for zone info
        logger: Logger for frame info output
    """
    self.frame_manager = frame_manager
    self.animation_engine = animation_engine
    self.zone_service = zone_service
    self.logger = logger

    # State
    self._frames: List[Frame] = []           # Preloaded frames
    self._current_index: int = 0             # Current frame index
    self._playing: bool = False              # Play/pause state
    self._play_task: Optional[Task] = None   # Background playback task
    self._animation_id: Optional[AnimationID] = None
    self._animation_params: Dict[str, Any] = {}

    # Metrics
    self._frame_times: List[float] = []      # Frame render times
    self._load_start_time: float = 0
```

**Frame Loading**:
```python
async def load_animation(self,
                         animation_id: AnimationID,
                         **animation_params) -> int:
    """
    Preload animation frames into memory.

    Args:
        animation_id: Which animation to load
        **animation_params: Animation parameters (speed, hue, length, etc.)

    Returns:
        Total frame count loaded

    Example:
        frame_count = await controller.load_animation(
            AnimationID.SNAKE,
            ANIM_SPEED=50,
            ANIM_SNAKE_LENGTH=5
        )
        logger.info(f"Loaded {frame_count} frames")
    """
    self.logger.info(
        f"Loading animation: {animation_id.name}",
        params=animation_params
    )

    self._animation_id = animation_id
    self._animation_params = animation_params
    self._frames.clear()
    self._current_index = 0

    # Create animation instance
    anim = self.animation_engine.create_animation_instance(
        animation_id,
        **animation_params
    )

    # Capture all frames
    self._load_start_time = time.perf_counter()

    async for frame_data in anim.run():
        # Convert tuple to Frame object
        frame = self._convert_to_frame(frame_data)
        self._frames.append(frame)

        # Show progress every 10 frames
        if len(self._frames) % 10 == 0:
            self.logger.debug(
                f"Captured {len(self._frames)} frames...",
                current_frame_data=frame_data
            )

    load_duration = time.perf_counter() - self._load_start_time

    self.logger.info(
        f"Animation loaded: {len(self._frames)} frames in {load_duration:.2f}s",
        animation=animation_id.name,
        avg_frame_time=f"{(load_duration / len(self._frames) * 1000):.2f}ms"
    )

    return len(self._frames)
```

**Frame Navigation**:
```python
async def show_current_frame(self) -> bool:
    """
    Render current frame to hardware.

    Submits frame to FrameManager with high priority,
    pauses animation rendering, and logs frame info.

    Returns:
        True if rendered successfully, False if no frame loaded
    """
    if not self._frames:
        self.logger.warn("No frames loaded")
        return False

    frame = self._frames[self._current_index]

    # Pause FrameManager (stop animation rendering)
    self.frame_manager.pause()

    # Submit frame with high priority (DEBUG level)
    self.frame_manager.submit_frame(
        frame,
        priority=FramePriority.DEBUG,
        source=FrameSource.DEBUG
    )

    # Log frame information
    self._log_frame_info()

    return True

async def next_frame(self) -> bool:
    """
    Advance to next frame (wraps around).

    Returns:
        True if frame exists, False if no frames loaded
    """
    if not self._frames:
        self.logger.warn("No frames loaded")
        return False

    self._current_index = (self._current_index + 1) % len(self._frames)
    return await self.show_current_frame()

async def previous_frame(self) -> bool:
    """
    Go back to previous frame (wraps around).

    Returns:
        True if frame exists, False if no frames loaded
    """
    if not self._frames:
        self.logger.warn("No frames loaded")
        return False

    self._current_index = (self._current_index - 1) % len(self._frames)
    return await self.show_current_frame()
```

**Playback Control**:
```python
async def play(self, fps: int = 30) -> None:
    """
    Start automatic playback (loop through frames).

    Args:
        fps: Playback speed (default 30 FPS)

    Note:
        - If FrameManager is paused, resumes it
        - Loops continuously (wraps to frame 0 at end)
    """
    if self._playing:
        self.logger.warn("Already playing")
        return

    if not self._frames:
        self.logger.warn("No frames loaded")
        return

    self._playing = True
    self.frame_manager.resume()  # Resume FrameManager rendering

    self.logger.info(
        f"Starting playback at {fps} FPS",
        total_frames=len(self._frames)
    )

    self._play_task = asyncio.create_task(
        self._playback_loop(fps)
    )

async def pause(self) -> None:
    """
    Pause automatic playback (freeze on current frame).

    Pauses FrameManager, keeping current frame visible.
    """
    self._playing = False

    if self._play_task:
        self._play_task.cancel()
        try:
            await self._play_task
        except asyncio.CancelledError:
            pass
        self._play_task = None

    self.frame_manager.pause()

    self.logger.info(
        "Playback paused",
        current_frame=self._current_index
    )

async def toggle_play(self) -> None:
    """
    Toggle between playing and paused state.
    """
    if self._playing:
        await self.pause()
    else:
        await self.play()
```

**Internal Helpers**:
```python
async def _playback_loop(self, fps: int) -> None:
    """
    Internal: Loop that plays frames continuously.

    Args:
        fps: Frames per second
    """
    frame_delay = 1.0 / fps

    try:
        while self._playing:
            # Show current frame
            await self.show_current_frame()

            # Advance to next
            self._current_index = (self._current_index + 1) % len(self._frames)

            # Sleep
            await asyncio.sleep(frame_delay)
    except asyncio.CancelledError:
        self.logger.debug("Playback loop cancelled")

def _convert_to_frame(self, frame_data) -> Frame:
    """
    Convert animation yield tuple to Frame object.

    Handles:
    - 3-tuple: (r, g, b) → FullStripFrame
    - 4-tuple: (zone_id, r, g, b) → ZoneFrame
    - 5-tuple: (zone_id, pixel_idx, r, g, b) → PixelFrame

    Args:
        frame_data: Tuple from animation.run()

    Returns:
        Frame object (FullStripFrame, ZoneFrame, or PixelFrame)
    """
    if len(frame_data) == 3 and isinstance(frame_data[0], int):
        # Full strip: (r, g, b)
        return FullStripFrame(
            color=frame_data,
            priority=FramePriority.DEBUG,
            source=FrameSource.DEBUG
        )

    elif len(frame_data) == 4:
        # Zone-based: (zone_id, r, g, b)
        zone_id, r, g, b = frame_data
        return ZoneFrame(
            zone_colors={zone_id: (r, g, b)},
            priority=FramePriority.DEBUG,
            source=FrameSource.DEBUG
        )

    elif len(frame_data) == 5:
        # Pixel-based: (zone_id, pixel_idx, r, g, b)
        zone_id, pixel_idx, r, g, b = frame_data
        return PixelFrame(
            zone_pixels={zone_id: [(r, g, b)] * (pixel_idx + 1)},
            priority=FramePriority.DEBUG,
            source=FrameSource.DEBUG
        )

    else:
        raise ValueError(f"Unknown frame format: {frame_data}")

def _log_frame_info(self) -> None:
    """
    Log detailed information about current frame.

    Output:
    - Frame index and total count
    - Animation and parameters
    - Zone colors (for zone-based animations)
    - Pixel data (for pixel-based animations)
    - Performance metrics
    """
    if not self._frames:
        return

    frame = self._frames[self._current_index]

    # Header
    self.logger.info(
        f"Frame {self._current_index + 1}/{len(self._frames)}",
        animation=self._animation_id.name if self._animation_id else "unknown",
        status="PAUSED" if not self._playing else "PLAYING"
    )

    # Frame details (varies by frame type)
    if isinstance(frame, FullStripFrame):
        r, g, b = frame.color
        self.logger.debug(
            "Full Strip Color",
            r=r, g=g, b=b,
            hex=f"#{r:02x}{g:02x}{b:02x}"
        )

    elif isinstance(frame, ZoneFrame):
        self.logger.debug("Zone Colors:")
        for zone_id, (r, g, b) in sorted(frame.zone_colors.items()):
            zone_name = zone_id.name if hasattr(zone_id, 'name') else str(zone_id)
            self.logger.debug(
                f"  {zone_name}: RGB({r}, {g}, {b}) #{r:02x}{g:02x}{b:02x}"
            )

    elif isinstance(frame, PixelFrame):
        self.logger.debug("Pixel Data (by zone):")
        for zone_id, pixels in sorted(frame.zone_pixels.items()):
            zone_name = zone_id.name if hasattr(zone_id, 'name') else str(zone_id)
            pixel_count = len(pixels)
            lit_count = sum(1 for r, g, b in pixels if any([r, g, b]))
            self.logger.debug(
                f"  {zone_name}: {pixel_count} pixels ({lit_count} lit)",
                pixels_preview=pixels[:5]  # Show first 5 pixels
            )

    # Performance metrics
    if self._frame_times:
        avg_ms = (sum(self._frame_times) / len(self._frame_times)) * 1000
        self.logger.debug(
            f"Average frame time: {avg_ms:.2f}ms"
        )
```

### 3.3 Interactive Session Handler

```python
async def run_interactive(self) -> None:
    """
    Run interactive frame-by-frame session with keyboard input.

    Blocks until user quits ('q' key).

    Controls:
    - [A]: Previous frame
    - [D]: Next frame
    - [SPACE]: Play / Pause
    - [Q]: Quit

    Note:
        - Configures stdin for raw input (no echo, line buffering disabled)
        - Restores stdin on exit (finally block)
        - Logs all input events
    """
    if not self._frames:
        self.logger.error("No animation loaded. Call load_animation() first.")
        return

    self.logger.info(
        "Starting interactive frame-by-frame session",
        total_frames=len(self._frames),
        controls="[A]=prev  [D]=next  [SPACE]=play/pause  [Q]=quit"
    )

    # Configure stdin for raw input
    stdin_fd = sys.stdin.fileno()
    stdin_settings = termios.tcgetattr(stdin_fd)
    tty.setcbreak(stdin_fd)

    try:
        await self.show_current_frame()  # Show first frame

        while True:
            # Non-blocking character read
            loop = asyncio.get_running_loop()
            ch = await loop.run_in_executor(None, sys.stdin.read, 1)

            if not ch:
                continue

            # Handle input
            if ch == 'q':
                self.logger.info("Quit requested by user")
                break

            elif ch == 'a':
                self.logger.debug("User input: Previous frame")
                await self.previous_frame()

            elif ch == 'd':
                self.logger.debug("User input: Next frame")
                await self.next_frame()

            elif ch == ' ':
                self.logger.debug(
                    "User input: Toggle play/pause",
                    new_state="PLAYING" if not self._playing else "PAUSED"
                )
                await self.toggle_play()

            else:
                self.logger.debug(f"Unknown input: {repr(ch)}")

    finally:
        # Restore stdin
        termios.tcsetattr(stdin_fd, termios.TCSADRAIN, stdin_settings)

        # Cleanup
        if self._playing:
            await self.pause()

        self.logger.info("Interactive session ended")
```

---

## 4. FrameManager Enhancements

### 4.1 Pause/Step API

**Already exists in FrameManager**:
```python
class FrameManager:
    def pause(self) -> None:
        """Pause rendering"""
        self._paused = True

    def resume(self) -> None:
        """Resume rendering"""
        self._paused = False

    async def step_frame(self) -> None:
        """Render one frame and pause"""
        self._paused = True
        self._step_pending = True
        await asyncio.sleep(0.02)  # Wait for one render cycle
```

### 4.2 Render Loop Changes

**Current** (from frame_manager.py):
```python
async def _render_loop(self):
    while self.running:
        if not self._paused:
            # Fetch and render frames
            self._render_cycle()

        await asyncio.sleep(1.0 / self.fps)
```

**Usage**:
- `frame_manager.pause()` → stops animation rendering, holds last frame
- `frame_manager.resume()` → resumes animation rendering
- Frame submission still works while paused

---

## 5. Integration Points

### 5.1 LEDController Integration

**Location**: `src/controllers/led_controller/led_controller.py`

**Changes Needed**:
```python
class LEDController:
    def __init__(self, ...):
        # ... existing init ...

        # NEW: Frame-by-frame controller
        self.frame_by_frame_controller = FrameByFrameController(
            frame_manager=frame_manager,
            animation_engine=animation_engine,
            zone_service=zone_service,
            logger=logger
        )

    async def handle_frame_by_frame_mode(self) -> None:
        """
        Enter frame-by-frame debugging mode.

        Called by:
        - Button press (debug button?)
        - User command via CLI/API
        """
        # Load current animation
        animation_id = self.animation_service.get_current_id()
        animation_params = self.animation_service.get_current_params()

        # Load frames
        await self.frame_by_frame_controller.load_animation(
            animation_id,
            **animation_params
        )

        # Run interactive session
        await self.frame_by_frame_controller.run_interactive()

        # Resume normal operation
        self.frame_manager.resume()
```

### 5.2 AnimationEngine Integration

**No changes needed** - Already has:
- `create_animation_instance(anim_id, **params)` method
- Animation instance is callable: `async for frame in anim.run()`

---

## 6. Bug Fixes Required

### 6.1 SnakeAnimation Zero Division

**File**: `src/animations/snake.py:63`

**Current**:
```python
self.total_pixels = sum(self.zone_pixel_counts.values())
```

**Issue**: If `zones` list is empty, `total_pixels = 0` → line 130 crashes.

**Fix**:
```python
self.total_pixels = sum(self.zone_pixel_counts.values())

if self.total_pixels == 0:
    raise ValueError("SnakeAnimation requires at least one zone with pixels")
```

**Better**: Default to dummy zones in test if needed:
```python
# In anim_test.py
if not zones:
    zones = ZoneService.get_all()  # Or create dummy zones
```

### 6.2 Frame Conversion in FramePlaybackController

**File**: `src/controllers/led_controller/frame_playback_controller.py:56`

**Current**:
```python
self.frame_manager.submit_zone_frame(frame.zone_id, frame.pixels)
```

**Issue**: API mismatch - `submit_zone_frame()` expects:
```python
submit_zone_frame(zone_colors: Dict[ZoneID, (r,g,b)], priority, source)
```

Not a `zone_id` and `pixels`.

**Fix**: Use correct FrameManager API or convert frame properly.

---

## 7. Logging & Debugging Output

### 7.1 Frame Information Display

**Example Output**:
```
[RENDER_ENGINE] INFO: Frame 47/240
  animation: SNAKE
  status: PAUSED

[RENDER_ENGINE] DEBUG: Pixel Data (by zone):
  FLOOR: 12 pixels (3 lit)
    pixels_preview: [(255, 0, 0), (200, 0, 0), (100, 0, 0), (0, 0, 0), (0, 0, 0)]
  LAMP: 19 pixels (2 lit)
    pixels_preview: [(255, 0, 0), (200, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)]
  TOP: 4 pixels (0 lit)
    pixels_preview: [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)]

[RENDER_ENGINE] DEBUG: Average frame time: 16.32ms
```

### 7.2 Input Event Logging

**Example Output**:
```
[RENDER_ENGINE] DEBUG: User input: Next frame
[RENDER_ENGINE] INFO: Frame 48/240
  animation: SNAKE
  status: PAUSED
  ...

[RENDER_ENGINE] DEBUG: User input: Toggle play/pause
[RENDER_ENGINE] INFO: Playback started at 60 FPS
  total_frames: 240
```

### 7.3 Performance Metrics

**Collect**:
- Frame load time (total animation duration)
- Average frame render time
- Playback FPS (during play)

**Display**:
```
[RENDER_ENGINE] INFO: Animation loaded: 240 frames in 3.42s
  animation: SNAKE
  avg_frame_time: 14.25ms
  animation_params: {'ANIM_SPEED': 50, 'ANIM_SNAKE_LENGTH': 5}
```

---

## 8. Implementation Checklist

### Phase 1: Core Controller ✓ (To Be Done)
- [ ] Create `FrameByFrameController` class
- [ ] Implement `load_animation()` (frame capture)
- [ ] Implement `show_current_frame()` (render + log)
- [ ] Implement `next_frame()` and `previous_frame()`
- [ ] Implement `play()` and `pause()`
- [ ] Implement `_log_frame_info()` (detailed logging)

### Phase 2: Interactive Session ✓ (To Be Done)
- [ ] Implement `run_interactive()` (keyboard loop)
- [ ] Test keyboard input (A, D, SPACE, Q)
- [ ] Verify frame stepping works
- [ ] Verify play/pause toggle works

### Phase 3: Integration ✓ (To Be Done)
- [ ] Integrate into LEDController
- [ ] Test with real hardware
- [ ] Verify FrameManager pause/resume works
- [ ] Test with different animation types

### Phase 4: Bug Fixes ✓ (To Be Done)
- [ ] Fix SnakeAnimation zero division error
- [ ] Fix FramePlaybackController API mismatch
- [ ] Test anim_test.py with real zones

### Phase 5: Enhancement (Future)
- [ ] Add frame scrubber (jump to specific frame)
- [ ] Add speed control (fast/slow playback)
- [ ] Add frame export (save frame data)
- [ ] Add visual frame info overlay

---

## 9. Keyboard Control Design

### 9.1 Control Mapping

| Key | Action | Notes |
|-----|--------|-------|
| **A** | Previous Frame | Wraps to last frame |
| **D** | Next Frame | Wraps to first frame |
| **SPACE** | Play / Pause | Toggles state |
| **Q** | Quit | Restores normal mode |

### 9.2 Alternative Design (Not Chosen)

Could use arrow keys:
```
← Previous (Left)
→ Next (Right)
```

**Problem**: Requires escape sequence parsing (`\x1b[C`, `\x1b[D`)
**Chosen**: Simple single-char keys (A, D, SPACE) are clearer

---

## 10. Frame Data Format Reference

### Animation Yield Formats

**Zone-Based** (BreatheAnimation, ColorFadeAnimation):
```python
yield (zone_id, r, g, b)  # 4-tuple
# Converted to: ZoneFrame(zone_colors={zone_id: (r, g, b)})
```

**Pixel-Based** (SnakeAnimation, ColorSnakeAnimation):
```python
yield (zone_id, pixel_idx, r, g, b)  # 5-tuple
# Converted to: PixelFrame(zone_pixels={zone_id: [(r, g, b), ...]})
```

**Full Strip** (ColorCycleAnimation):
```python
yield (r, g, b)  # 3-tuple
# Converted to: FullStripFrame(color=(r, g, b))
```

---

## 11. Error Handling

### Common Scenarios

**No Animation Loaded**:
```python
await controller.show_current_frame()
# → Logs warn message, returns False
```

**Invalid Frame Data**:
```python
# Animation yields malformed tuple
frame_data = (1, 2)  # Too short!
# → _convert_to_frame() raises ValueError
# → Caught in load_animation() loop
# → Logged and animation stops
```

**Concurrent Play + Step**:
```python
# User presses SPACE while already playing
await controller.toggle_play()
# → Cancels _play_task
# → Pauses FrameManager
# → Safe and idempotent
```

---

## 12. Testing Strategy

### Unit Tests

```python
def test_frame_by_frame_controller():
    """Test frame-by-frame controller"""

    controller = FrameByFrameController(
        frame_manager=MockFrameManager(),
        animation_engine=MockAnimationEngine(),
        zone_service=MockZoneService(),
        logger=MockLogger()
    )

    # Test: Load animation
    frame_count = await controller.load_animation(AnimationID.SNAKE, speed=50)
    assert frame_count > 0

    # Test: Navigation
    await controller.next_frame()
    assert controller._current_index == 1

    await controller.previous_frame()
    assert controller._current_index == 0

    # Test: Play/Pause
    await controller.play(fps=30)
    assert controller._playing == True
    assert controller.frame_manager.is_paused == False

    await controller.pause()
    assert controller._playing == False
    assert controller.frame_manager.is_paused == True
```

### Integration Tests

```python
async def test_frame_by_frame_with_real_animation():
    """Test with real AnimationEngine and FrameManager"""

    # Setup real components
    zones = ZoneService.get_all()
    frame_manager = FrameManager(fps=60)
    animation_engine = AnimationEngine(strip, zones, frame_manager)

    controller = FrameByFrameController(
        frame_manager=frame_manager,
        animation_engine=animation_engine,
        zone_service=ZoneService(),
        logger=get_logger()
    )

    # Load SnakeAnimation
    frame_count = await controller.load_animation(
        AnimationID.SNAKE,
        ANIM_SPEED=50
    )
    print(f"Loaded {frame_count} frames")

    # Step through 5 frames
    for i in range(5):
        success = await controller.next_frame()
        assert success
        await asyncio.sleep(0.1)  # Render time

    # Verify frame manager was paused
    assert frame_manager.is_paused == True
```

---

## 13. Performance Considerations

### Frame Loading Time

**For 10-second animation @ 60 FPS**:
- Frame count: 600 frames
- Storage: ~10 KB per frame (PixelFrame: 90 pixels × 3 bytes)
- Total: ~6 MB in memory

**On Raspberry Pi 4**: Well within budget (~100 MB available for app)

### Rendering Time

**Per-frame**:
- FrameManager cycle: ~1-2 ms
- ZoneStrip.show(): ~2.7 ms
- Total: ~3.7-4.7 ms per frame @ 60 FPS

**In frame-by-frame (paused)**:
- No animation loop (paused)
- Only user frame rendering
- Should be instant (<1 frame)

### Memory Optimization (Future)

If memory becomes issue:
- Stream frames from disk instead of preload
- Compress frame data (delta encoding)
- Render on-demand instead of preload

---

## 14. Conclusion

The frame-by-frame controller provides a powerful debugging tool for animation development with minimal architectural changes. By building on top of existing `FrameManager` pause capability and `FramePlaybackController`, we create a unified interface for frame-level debugging with comprehensive logging and intuitive keyboard control.

**Key Benefits**:
- ✅ Non-intrusive (uses existing pause mechanism)
- ✅ Extensible (easily add more features)
- ✅ Observable (detailed logging of every frame)
- ✅ Intuitive (simple keyboard controls)

**Status**: Ready for implementation

