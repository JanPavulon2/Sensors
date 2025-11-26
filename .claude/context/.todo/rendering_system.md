---
Last Updated: 2025-11-25
Title: Rendering System Issues and Tasks
Category: Rendering System
---

# Rendering System TODO

## BLOCKING Issues

### SnakeAnimation Zero Division
**Status**: 🔴 BLOCKING
**File**: `src/animations/snake.py:63`
**Severity**: Critical
**Impact**: Application crashes when starting snake animation with empty zones

**Problem**:
```python
# Line 63
self.total_pixels = sum(...)  # Could be 0
self.snake_position = random.randint(0, self.total_pixels - 1)  # Division by zero!
```

**Solution**:
Add validation in `__init__()`:
```python
if self.total_pixels == 0:
    raise ValueError("SnakeAnimation requires at least one enabled zone with pixels")
```

**Fix Location**: `src/animations/snake.py:__init__()` around line 50-65
**Estimated Time**: 5 minutes

---

## MEDIUM Priority

### Ghost Pixels During Animation Transitions
**Status**: 🟡 INVESTIGATING
**File**: `src/engine/frame_manager.py` + `src/animations/engine.py`
**Severity**: Medium (visual glitch)
**Impact**: When switching between animations, previous animation pixels briefly remain

**Problem**:
- Animation A running (frames in queue)
- User switches to Animation B
- Animation A's last frame still in queue during first Animation B frames
- Brief moment: both animations visible

**Hypothesis**:
- TTL allows expired frames to remain 100ms
- During crossfade transition, multiple frame sources competing
- Need more aggressive frame culling during animation switch

**Potential Solutions**:
1. Clear frame queue when switching animations
2. Flush on-demand (not just TTL-based)
3. Shorter TTL for animation frames (50ms instead of 100ms)
4. Priority adjustment for crossfade transitions

**Related Code**:
- `AnimationEngine._run_loop()` (engine.py:250)
- `AnimationEngine.stop()` (engine.py:180)
- `FrameManager._select_frame()` (frame_manager.py:250)

**Estimated Time**: 2-4 hours (needs investigation + testing)

---

### Animation Power-Off Flickering
**Status**: 🟡 KNOWN ISSUE
**Severity**: Medium (visual glitch)
**Impact**: When power off during animation, animation pixels briefly visible before fade

**Problem**:
- Animation running
- Power button pressed
- TransitionService starts fade-out
- But animation frames still being generated and queued
- Briefly see animation flicker before fade completes

**Solution**:
- Stop animation immediately on power-off
- Clear frame queue before fade starts
- Or: change animation priority to lower than TRANSITION

**Related Code**:
- `PowerToggleController` (power_toggle_controller.py)
- `AnimationEngine.stop()` (engine.py:180)

**Estimated Time**: 1-2 hours

---

### Preview Panel Integration
**Status**: 🟡 NOT IMPLEMENTED
**File**: `src/controllers/preview_panel_controller.py`
**Severity**: Medium (feature incomplete)
**Impact**: No animation preview on 8-LED panel, parameter visualization missing

**Problem**:
- PreviewPanelController exists (200+ lines)
- But disabled in `main_asyncio.py:237-259`
- Not integrated with FrameManager
- Needs `PreviewService` to work

**Solution**:
Create `PreviewService`:
```python
class PreviewService:
    async def start_preview(self, animation_id, **params):
        gen = create_animation(animation_id, zone=PREVIEW, **params)
        async for frame_data in gen:
            frame = PreviewFrame(pixels=[...])
            await frame_manager.submit_preview_frame(frame)
```

Then enable PreviewPanelController in main_asyncio.

**Related Code**:
- `PreviewPanelController` (preview_panel_controller.py)
- `AnimationEngine` (engine.py)
- `FrameManager.submit_preview_frame()` (frame_manager.py)

**Estimated Time**: 3-4 hours (implementation + testing)

---

## LOW Priority

### PixelFrame.clear_other_zones Flag Not Implemented
**Status**: 🟢 LOW PRIORITY
**File**: `src/engine/frame_manager.py:433-460`
**Severity**: Low (feature incomplete)
**Impact**: Advanced frame control not available

**Problem**:
- PixelFrame has `clear_other_zones: bool` field (line 65 model)
- FrameManager doesn't check this flag during rendering
- Flag should zero out zones not in `frame.zone_pixels`

**Solution**:
In `_render_pixel_frame()`, check flag:
```python
if frame.clear_other_zones:
    # Zero all pixels not in frame.zone_pixels
    for zone in all_zones:
        if zone not in frame.zone_pixels:
            for pixel_idx in zone.pixel_indices:
                pixels[pixel_idx] = (0, 0, 0)
```

**Estimated Time**: 30 minutes

---

## Code Quality Issues

### Color Conversion Repetition
**Status**: 🟡 DRY VIOLATION
**Files**: Multiple controllers and services
**Severity**: Low (maintainability)

**Problem**:
```python
# Repeated in StaticModeController, ZoneStripController, etc.
r, g, b = color.to_rgb()
r, g, b = Color.apply_brightness(r, g, b, brightness)
```

**Solution**:
Add method to Color class:
```python
def to_rgb_with_brightness(self, brightness: float) -> Tuple[int, int, int]:
    r, g, b = self.to_rgb()
    return (int(r * brightness), int(g * brightness), int(b * brightness))
```

**Estimated Time**: 30 minutes

---

### Excluded Zones Building Repetition
**Status**: 🟡 DRY VIOLATION
**Files**: `AnimationModeController`, `LEDController`
**Severity**: Low (maintainability)

**Problem**:
```python
# Repeated pattern
excluded_zones = [
    zone.config.id for zone in self.zone_service.get_all()
    if zone.config.id != selected_zone.config.id
]
```

**Solution**:
Add method to ZoneService:
```python
def get_excluded_zones(self, except_zone_id: ZoneID) -> List[ZoneID]:
    return [z.config.id for z in self.get_all() if z.config.id != except_zone_id]
```

**Estimated Time**: 15 minutes

---

### Frame Conversion Consolidation
**Status**: 🟡 DRY VIOLATION
**Files**: `AnimationEngine`, `TransitionService`
**Severity**: Low (code duplication)

**Problem**:
- Similar frame building logic in multiple places
- Yield → frame conversion patterns repeated
- Pixel array building duplicated

**Solution**:
Create utility module:
```python
class FrameBuilder:
    @staticmethod
    def from_zone_yield(zone_id, color, priority) -> ZoneFrame:
        ...

    @staticmethod
    def from_pixel_yield(zone_id, pixel_idx, color, priority) -> PixelFrame:
        ...
```

**Estimated Time**: 1 hour

---

## Testing Gaps

### Missing Tests
- FrameManager priority selection (edge cases)
- Animation switching with crossfade
- Hardware timing validation
- Multi-GPIO rendering consistency

**Estimated Time per test suite**: 2-3 hours

---

## Performance Optimization

### Optional Improvements
- Frame queue optimization (currently linear scan)
- Batch zone updates
- Cache pixel indices (instead of computing each frame)
- SIMD color conversions (if performance-critical)

**Current Performance**: Adequate (4.25ms used of 16.67ms budget)
**Priority**: Low

---

## Documentation

### Related Documentation
- See `/context/.documentation/1_rendering_system/user/` for user guide
- See `/context/.documentation/1_rendering_system/agent/` for implementation details
- See `/context/project/todo.md` for overall project tasks

---

## Task Summary

| Task | Priority | Time | Blocker |
|------|----------|------|---------|
| Fix SnakeAnimation zero division | 🔴 BLOCKING | 5m | YES |
| Ghost pixels investigation | 🟡 MEDIUM | 2-4h | NO |
| Power-off flickering | 🟡 MEDIUM | 1-2h | NO |
| Preview panel integration | 🟡 MEDIUM | 3-4h | NO |
| Implement clear_other_zones flag | 🟢 LOW | 30m | NO |
| Color conversion refactor | 🟢 LOW | 30m | NO |
| Excluded zones helper | 🟢 LOW | 15m | NO |
| Frame builder utilities | 🟢 LOW | 1h | NO |

---

**Last Updated**: 2025-11-25
**Next Review**: After SnakeAnimation fix + testing