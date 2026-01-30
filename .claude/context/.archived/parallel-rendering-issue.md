# Critical Architecture Issue: Parallel Rendering Paths

**Identified**: 2025-11-08 (during Phase 5 devtest)
**Severity**: CRITICAL - Causes all flickering/glitching
**Root Cause**: Two simultaneous rendering systems accessing hardware

---

## The Problem

The codebase has **TWO separate rendering systems** that both call `strip.show()`:

### Path 1: FrameManager (Intended Centralized System)
```
AnimationEngine.start()
  → PixelFrame submission
    → FrameManager.submit_pixel_frame()
      → main_queues[ANIMATION] += frame
        → _render_loop() selects highest priority
          → strip.show() ✓ (ONE call per tick)
```

### Path 2: Direct Hardware Access (Legacy system, STILL ACTIVE)
```
StaticModeController.enter_mode()
  → render_zone(zone_id, color, brightness)
    → led_channel.set_zone_color()
      → strip.show() ✗ (DIRECT, bypasses FrameManager)

TransitionService.fade_out()
  → for each fade step:
    → strip.set_pixel_color_absolute(i, r, g, b)
      → strip.show() ✗ (DIRECT, bypasses FrameManager)

PreviewPanel methods
  → _pixel_strip.show() ✗ (DIRECT, separate hardware)
```

### Result: Race Condition
```
Time | FrameManager | Direct Methods | Hardware Display
-----|---|---|---
T0   | Submits ANIM frame | StaticController calls show() | Which frame visible?
T1   | Selects & renders | TransitionService calls show() | Glitch/flicker
T2   | Calls show() | (still rendering) | Corruption
T3   | - | - | ?
```

---

## Why This Happens

1. **FrameManager was added as centralized renderer** (Phase 3)
   - Designed to be the ONLY place calling show()
   - Manages priority-based frame selection
   - Synchronizes main strip + preview

2. **But legacy direct methods still exist and are ACTIVELY USED**:
   - `led_channel.set_zone_color()` - calls show() directly
   - `led_channel.set_pixel_color_absolute()` - calls show() directly
   - `led_channel.clear()` - calls show() directly
   - `TransitionService.fade_out/fade_in()` - call show() directly
   - `PreviewPanel` render methods - call show() directly

3. **Controllers still use these legacy methods**:
   - StaticModeController.render_zone()
   - TransitionService internal methods
   - PowerToggleController (indirectly)

---

## Devtest Observations That Confirm This

1. **"Only zone 'floor' went black"** - FLOOR is used as dummy zone in fade_out()
   - TransitionService only submits to FLOOR zone in FrameManager
   - But `strip.show()` is called directly with only partial data
   - Other zones have stale MANUAL frames from StaticController
   - Result: Race between TRANSITION frame (FLOOR only) and MANUAL frames (all zones)

2. **"Some zones flicker, some don't"** - Timing dependent
   - Depends on which rendering path wins the race
   - Different each time (inconsistent)

3. **"Single pixels showing incorrect values"** - Buffer corruption
   - Two systems modifying same pixel buffer simultaneously
   - No synchronization between them

---

## The Fix (Required Architecture Change)

### Phase 6-7 (Skipped, Now Required)

**Goal**: Remove ALL direct show() calls except in FrameManager

1. **StaticModeController Integration**
   - Instead of calling `render_zone()` (which calls show())
   - Submit MANUAL priority PixelFrames to FrameManager
   - Only FrameManager calls show()

2. **TransitionService Integration**
   - Already partially done (submits to FrameManager)
   - BUT: Lines 214, 219 still call show() directly (fallback)
   - Remove these fallback show() calls
   - ONLY use FrameManager submission

3. **ZoneStrip Method Refactor**
   - `set_zone_color()` - should NOT call show()
   - `set_pixel_color()` - should NOT call show()
   - `clear()` - should NOT call show()
   - Add new `set_zone_color_no_show()` if needed for compatibility

4. **PreviewPanel Integration**
   - PreviewPanel has separate `_pixel_strip`
   - FrameManager already handles preview submission
   - Remove direct show() calls from preview methods

### Implementation Order

1. **Fix TransitionService** (immediate - quick)
   - Remove direct show() calls (lines 214, 219)
   - Ensure all fallback paths go through FrameManager

2. **Fix StaticModeController** (Phase 6)
   - Submit MANUAL priority frames to FrameManager instead of calling render_zone()
   - Requires frame_manager parameter

3. **Update ZoneStrip methods** (Phase 6)
   - Add `_no_show` variants if needed
   - Or integrate with FrameManager directly

4. **Verify AnimationEngine** (Phase 4 validation)
   - Ensure all animation frames go through FrameManager
   - No direct show() calls

---

## Why This Matters

**Without this fix**:
- Flickering persists
- Glitching continues
- Unpredictable zone visibility
- Animation switches glitch
- Power toggles unreliable

**With this fix**:
- Single rendering path (FrameManager only)
- No race conditions
- Priority-based fallback works
- Smooth transitions guaranteed
- Predictable hardware updates

---

## Current Status

- **FrameManager**: Ready (Phase 3) ✓
- **AnimationEngine**: Uses FrameManager (Phase 4) ✓
- **TransitionService**: Partially integrated (has direct show() fallback) ⚠️
- **StaticModeController**: NOT integrated (uses direct render_zone) ✗
- **PreviewPanel**: NOT integrated (separate system) ✗

**Next Action**: Remove parallel rendering paths before further devtesting

---

## Code Changes Needed

### 1. TransitionService (Immediate)
Remove lines with direct `show()` calls in _fade_out_no_lock(), fade_in(), etc.
Replace fallback with retry logic or error handling.

### 2. StaticModeController (Phase 6)
```python
# CURRENT (bypasses FrameManager):
self.strip_controller.render_zone(zone_id, color, brightness)

# NEW (goes through FrameManager):
zone_pixels = {zone_id: [(r, g, b)] * zone_pixel_count}
frame = PixelFrame(priority=FramePriority.MANUAL, zone_pixels=zone_pixels)
await self.frame_manager.submit_pixel_frame(frame)
```

### 3. AnimationModeController (Phase 7)
Verify already uses FrameManager (it should)

---

## Testing After Fix

Once parallel rendering eliminated:
1. Startup fade should be smooth (no flickering)
2. Power toggle should affect ALL zones equally
3. Animation switches should be glitch-free
4. No single-pixel corruption
5. Preview synchronized with main strip
