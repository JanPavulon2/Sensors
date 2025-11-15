---
Last Updated: 2025-11-15
Updated By: @architecture-expert-sonnet
Changes: Quick reference guide for implementing frame-by-frame mode
---

# Frame-By-Frame Mode - Developer Quick Reference

## 30-Second Overview

**Goal**: Step through animation frames one at a time with keyboard control (A/D/SPACE/Q)

**Location**: Create `src/controllers/led_controller/frame_by_frame_controller.py`

**How it works**:
1. Load animation frames offline (preload all frames into list)
2. Submit frames to FrameManager with DEBUG priority (highest priority)
3. Call `frame_manager.pause()` to freeze animation loop
4. Keyboard input advances/rewinds through frame list
5. SPACE toggles play/pause for auto-playback

**Why it's elegant**: Existing FrameManager priority system handles everything (no conflicts with animation)

---

## Critical Files to Read FIRST

**Must Read**:
1. `.claude/context/project/frame-by-frame-implementation.md` - Full specification
2. `.claude/context/architecture/rendering-system.md` - System architecture (Sections 3-5)
3. `.claude/context/project/frame-by-frame-summary.md` - Design decisions & templates

**Reference Code**:
- `src/animations/engine.py` - How AnimationEngine creates and manages animations
- `src/models/frame.py` - Frame model classes
- `src/engine/frame_manager.py` - FrameManager API
- `src/anim_test.py` - Example keyboard input handling

---

## Two Bugs to Fix First

### Bug #1: SnakeAnimation Zero Division

**File**: `src/animations/snake.py:63-64`

**Add validation**:
```python
self.total_pixels = sum(self.zone_pixel_counts.values())

# ADD THIS:
if self.total_pixels == 0:
    raise ValueError(
        f"SnakeAnimation requires zones with pixels. "
        f"Got {len(zones)} zones with total {self.total_pixels} pixels."
    )
```

**Time**: 2 minutes

---

### Bug #2: FramePlaybackController API Fix

**File**: `src/controllers/led_controller/frame_playback_controller.py:56`

**Change**:
```python
# OLD (wrong):
self.frame_manager.submit_zone_frame(frame.zone_id, frame.pixels)

# NEW (correct):
self.frame_manager.submit_frame(
    frame,
    priority=FramePriority.DEBUG,
    source=FrameSource.DEBUG
)
```

**Also check imports** - may need:
```python
from models.enums import FramePriority, FrameSource
```

**Time**: 3 minutes

---

## Implementation Skeleton

### Step 1: Create File

```bash
touch src/controllers/led_controller/frame_by_frame_controller.py
```

### Step 2: Copy Template

```python
"""
Frame-by-frame animation debugger.

Allows stepping through animation frames one at a time with keyboard control.
Uses FrameManager's DEBUG priority (50) to override animation rendering.
"""

import asyncio
import sys
import termios
import tty
import time
from typing import Optional, List, Dict, Any

from engine.frame_manager import FrameManager
from animations.engine import AnimationEngine
from services.zone_service import ZoneService
from models.frame import Frame, FullStripFrame, ZoneFrame, PixelFrame
from models.enums import AnimationID, FramePriority, FrameSource, LogCategory
from utils.logger import get_category_logger

log = get_category_logger(LogCategory.RENDER_ENGINE)


class FrameByFrameController:
    """
    Frame-by-frame animation debugging controller.

    Preloads animation frames and allows stepping through with keyboard control.
    Submits frames with DEBUG priority to override animation rendering.

    Keyboard Controls:
    - [A]: Previous frame
    - [D]: Next frame
    - [SPACE]: Play / Pause
    - [Q]: Quit

    Example:
        controller = FrameByFrameController(
            frame_manager=frame_manager,
            animation_engine=animation_engine,
            zone_service=zone_service,
            logger=log
        )

        await controller.load_animation(AnimationID.SNAKE, ANIM_SPEED=50)
        await controller.run_interactive()
    """

    def __init__(self,
                 frame_manager: FrameManager,
                 animation_engine: AnimationEngine,
                 zone_service: ZoneService,
                 logger):
        """Initialize controller."""
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

    async def load_animation(self,
                             animation_id: AnimationID,
                             **animation_params) -> int:
        """
        Preload animation frames into memory.

        Args:
            animation_id: Which animation to load
            **animation_params: Animation parameters (ANIM_SPEED, ANIM_SNAKE_LENGTH, etc.)

        Returns:
            Total frame count loaded
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
            frame = self._convert_to_frame(frame_data)
            self._frames.append(frame)

            if len(self._frames) % 10 == 0:
                self.logger.debug(f"Captured {len(self._frames)} frames...")

        load_duration = time.perf_counter() - self._load_start_time

        self.logger.info(
            f"Animation loaded: {len(self._frames)} frames in {load_duration:.2f}s",
            animation=animation_id.name,
            avg_frame_time_ms=f"{(load_duration / len(self._frames) * 1000):.2f}"
        )

        return len(self._frames)

    async def show_current_frame(self) -> bool:
        """
        Render current frame to hardware.

        Returns:
            True if rendered, False if no frames loaded
        """
        if not self._frames:
            self.logger.warn("No frames loaded")
            return False

        # Pause animation rendering
        self.frame_manager.pause()

        # Submit frame with DEBUG priority (highest)
        frame = self._frames[self._current_index]
        self.frame_manager.submit_frame(
            frame,
            priority=FramePriority.DEBUG,
            source=FrameSource.DEBUG
        )

        # Log frame info
        self._log_frame_info()

        return True

    async def next_frame(self) -> bool:
        """Advance to next frame (with wrapping)."""
        if not self._frames:
            self.logger.warn("No frames loaded")
            return False

        self._current_index = (self._current_index + 1) % len(self._frames)
        return await self.show_current_frame()

    async def previous_frame(self) -> bool:
        """Go back to previous frame (with wrapping)."""
        if not self._frames:
            self.logger.warn("No frames loaded")
            return False

        self._current_index = (self._current_index - 1) % len(self._frames)
        return await self.show_current_frame()

    async def play(self, fps: int = 30) -> None:
        """Start automatic playback."""
        if self._playing:
            self.logger.warn("Already playing")
            return

        if not self._frames:
            self.logger.warn("No frames loaded")
            return

        self._playing = True
        self.frame_manager.resume()

        self.logger.info(
            f"Starting playback at {fps} FPS",
            total_frames=len(self._frames)
        )

        self._play_task = asyncio.create_task(
            self._playback_loop(fps)
        )

    async def pause(self) -> None:
        """Pause automatic playback."""
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
        """Toggle play/pause."""
        if self._playing:
            await self.pause()
        else:
            await self.play()

    async def _playback_loop(self, fps: int) -> None:
        """Internal: Auto-playback loop."""
        frame_delay = 1.0 / fps

        try:
            while self._playing:
                await self.show_current_frame()
                self._current_index = (self._current_index + 1) % len(self._frames)
                await asyncio.sleep(frame_delay)
        except asyncio.CancelledError:
            self.logger.debug("Playback loop cancelled")

    def _convert_to_frame(self, frame_data) -> Frame:
        """Convert animation tuple to Frame object."""
        # Implementation here (see spec)
        pass

    def _log_frame_info(self) -> None:
        """Log detailed frame information."""
        # Implementation here (see spec)
        pass

    async def run_interactive(self) -> None:
        """Run interactive frame-by-frame session with keyboard input."""
        # Implementation here (see spec)
        pass
```

---

## Implementation Checklist

### Phase 1: Core Methods (1.5 hours)
- [ ] `__init__()` - Initialize state
- [ ] `load_animation()` - Preload frames
- [ ] `show_current_frame()` - Render + log
- [ ] `next_frame()` / `previous_frame()` - Navigation
- [ ] `play()` / `pause()` / `toggle_play()` - Playback
- [ ] `_playback_loop()` - Auto-playback loop

### Phase 2: Helpers (0.5 hours)
- [ ] `_convert_to_frame()` - Tuple → Frame conversion
- [ ] `_log_frame_info()` - Detailed logging

### Phase 3: Interactive Session (1 hour)
- [ ] `run_interactive()` - Keyboard loop
- [ ] stdin configuration (termios, tty)
- [ ] Key handling (A/D/SPACE/Q)
- [ ] Terminal restoration (finally block)

### Phase 4: Testing (1 hour)
- [ ] Unit tests (frame loading, navigation)
- [ ] Integration tests (real animations)
- [ ] Hardware tests (LED rendering)
- [ ] Manual tests (keyboard controls)

---

## API Reference Quick Lookup

### FrameManager Methods

```python
# Pause/resume
frame_manager.pause()              # Stop animation loop
frame_manager.resume()             # Resume animation loop

# Frame submission
frame_manager.submit_frame(
    frame: Frame,                  # FullStripFrame, ZoneFrame, PixelFrame
    priority: FramePriority,       # DEBUG=50 (highest)
    source: FrameSource            # DEBUG
)

# Check state
frame_manager.is_paused()          # Returns bool (if available)
```

### AnimationEngine Methods

```python
# Create animation instance
anim = animation_engine.create_animation_instance(
    animation_id: AnimationID,     # Which animation
    **params                       # Animation parameters
)

# Use as async generator
async for frame_data in anim.run():
    # frame_data is tuple:
    # - (zone_id, r, g, b)              → ZoneFrame
    # - (zone_id, pixel_idx, r, g, b)   → PixelFrame
    # - (r, g, b)                       → FullStripFrame
    pass
```

### Frame Models

```python
# Zone-based
ZoneFrame(
    zone_colors: Dict[ZoneID, (r, g, b)],
    priority: FramePriority,
    source: FrameSource,
    ttl: float = 1.0
)

# Pixel-based
PixelFrame(
    zone_pixels: Dict[ZoneID, List[(r, g, b)]],
    priority: FramePriority,
    source: FrameSource,
    ttl: float = 1.0
)

# Full strip
FullStripFrame(
    color: (r, g, b),
    priority: FramePriority,
    source: FrameSource,
    ttl: float = 1.0
)
```

### Enums

```python
# Priority levels
FramePriority.DEBUG      = 50    # Highest (use for frame-by-frame)
FramePriority.TRANSITION = 40
FramePriority.ANIMATION  = 30
FramePriority.PULSE      = 20
FramePriority.MANUAL     = 10
FramePriority.IDLE       = 0     # Lowest

# Sources
FrameSource.DEBUG       # Frame-by-frame debugging
FrameSource.ANIMATION   # Animation rendering
FrameSource.TRANSITION  # Smooth transitions
FrameSource.STATIC      # Manual color sets
```

---

## Common Patterns

### Pattern 1: Safe Task Cancellation

```python
self._play_task = asyncio.create_task(self._playback_loop(fps))

# Later, when stopping:
if self._play_task:
    self._play_task.cancel()
    try:
        await self._play_task
    except asyncio.CancelledError:
        pass  # Expected
    self._play_task = None
```

### Pattern 2: Frame Conversion with Type Checking

```python
if len(frame_data) == 3 and isinstance(frame_data[0], int):
    # (r, g, b) - Full strip
    return FullStripFrame(color=frame_data, ...)
elif len(frame_data) == 4:
    # (zone_id, r, g, b) - Zone-based
    zone_id, r, g, b = frame_data
    return ZoneFrame(zone_colors={zone_id: (r, g, b)}, ...)
elif len(frame_data) == 5:
    # (zone_id, pixel_idx, r, g, b) - Pixel-based
    zone_id, pixel_idx, r, g, b = frame_data
    return PixelFrame(zone_pixels={zone_id: pixels}, ...)
else:
    raise ValueError(f"Unknown frame format: {frame_data}")
```

### Pattern 3: Non-blocking Stdin Read

```python
import asyncio
import sys

async def read_char() -> str:
    """Read single character non-blocking."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, sys.stdin.read, 1)

# In interactive loop:
while True:
    ch = await read_char()
    if ch == 'q':
        break
    elif ch == 'a':
        await controller.previous_frame()
    elif ch == 'd':
        await controller.next_frame()
    elif ch == ' ':
        await controller.toggle_play()
```

### Pattern 4: Terminal Raw Mode

```python
import termios
import tty

stdin_fd = sys.stdin.fileno()

# Save settings
old_settings = termios.tcgetattr(stdin_fd)

try:
    # Enable raw mode (no echo, line buffering)
    tty.setcbreak(stdin_fd)

    # Read input here
    ch = sys.stdin.read(1)

finally:
    # Always restore!
    termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_settings)
```

---

## Common Pitfalls to Avoid

### ❌ Don't

1. **Forget to pause FrameManager**
   ```python
   # WRONG - animation keeps running!
   await self.show_current_frame()  # Need to pause first!
   ```

2. **Call show() without checking _frames**
   ```python
   # WRONG - will crash
   if self._frames:  # MUST CHECK!
       frame = self._frames[self._current_index]
   ```

3. **Forget terminal restoration**
   ```python
   # WRONG - terminal left in raw mode
   try:
       tty.setcbreak(stdin_fd)
       # ... interactive loop ...
   # NEED finally BLOCK!
   ```

4. **Submit frames with wrong priority**
   ```python
   # WRONG - animation overrides debug frames
   submit_frame(frame, priority=FramePriority.ANIMATION, ...)
   # CORRECT:
   submit_frame(frame, priority=FramePriority.DEBUG, ...)
   ```

5. **Block on async operations**
   ```python
   # WRONG - blocks event loop
   frame_data = animation.run().__next__()  # Blocking!
   # CORRECT:
   async for frame_data in animation.run():  # Async!
       pass
   ```

### ✅ Do

1. **Pause before showing frame**
   ```python
   self.frame_manager.pause()
   await self.show_current_frame()
   ```

2. **Always check frame list**
   ```python
   if not self._frames:
       return False
   frame = self._frames[self._current_index]
   ```

3. **Use try/finally for cleanup**
   ```python
   try:
       tty.setcbreak(stdin_fd)
       # ...
   finally:
       termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_settings)
   ```

4. **Use DEBUG priority (highest)**
   ```python
   submit_frame(frame, priority=FramePriority.DEBUG, ...)
   ```

5. **Use async/await everywhere**
   ```python
   async for frame_data in animation.run():
       # Async iteration
       pass
   ```

---

## Testing Quick Start

### Unit Test Template

```python
import pytest

def test_frame_by_frame_controller():
    """Test frame-by-frame controller."""
    from unittest.mock import Mock
    from frame_by_frame_controller import FrameByFrameController

    # Mock dependencies
    frame_manager = Mock()
    animation_engine = Mock()
    zone_service = Mock()
    logger = Mock()

    # Create controller
    controller = FrameByFrameController(
        frame_manager=frame_manager,
        animation_engine=animation_engine,
        zone_service=zone_service,
        logger=logger
    )

    # Test: No frames loaded
    assert await controller.show_current_frame() == False

    # Test: Load animation
    # (with mocked animation_engine)

    # Test: Navigation
    assert controller._current_index == 0
    await controller.next_frame()
    assert controller._current_index == 1
```

---

## Debugging Tips

**Enable debug logging**:
```python
from utils.logger import get_category_logger
from models.enums import LogCategory

log = get_category_logger(LogCategory.RENDER_ENGINE)
log.debug("Debug message")
log.info("Info message")
log.warn("Warning message")
```

**Check FrameManager state**:
```python
# Add to _log_frame_info():
self.logger.debug(
    "FrameManager state",
    is_paused=self.frame_manager._paused,
    pending_frames=len(self.frame_manager.main_queues[FramePriority.DEBUG])
)
```

**Trace frame conversion**:
```python
def _convert_to_frame(self, frame_data) -> Frame:
    self.logger.debug(f"Converting frame data: {frame_data}")
    frame = ...
    self.logger.debug(f"Converted to: {type(frame).__name__}")
    return frame
```

---

## References

**Complete Spec**: `.claude/context/project/frame-by-frame-implementation.md`

**Architecture**: `.claude/context/architecture/rendering-system.md` (Sections 3-5)

**Summary**: `.claude/context/project/frame-by-frame-summary.md`

**Code Examples**: `src/anim_test.py`, `src/animations/snake.py`

