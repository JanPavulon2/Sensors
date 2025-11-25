---
Last Updated: 2025-11-25
Updated By: Architecture Analysis
Changes: Optimization opportunities and implementation guidelines
---

# Frame Rendering Optimization Guide

## 1. Current Implementation Analysis

### Performance Characteristics

**Current Behavior**:
```
60 FPS rendering (target)
16.67ms per frame
Hardware DMA: 2.7ms per transfer (all 90 pixels)
CPU idle: 13.97ms per cycle (83% idle)
```

**Memory Usage**:
```
Per priority queue: 2 frames max (deque maxlen=2)
Per frame: ~4-6 KB (Zone dict + Color objects + metadata)
Total: ~6 queues × 2 frames × 5 KB = 60 KB
```

**Static-Only Mode** (most common):
```
Scenario: No animations running, just static zones

Frame submission frequency: ~0 per second (only on user input)
Rendering frequency: 60 per second (always)
Hardware updates: 60 per second (SAME pixels each time)

Wasted DMA transfers: 60 × 2.7ms = 162ms per second
                      → 16% of total time sending identical data!
```

---

## 2. Optimization #1: Frame Change Detection (EASY - PRIORITY)

### Problem

In static-only mode, the same pixel data is sent to hardware 60 times per second, even though it hasn't changed.

### Solution

**Add frame hash comparison before rendering**:

```python
class FrameManager:
    def __init__(self, fps: int = 60):
        # ... existing code ...
        self.last_rendered_frame: Optional[MainStripFrame] = None
        self.last_rendered_frame_hash: Optional[str] = None

    async def _render_loop(self) -> None:
        """Main render loop with frame change detection."""
        frame_delay = 1.0 / self.fps

        while self.running:
            # Select frame
            main_frame = await self._select_main_frame_by_priority()
            preview_frame = await self._select_preview_frame_by_priority()

            # NEW: Check if frame actually changed
            if main_frame:
                frame_hash = self._compute_frame_hash(main_frame)

                if frame_hash != self.last_rendered_frame_hash:
                    # Frame changed → render to hardware
                    self._render_atomic(main_frame, preview_frame)
                    self.last_rendered_frame_hash = frame_hash
                    self.frames_rendered += 1
                else:
                    # Frame unchanged → skip hardware update
                    # (LEDs already have correct pixels)
                    pass

            await asyncio.sleep(frame_delay)

    def _compute_frame_hash(self, frame: MainStripFrame) -> str:
        """Compute hash of frame content (not metadata)."""
        # Hash only the pixel data, ignore timestamp
        if isinstance(frame, PixelFrame):
            # Hash zone_pixels dict
            pixel_tuples = tuple(
                (zone_id, tuple(color.to_rgb() for color in pixels))
                for zone_id, pixels in sorted(frame.zone_pixels.items())
            )
            return hash(pixel_tuples)

        elif isinstance(frame, ZoneFrame):
            # Hash zone_colors dict
            color_tuples = tuple(
                (zone_id, color.to_rgb())
                for zone_id, color in sorted(frame.zone_colors.items())
            )
            return hash(color_tuples)

        elif isinstance(frame, FullStripFrame):
            # Hash single color
            return hash(frame.color)

        return str(hash(frame))
```

**Location to add**: `src/engine/frame_manager.py` - in `__init__` and `_render_loop`

### Benefits

- **95% reduction** in hardware updates during static-only mode
- **Eliminates unnecessary DMA transfers**
- **Same visual output** (no change to user experience)
- **Minimal CPU overhead** (hash comparison ~microseconds)

### Drawbacks

- Slight complexity in frame comparison
- Edge case: If hash collides, frame won't update (rare but possible)

### Implementation Notes

- Use Python's `hash()` function (built-in, fast)
- Only compare pixel data, ignore timestamp
- Cache hash in frame object if called multiple times per cycle

### Risk Assessment

**Low Risk**:
- Rendering still happens at 60 FPS (timing unchanged)
- Only skips hardware DMA, not frame selection logic
- Easy to revert if issues found

---

## 3. Optimization #2: Longer TTL for Slow Animations (MEDIUM)

### Problem

All animations use fixed ttl=0.1s, but some animations are slower:

```
Fast animations (Snake, ColorSnake): 30+ FPS internal update
  → 0.1s TTL = 3+ frames in queue → OK

Slow animations (Breathe): 1-2 Hz internal update
  → 0.1s TTL = 0.1-0.2 frames in queue → Risky
  → If system busy, frame expires before next animation frame submitted
```

### Solution

**Make TTL configurable per animation type**:

```python
class BaseAnimation:
    """Base class for all animations."""

    def __init__(self):
        self.animation_speed = 1.0  # 1.0 = normal speed
        self.frame_ttl = self._calculate_ttl()  # NEW

    def _calculate_ttl(self) -> float:
        """Calculate appropriate TTL based on animation speed."""
        # TTL should be longer than frame interval
        frame_interval = 0.016  # 60 FPS = 16.67ms between renders

        # For safety, use 2-3× the frame interval
        # So even if frames are submitted slower, TTL doesn't expire
        return max(0.1, 3.0 * frame_interval)  # Minimum 100ms

    async def _submit_frame(self, frame: PixelFrame) -> None:
        """Submit frame with animation-specific TTL."""
        frame.ttl = self.frame_ttl  # ← Use animation's TTL
        await self.frame_manager.submit_pixel_frame(frame)


class SnakeAnimation(BaseAnimation):
    """Fast animation with many FPS."""
    def _calculate_ttl(self) -> float:
        return 0.1  # 100ms (fast, short TTL ok)


class BreatheAnimation(BaseAnimation):
    """Slow animation (1-2 Hz)."""
    def _calculate_ttl(self) -> float:
        return 1.0  # 1000ms (slow, need longer TTL)


class ColorCycleAnimation(BaseAnimation):
    """Medium speed animation."""
    def _calculate_ttl(self) -> float:
        return 0.5  # 500ms (medium)
```

**Location to modify**: `src/animations/engine.py` and per-animation classes

### Benefits

- Slow animations less likely to expire unexpectedly
- Automatic adapting to animation speed
- Better handling of system load spikes

### Drawbacks

- More complex frame submission logic
- Need to tune TTL per animation type
- Risk of frames staying too long if animation dies

### Implementation Notes

- Start with conservative estimates (longer TTL is safer)
- Monitor frame expiration metrics
- Test with slow animations + other system load

### Risk Assessment

**Low-Medium Risk**:
- If TTL too long, frame stays visible after animation stops (brief flicker)
- If TTL too short, same as current (expiration issues)
- Easy to adjust values

---

## 4. Optimization #3: Zone Masking (HARD)

### Problem

When a frame doesn't specify a zone, it defaults to black:

```python
# PULSE frame only updates LAMP:
frame.zone_colors = {ZoneID.LAMP: Color.white()}

# But rendering fills ALL zones:
full_frame = strip.build_frame_from_zones(frame.zone_colors)
# Missing zones default to black!

Result: When PULSE replaces ANIMATION:
  FLOOR → black (not in PULSE frame)
  LAMP → white (in PULSE frame)
  LEFT → black (not in PULSE frame)
```

### Solution

**Add zone masking to frame types**:

```python
@dataclass
class ZoneFrame(BaseFrame):
    """Per-zone colors with optional masking."""
    zone_colors: Dict[ZoneID, Color] = field(default_factory=dict)

    # NEW: Only update these zones, preserve others
    zone_mask: Optional[Set[ZoneID]] = None

    def should_update_zone(self, zone_id: ZoneID) -> bool:
        """Check if this frame should update the given zone."""
        if self.zone_mask is None:
            # No mask = update all zones specified
            return zone_id in self.zone_colors
        else:
            # With mask = only update zones in mask
            return zone_id in self.zone_mask


@dataclass
class PixelFrame(BaseFrame):
    """Per-pixel colors with optional masking."""
    zone_pixels: Dict[ZoneID, List[Color]] = field(default_factory=dict)

    # NEW: Only update these zones
    zone_mask: Optional[Set[ZoneID]] = None

    def should_update_zone(self, zone_id: ZoneID) -> bool:
        if self.zone_mask is None:
            return zone_id in self.zone_pixels
        else:
            return zone_id in self.zone_mask


# RENDERING WITH MASKING:

def _render_zone_frame(self, frame: ZoneFrame, strip: ZoneStrip) -> None:
    """Render ZoneFrame with zone masking."""

    full_frame = {}

    for zone_id in strip.mapper.all_zone_ids():
        if frame.should_update_zone(zone_id):
            # Update this zone from frame
            if zone_id in frame.zone_colors:
                full_frame[zone_id] = frame.zone_colors[zone_id]
        else:
            # Preserve previous zone state
            previous_pixels = strip.get_current_zone_pixels(zone_id)
            if previous_pixels:
                full_frame[zone_id] = previous_pixels
            else:
                full_frame[zone_id] = Color.black()

    strip.show_full_pixel_frame(full_frame)


# USAGE:

# PULSE frame: only updates LAMP, preserves FLOOR
pulse_frame = ZoneFrame(
    zone_colors={ZoneID.LAMP: Color.white().with_brightness(0.8)},
    zone_mask={ZoneID.LAMP},  # NEW: only mask this zone
    priority=FramePriority.PULSE,
    source=FrameSource.PULSE,
    ttl=0.1
)

# ANIMATION frame: updates all specified zones
anim_frame = PixelFrame(
    zone_pixels={ZoneID.FLOOR: [animated], ZoneID.LEFT: [static]},
    zone_mask=None,  # No mask = update all zones in zone_pixels
    priority=FramePriority.ANIMATION,
    source=FrameSource.ANIMATION,
    ttl=0.1
)
```

**Locations to modify**:
- `src/models/frame.py` - Add zone_mask field
- `src/engine/frame_manager.py` - Rendering methods
- `src/zone_layer/zone_strip.py` - Add get_current_zone_pixels()

### Benefits

- Zones not explicitly controlled preserve previous state
- No unexpected "zones turn black" when frame sources change
- More intuitive behavior for multi-source rendering

### Drawbacks

- More complex rendering logic
- Need to track previous zone pixels
- Memory overhead for storing current pixels

### Implementation Notes

- Track "current pixels" in ZoneStrip for each zone
- Update tracking after each render
- Default to black if no previous state available
- This is what actually should happen based on user expectations

### Risk Assessment

**Medium-High Risk**:
- Complex state tracking
- Risk of stale pixel data (showing old zone color)
- Need thorough testing

---

## 5. Optimization #4: Priority Ranges (MEDIUM)

### Problem

Fixed priority per source limits flexibility:

```
Current: ANIMATION = 30 (always)
         PULSE = 20 (always)

Issue: Sometimes you want PULSE to override ANIMATION
       (e.g., user presses "brightness pulse" button)
       But pri=20 < pri=30, so animation always wins
```

### Solution

**Use priority ranges instead of fixed values**:

```python
class FramePriority(IntEnum):
    """Priority ranges for frame sources."""

    # Range: 0-10 (IDLE/MANUAL)
    IDLE = 0
    MANUAL = 10

    # Range: 15-25 (PULSE - can vary by intensity)
    PULSE_LOW = 15
    PULSE_MEDIUM = 20
    PULSE_HIGH = 25

    # Range: 30-40 (ANIMATION - can vary by type)
    ANIMATION_SLOW = 30
    ANIMATION_NORMAL = 35
    ANIMATION_FAST = 40

    # Range: 45-49 (TRANSITION)
    TRANSITION_LOW = 45
    TRANSITION_HIGH = 49

    # Range: 50+ (DEBUG)
    DEBUG = 50


# USAGE:

# Fast animation gets higher priority
snake_frame = PixelFrame(
    ...
    priority=FramePriority.ANIMATION_FAST,  # pri=40
)

# Slow animation gets lower priority
breathe_frame = PixelFrame(
    ...
    priority=FramePriority.ANIMATION_SLOW,  # pri=30
)

# User enables high-intensity pulse (overrides slow animation)
pulse_frame = ZoneFrame(
    ...
    priority=FramePriority.PULSE_HIGH,  # pri=25
)
```

### Benefits

- Fine-grained priority control
- Can let user choices override slow background animations
- Smooth transitions between priority levels

### Drawbacks

- More priority values to manage
- Risk of priority conflicts
- More complex decision-making

### Implementation Notes

- Keep ranges separated (5-10 points each)
- Document priority decisions in comments
- Test interaction between priority ranges

### Risk Assessment

**Low-Medium Risk**:
- Only affects priority selection logic
- Easy to debug and adjust
- Can be implemented incrementally

---

## 6. Optimization #5: Frame Deduplication (EASY)

### Problem

Identical frames submitted multiple times in queue:

```python
# Animation yields same pixels for 100ms (no change)
# Submits frame every 16.67ms
# Result: 6 identical frames in queue

queue = [Frame_A, Frame_A, Frame_A, Frame_A, Frame_A, Frame_A]
# Only first rendered, others waste space
```

### Solution

**Compare with queue tail before appending**:

```python
async def submit_pixel_frame(self, frame: PixelFrame) -> None:
    """Submit frame, deduplicating identical frames."""
    async with self._lock:
        queue = self.main_queues[frame.priority.value]

        # NEW: Check if same as last frame in queue
        if queue:
            last_frame = queue[-1]
            if self._frames_equal(frame, last_frame):
                # Identical frame, skip submission
                return

        # Different frame, append
        queue.append(frame)

def _frames_equal(self, f1: MainStripFrame, f2: MainStripFrame) -> bool:
    """Check if two frames have identical pixel data."""
    if type(f1) != type(f2):
        return False

    if isinstance(f1, PixelFrame) and isinstance(f2, PixelFrame):
        return f1.zone_pixels == f2.zone_pixels

    elif isinstance(f1, ZoneFrame) and isinstance(f2, ZoneFrame):
        return f1.zone_colors == f2.zone_colors

    elif isinstance(f1, FullStripFrame) and isinstance(f2, FullStripFrame):
        return f1.color == f2.color

    return False
```

**Location**: `src/engine/frame_manager.py` - submit_pixel_frame(), submit_zone_frame(), etc.

### Benefits

- Cleaner queue management
- Slightly faster queue operations (fewer items)
- Preparation for Optimization #1 (frame change detection)

### Drawbacks

- Tiny CPU overhead for equality check
- Equality comparison might be expensive for large pixel frames

### Implementation Notes

- Use `==` operator for dict/list comparison (Python built-in)
- Could optimize with frame hashing instead of equality
- Safe to implement without breaking changes

### Risk Assessment

**Very Low Risk**:
- Non-invasive change
- Only affects queue management
- Easy to test and revert

---

## 7. Implementation Roadmap

### Phase 1: Immediate (Easy, High Value)

**Optimization #1: Frame Change Detection**
- Reduces DMA overhead by ~95% in static mode
- Implementation: 20-30 lines of code
- Testing: Simple (compare hash before/after)
- **RECOMMENDED: Do this first**

```
Effort: 2 hours
Risk: Low
Value: High
Expected result: ~95% less GPIO in static mode
```

**Optimization #5: Frame Deduplication**
- Cleans up queue management
- Implementation: 10-15 lines of code
- Pairs well with Opt #1
- **RECOMMENDED: Do together with #1**

```
Effort: 1 hour
Risk: Very Low
Value: Medium (cleanup, not perf)
Expected result: Cleaner queue behavior
```

---

### Phase 2: Secondary (Medium Effort, Medium Value)

**Optimization #3: TTL Customization**
- Improves animation reliability
- Implementation: 15-20 lines of code
- Testing: Requires testing with slow animations
- **RECOMMENDED: Do if animation stability issues found**

```
Effort: 3 hours
Risk: Low
Value: Medium
Expected result: Better handling of slow animations
```

---

### Phase 3: Advanced (High Effort, Situational Value)

**Optimization #2: Zone Masking**
- Fixes "zones turn black" issue
- Implementation: 50-100 lines of code
- Testing: Complex (state tracking)
- **OPTIONAL: Do if users report visual issues**

```
Effort: 6-8 hours
Risk: Medium
Value: Medium (UX improvement)
Expected result: Zones preserve state better
```

**Optimization #4: Priority Ranges**
- Provides fine-grained control
- Implementation: 30-50 lines of code
- Testing: Priority conflict testing
- **OPTIONAL: Do if need more priority flexibility**

```
Effort: 4-5 hours
Risk: Low-Medium
Value: Low (niche use case)
Expected result: More priority combinations
```

---

## 8. Performance Impact Estimates

### Optimization #1: Frame Change Detection

**Static-Only Mode** (most common):
```
Current:  60 frames/sec × 2.7ms DMA = 162ms/sec (16.2% CPU)
Optimized: 1 frame submission × 2.7ms DMA = 2.7ms/sec (0.27% CPU)
                                  (only on user input)

Improvement: 98% reduction in DMA overhead
```

**Animation Mode**:
```
Current: 60 frames/sec × 2.7ms DMA = 162ms/sec
Optimized: 60 frames/sec × hash(compare 1-2µs) ≈ 10µs/sec (0.001% CPU)
           Only 1st frame rendered (animation rarely stable)

Improvement: 99% reduction if animation very stable
```

### Optimization #2: Zone Masking

**Reduction in unexpected visual changes**:
```
Current: When ANIMATION → PULSE transition, zones go black
Optimized: Zones preserve previous state (no black flash)

Impact: User experience improvement, no measured perf change
```

### Overall System

**Before optimizations**:
```
CPU time: ~1ms per frame (hash, selection, rendering)
GPIO time: 2.7ms per frame (DMA)
Total: 3.7ms per frame @ 60 FPS
Idle: 12.97ms per frame (78% idle)
```

**After Optimization #1 + #5** (recommended):
```
Static mode:
  CPU time: ~1ms per frame (hash, selection)
  GPIO time: 0ms average (only on frame change)
  Total: ~1ms per frame
  Idle: 15.67ms per frame (94% idle)

Animation mode:
  CPU time: ~1ms per frame (hash, selection)
  GPIO time: 2.7ms per frame (DMA)
  Total: 3.7ms per frame (same as current)
  Idle: 12.97ms per frame (78% idle)
```

---

## 9. Testing Optimization Implementations

### Test Plan for Frame Change Detection (#1)

```python
# Test 1: Static frame repeated
frame_1 = ZoneFrame(zone_colors={FLOOR: Color.red()})
frame_2 = ZoneFrame(zone_colors={FLOOR: Color.red()})  # Identical

hash_1 = fm._compute_frame_hash(frame_1)
hash_2 = fm._compute_frame_hash(frame_2)
assert hash_1 == hash_2  # Should match

# Test 2: Different frame
frame_3 = ZoneFrame(zone_colors={FLOOR: Color.blue()})  # Different
hash_3 = fm._compute_frame_hash(frame_3)
assert hash_3 != hash_1  # Should differ

# Test 3: Different zone order (should still match)
frame_4 = ZoneFrame(zone_colors={RIGHT: Color.green(), FLOOR: Color.red()})
frame_5 = ZoneFrame(zone_colors={FLOOR: Color.red(), RIGHT: Color.green()})
hash_4 = fm._compute_frame_hash(frame_4)
hash_5 = fm._compute_frame_hash(frame_5)
assert hash_4 == hash_5  # Dict order doesn't matter

# Test 4: Metadata ignored
frame_6a = PixelFrame(..., timestamp=1.0, ttl=0.1)
frame_6b = PixelFrame(..., timestamp=2.0, ttl=0.5)  # Different metadata
hash_6a = fm._compute_frame_hash(frame_6a)
hash_6b = fm._compute_frame_hash(frame_6b)
assert hash_6a == hash_6b  # Metadata ignored

# Integration test: Static animation
animate_for_1_second_without_change()
assert fm.frames_rendered == 1  # Only 1 DMA even though 60 FPS
assert fm.hash_skips == 59  # 59 hash matches
```

### Test Plan for Zone Masking (#3)

```python
# Test 1: PULSE only updates LAMP
pulse_frame = ZoneFrame(
    zone_colors={LAMP: Color.white()},
    zone_mask={LAMP}
)

# Simulate: FLOOR was red from previous animation
strip.set_current_zone_pixels({FLOOR: [Color.red()], ...})

render_zone_frame(pulse_frame, strip)

# Check: FLOOR still red, LAMP now white
assert get_zone_color(FLOOR) == Color.red()  # Preserved!
assert get_zone_color(LAMP) == Color.white()

# Test 2: No mask means update all specified zones
anim_frame = PixelFrame(
    zone_pixels={FLOOR: [animated], LAMP: [white]},
    zone_mask=None  # No mask
)

render_pixel_frame(anim_frame, strip)

# Check: FLOOR and LAMP updated, LEFT unchanged
assert get_zone_color(FLOOR) == Color.animated
assert get_zone_color(LAMP) == Color.white
# LEFT behavior: if not in zone_pixels, defaults to black
```

---

## 10. Decision Framework: Which Optimizations to Implement?

### Current Status (Phase 6 Complete)

✅ **No blocking performance issues**
- 60 FPS achieved consistently
- Hardware is limiting factor, not CPU
- No thermal issues reported

### Implement #1 (Frame Change Detection) If:

- [ ] Users report unnecessary GPIO activity (power draw)
- [ ] System needs to run 24/7 on battery or limited power
- [ ] Monitoring shows >15% CPU devoted to rendering in static mode
- [ ] Performance baseline required for future optimization

✅ **RECOMMENDATION: Good practice, implement proactively**

### Implement #3 (Zone Masking) If:

- [ ] Users report visual glitches when animation mode ends
- [ ] "Zones turning black" issues confirmed from users
- [ ] A/B testing shows feature improves user experience

### Implement #2,#4,#5 If:

- [ ] Specific use case requires the feature
- [ ] User requests for fine-grained control
- [ ] Performance analysis identifies bottleneck

### AVOID Unless Necessary:

- Optimization #2 (Priority Ranges) - adds complexity without clear benefit
- Optimization #4 (Frame Deduplication) - marginal benefit, small overhead
- Optimization #3 (Zone Masking) - only if UX issue confirmed

---

## Summary

| Optimization | Effort | Risk | Value | Status |
|--------------|--------|------|-------|--------|
| **#1: Frame Change Detection** | 2h | Low | High | ✅ **DO NOW** |
| **#5: Frame Dedup** | 1h | V.Low | Medium | ✅ **DO NOW** |
| **#3: TTL Customization** | 3h | Low | Medium | ⚠️ If needed |
| **#2: Zone Masking** | 6h | Medium | Medium | ⚠️ If UX issue |
| **#4: Priority Ranges** | 4h | Low-Med | Low | ❌ Skip |

**Recommended Action**: Implement #1 and #5 together as a quick win.
Expected result: 95% reduction in GPIO overhead for static-only mode, cleaner code.