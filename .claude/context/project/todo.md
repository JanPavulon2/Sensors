---
Last Updated: 2025-11-15
Updated By: @architecture-expert-sonnet
Changes: Complete project status, known issues, and roadmap
---

# Diuna Project - Tasks & Status

## Phase 5 - Frame-By-Frame Mode (Current)

### Active Tasks

#### 1. Fix SnakeAnimation Zero Division Error
**Status**: =4 BLOCKING
**Severity**: CRITICAL
**Affected File**: `src/animations/snake.py:63`

**Issue**:
```python
self.total_pixels = sum(self.zone_pixel_counts.values())
# If zones list is empty: total_pixels = 0
# Line 130: pos = (self.current_position - i) % self.total_pixels
# í ZeroDivisionError!
```

**Root Cause**: `anim_test.py` line 40 passes empty zones list
```python
zones = []  # ê EMPTY!
```

**Fix Options**:
1. **Defensive**: Add validation in SnakeAnimation.__init__()
2. **Preventive**: Fix anim_test.py to use real zones
3. **Both**: Do both for robustness

**Implementation Notes**:
- Add: `if self.total_pixels == 0: raise ValueError("...")`
- Test: Run anim_test.py with valid zones
- Verify: All zone animations handle empty zones gracefully

---

#### 2. Implement FrameByFrameController
**Status**: =· PENDING
**Severity**: HIGH
**Complexity**: MEDIUM (2-3 hours)
**Files to Create**: `src/controllers/led_controller/frame_by_frame_controller.py`

**Responsibilities**:
- Preload animation frames into memory
- Navigate frames (next/previous with wrapping)
- Play/pause toggle for automatic playback
- Pause FrameManager while stepping
- Log detailed frame information
- Handle keyboard input (A/D/SPACE/Q)

**Design**:
- Constructor: `__init__(frame_manager, animation_engine, zone_service, logger)`
- Methods:
  - `load_animation(animation_id, **params) í int` - Returns frame count
  - `show_current_frame() í bool` - Render + log
  - `next_frame() í bool`
  - `previous_frame() í bool`
  - `play(fps=30)`
  - `pause()`
  - `toggle_play()`
  - `run_interactive()` - Keyboard loop (A/D/SPACE/Q)

**Key Design Decision**: Use DEBUG frame priority (50) to override animation rendering while paused

**Dependencies**:
- FrameManager (already has pause/resume)
- AnimationEngine (for animation instance creation)
- BaseAnimation (for async generator)
- Frame models (ZoneFrame, PixelFrame, FullStripFrame)

**Reference**: See `.claude/context/project/frame-by-frame-implementation.md` for full spec

---

#### 3. Fix FramePlaybackController API Mismatch
**Status**: =· PENDING
**Severity**: MEDIUM
**Affected File**: `src/controllers/led_controller/frame_playback_controller.py:56`

**Issue**:
```python
self.frame_manager.submit_zone_frame(frame.zone_id, frame.pixels)
# Expected: submit_zone_frame(zone_colors: Dict[ZoneID, (r,g,b)], priority, source)
# Actual:   submit_zone_frame(zone_id, pixels)  ê API mismatch!
```

**Fix**: Update to correct FrameManager API:
```python
async def show_current(self):
    frame = self.current_frame()
    if not frame:
        log.warn("No frame to render.")
        return
    # Submit frame correctly
    self.frame_manager.submit_frame(
        frame,
        priority=FramePriority.DEBUG,
        source=FrameSource.DEBUG
    )
    log.debug(f"Rendered frame {self._current_index + 1}/{len(self._frames)}")
```

---

#### 4. Test Frame-By-Frame Implementation
**Status**: =· PENDING
**Severity**: HIGH
**Complexity**: MEDIUM (1-2 hours)

**Test Scenarios**:
- [ ] Load SnakeAnimation successfully
- [ ] Step forward (A key)
- [ ] Step backward (D key)
- [ ] Play/pause toggle (SPACE)
- [ ] Frame wrapping (previous at frame 0 í last frame)
- [ ] Frame information logging
- [ ] Performance metrics (frame load time, avg render time)

**Hardware Testing**:
- [ ] With real ZoneStrip and zones
- [ ] Verify FrameManager pause prevents animation rendering
- [ ] Verify frame data renders correctly to LEDs
- [ ] Test all animation types (zone-based, pixel-based, full-strip)

---

### Completed Tasks (Phase 5)

 **Created rendering-system.md** - Complete architectural documentation
- Explains all layers (hardware, frame, animation, controller)
- Details frame models and priority system
- Covers FrameManager, AnimationEngine, TransitionService
- Documents hardware constraints and performance
- Future enhancements identified

 **Created frame-by-frame-implementation.md** - Full implementation spec
- Current state analysis
- FrameByFrameController design (methods, signatures)
- Integration points
- Bug fixes required
- Logging design
- Testing strategy

---

## Phase 4 - Core Rendering System (Completed )

### Completed
 FrameManager implementation with priority queues
 Frame models (ZoneFrame, PixelFrame, FullStripFrame, PreviewFrame)
 Priority-based rendering (IDLE < MANUAL < PULSE < ANIMATION < TRANSITION < DEBUG)
 TTL-based frame expiration
 Atomic rendering (single show() per cycle)
 AnimationEngine lifecycle management
 Transition service with crossfade support
 Animation pause/resume capability
 Zone and pixel buffer management

### Known Issues (Unfixed)

**1. Animation Power-Off Flickering**
- Severity: MEDIUM
- When: Power off during animation
- Effect: Last animation pixels briefly remain lit before fading
- Status: Under investigation (see `remaining-animation-issues.md`)

**2. Animation Cycling Ghost Pixels**
- Severity: MEDIUM
- When: Switching between animations
- Effect: Previous animation pixels don't fully clear before new animation
- Status: Under investigation

**3. Stale Pixels After Mode Switch**
- Severity: MEDIUM
- When: Switching STATIC î ANIMATION
- Effect: Some pixels stay lit momentarily
- Hypothesis: Animation frames still submitting during transition

---

## Phase 3 - Animation System (Completed )

### Completed
 BreatheAnimation (zone-based, individual colors)
 ColorFadeAnimation (zone-based, fade through hues)
 ColorCycleAnimation (full-strip, uniform color cycling)
 SnakeAnimation (pixel-based, single/multi-pixel snake)
 ColorSnakeAnimation (pixel-based, colored snake)
 Animation parameter updates (live adjustments)
 Animation switching with smooth transitions

### Not Completed
- MatrixAnimation (disabled, complex rendering)

---

## Phase 2 - Hardware Abstraction (Completed )

### Completed
 ZoneStrip - Main LED strip control (90 pixels, 6-8 zones)
 PreviewPanel - 8-LED feedback panel
 Zone mapping (FLOOR, LAMP, TOP, RIGHT, BOTTOM, LEFT, BACK)
 Pixel and zone color setting
 Hardware state capture (get_frame())

---

## Phase 1 - Infrastructure (Completed )

### Completed
 GPIO manager (pigpio integration)
 Event bus (async event publishing)
 Configuration system (YAML zones and parameters)
 State persistence (JSON)
 Logging system (categorized log output)
 Dependency injection
 Async architecture (asyncio)

---

## Backlog - Priority Issues

### Critical (Must Fix)
1. SnakeAnimation zero division í Blocks frame-by-frame testing
2. Animation ghost pixels í Affects user experience
3. Stale pixels on mode switch í Affects user experience

### High (Should Fix Soon)
1. Frame-by-frame mode í Enables debugging
2. Animation cycling artifacts í Investigate root cause
3. MatrixAnimation re-enable í Feature parity

### Medium (Nice to Have)
1. FPS counter í Performance monitoring
2. Memory profiler í Resource usage tracking
3. Animation recording í Capture and playback
4. WebSocket streaming í Remote viewing

### Low (Future Enhancement)
1. Game mode í Interactive snake game
2. Music reactive mode í Audio-synchronized effects
3. Custom animation upload í User-defined effects
4. LED matrix support í New hardware capability

---

## Bugs & Issues Tracker

### Bug #1: SnakeAnimation Zero Division
**Status**: =4 OPEN
**Priority**: CRITICAL
**Component**: Animation
**File**: `src/animations/snake.py:130`
**Reported**: 2025-11-15
**Details**:
- Crash: `ZeroDivisionError: integer modulo by zero`
- Cause: `self.total_pixels = 0` when zones list is empty
- Trigger: Run anim_test.py with default empty zones
- Fix: Add validation in __init__()

**Workaround**: None (blocks execution)

---

### Bug #2: Animation Ghost Pixels
**Status**: =· INVESTIGATING
**Priority**: HIGH
**Component**: Animation Lifecycle
**File**: `src/animations/engine.py`
**Reported**: 2025-11-08
**Details**:
- When: Switching between animations
- Effect: Previous animation pixels remain lit briefly
- Hypothesis 1: Animation frames still submitted during crossfade
- Hypothesis 2: FrameManager not clearing old ANIMATION frames
- Hypothesis 3: Buffer accumulation issue

**Investigation Needed**:
- Add logging to AnimationEngine._run_loop()
- Track frame submission timing
- Monitor FrameManager queue state during transition
- Verify task cancellation is complete

**Related Issue**: `remaining-animation-issues.md`

---

### Bug #3: Stale Pixels on Power Off
**Status**: =· INVESTIGATING
**Priority**: MEDIUM
**Component**: Transition Service
**File**: `src/services/transition_service.py`
**Reported**: 2025-11-08
**Details**:
- When: Power off during animation
- Effect: Pixels don't fully fade to black
- Sequence:
  1. User presses power button
  2. AnimationEngine.stop() is called
  3. TransitionService.fade_out() interpolates
  4. Some pixels remain lit briefly

**Hypothesis**:
- Animation frames still in FrameManager queue
- TTL system not expiring fast enough
- Current strip state capture incomplete

**Investigation Needed**:
- Verify animation task fully stops before fade_out()
- Check FrameManager frame selection during transition
- Monitor queue state
- Consider explicit frame clearing

**Related Issue**: `remaining-animation-issues.md`

---

### Bug #4: FramePlaybackController API Mismatch
**Status**: =· NEEDS FIX
**Priority**: MEDIUM
**Component**: Controller
**File**: `src/controllers/led_controller/frame_playback_controller.py:56`
**Details**:
- Method calls: `submit_zone_frame(zone_id, pixels)`
- Expected API: `submit_zone_frame(zone_colors: Dict, priority, source)`
- Result: Frame submission fails silently or crashes

**Fix**: Update to correct API (see above)

---

## Documentation Status

### Recently Created =›
-  `architecture/rendering-system.md` - Complete rendering system architecture
-  `project/frame-by-frame-implementation.md` - Frame-by-frame mode specification

### Needs Update =À
- [ ] `domain/animations.md` - Add new animation types (if any)
- [ ] `domain/zones.md` - Verify zone configuration current
- [ ] `technical/hardware.md` - Update thermal notes
- [ ] `development/coding-standards.md` - Add frame-by-frame patterns

### Needs Creation =›
- [ ] `project/changelog.md` - Version history and release notes
- [ ] `project/debugging.md` - Debug mode features and how to use them
- [ ] `development/testing.md` - Testing strategy and examples
- [ ] `architecture/patterns.md` - Design patterns used in codebase

---

## Performance Metrics

### Current (Measured 2025-11-15)

**Rendering**:
- Target FPS: 60 Hz
- Frame time: 16.6 ms per frame
- Hardware limit: 2.75 ms (DMA transfer only)
- Python overhead: ~13 ms
- Headroom: 40% (for system tasks)

**Memory**:
- Total footprint: ~500 KB
- FrameManager queues: ~50 KB
- Animation instances: ~50 KB per active
- Frame buffers: ~27 KB (10 frames ◊ 90 pixels)

**Hardware**:
- Main strip: 90 pixels (WS2811, 12V)
- Preview panel: 8 pixels (WS2812B, 5V)
- Max power: 65W (full white)
- Thermal: Unknown (needs measurement)

---

## Dependencies & Requirements

### Hardware
- Raspberry Pi 4 (2GB+ RAM)
- WS2811 LED strip (90 pixels)
- WS2812B preview panel (8 pixels)
- 12V and 5V power supplies
- GPIO headers for control

### Python Packages
- asyncio (stdlib)
- rpi_ws281x (LED control)
- pigpio (GPIO daemon)
- pyyaml (config)
- python-evdev (optional, keyboard input)

### System
- Raspberry Pi OS (Bullseye or later)
- Python 3.8+
- GPIO access (requires root or gpio group)

---

## Next Steps (Recommended)

### Immediate (This Session)
1.  Document rendering system architecture í DONE
2.  Create frame-by-frame spec í DONE
3. í Implement FrameByFrameController
4. í Fix SnakeAnimation zero division
5. í Test frame-by-frame with real zones

### Short Term (Next Week)
1. Complete frame-by-frame testing
2. Investigate animation ghost pixels
3. Fix stale pixels on power off
4. Update all remaining documentation

### Medium Term (Next Month)
1. Re-enable MatrixAnimation
2. Add FPS counter
3. Add memory profiler
4. Start game mode design

### Long Term (Future)
1. WebSocket streaming
2. Animation recording/playback
3. Music reactive mode
4. Custom animation support

---

## How to Use This File

**Finding Issues**:
- Use Ctrl+F to search for component name or bug ID
- Check Status column for =4 OPEN / =· INVESTIGATING /  COMPLETED

**Adding New Tasks**:
1. Copy template from relevant section
2. Add status emoji: =4 OPEN, =· IN_PROGRESS,  COMPLETED
3. Include severity/complexity where relevant
4. Link to related files or issues

**Updating Progress**:
- Update status emoji and timestamp
- Add notes in "Details" section
- Move completed items down to "Completed" subsection

---

## Reference Links

**Architecture Files**:
- [Rendering System](architecture/rendering-system.md) - Complete system architecture
- [Animation System](domain/animations.md) - Animation types and design
- [Frame-By-Frame Mode](project/frame-by-frame-implementation.md) - Feature specification

**Issue Tracking**:
- [Remaining Animation Issues](remaining-animation-issues.md) - Investigation notes
- [Parallel Rendering Issue](parallel-rendering-issue.md) - Phase 4 resolution

**Code References**:
- `src/engine/frame_manager.py` - Core rendering system
- `src/animations/engine.py` - Animation lifecycle
- `src/services/transition_service.py` - Smooth transitions
- `src/animations/base.py` - Animation base class

