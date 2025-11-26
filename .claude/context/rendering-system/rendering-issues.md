# Rendering System Violations & Refactor Plan

**Branch:** `refactor/pre-api-perfection`
**Analysis Date:** 2025-11-19
**Status:** Hardware abstraction 95% complete ✅

---

## Executive Summary

The rendering system refactor is **nearly complete** with excellent hardware abstraction. Only **4 critical violations** remain, all easily fixable. The core architecture (FrameManager, WS281xStrip, ZonePixelMapper) is production-ready.

**Critical Issues:**
1. TransitionService bypasses FrameManager (4 `strip.clear()` calls)
2. ZoneStrip missing `zone_indices` property (breaks compatibility)
3. AnimationEngine touches strip buffer directly in `_get_first_frame()`
4. PreviewPanel has unused rpi_ws281x import

---

## Architecture Status ✅

### What's Working Perfectly

**Hardware Layer:**
- ✅ `WS281xStrip` - Only place that touches `rpi_ws281x`
- ✅ `IPhysicalStrip` protocol - Clean abstraction interface
- ✅ Color order remapping, DMA optimization, buffer management

**Zone Layer:**
- ✅ `ZoneStrip` - Uses `IPhysicalStrip`, no hardware coupling
- ✅ `ZonePixelMapper` - Clean zone→pixel mapping with reversed support
- ✅ `apply_frame()` - Atomic single-DMA rendering

**Rendering Engine:**
- ✅ `FrameManager` - Priority queues, 60 FPS loop, atomic rendering
- ✅ Frame types - FullStripFrame, ZoneFrame, PixelFrame, PreviewFrame
- ✅ WS2811 timing enforcement (2.75ms minimum)
- ✅ Pause/step/resume (frame-by-frame debugging)

**Animations:**
- ✅ Properly isolated - yield tuples, never touch hardware
- ✅ `run()` and `run_preview()` generators working
- ✅ BaseAnimation provides clean API

---

## Critical Violations

### 1. ❌ TransitionService - FrameManager Bypass

**File:** `src/services/transition_service.py`
**Severity:** 🔴 **CRITICAL** - Breaks priority system

**Violations:**
```python
# Line 185 - in _fade_out_no_lock()
self.strip.clear()  # ❌ BYPASSES FrameManager

# Line 386 - in fade_in_from_black()
self.strip.clear()  # ❌ BYPASSES FrameManager

# Line 426 - in fade_to_new_state()
self.strip.clear()  # ❌ BYPASSES FrameManager

# Line 543 - in cut()
self.strip.clear()  # ❌ BYPASSES FrameManager
```

**Why This is Critical:**
- Direct hardware manipulation bypasses FrameManager's priority system
- Can cause race conditions with animations
- Violates "all rendering goes through FrameManager" rule

**Fix:**
Replace all `strip.clear()` with black PixelFrame submissions:

```python
# Instead of: self.strip.clear()

# Use:
black_frame = [(0, 0, 0)] * self.strip.pixel_count
zone_pixels_dict = self._get_zone_pixels_dict(black_frame)
pixel_frame = PixelFrame(
    priority=FramePriority.TRANSITION,
    source=FrameSource.TRANSITION,
    zone_pixels=zone_pixels_dict
)
await self.frame_manager.submit_pixel_frame(pixel_frame)
```

**Estimated Time:** 30 minutes

---

### 2. ⚠️ ZoneStrip - Missing `zone_indices` Property

**File:** `src/zone_layer/zone_strip.py`
**Severity:** 🔴 **CRITICAL** - Runtime crashes

**Issue:**
New ZoneStrip uses `ZonePixelMapper` internally but doesn't expose `zone_indices` property that other code expects.

**Affected Files:**
```python
# src/engine/frame_manager.py:408
if hasattr(strip, 'zone_indices'):
    for zone_key in strip.zone_indices.keys():  # ❌ AttributeError

# src/services/transition_service.py:153
if hasattr(self.strip, 'zone_indices') and self.strip.zone_indices:  # ❌ AttributeError

# src/controllers/led_controller/frame_playback_controller.py:238
for zone_name, physical_indices in strip.zone_indices.items():  # ❌ AttributeError
```

**Fix:**
Add backward-compatible property to ZoneStrip:

```python
# In zone_layer/zone_strip.py

@property
def zone_indices(self) -> Dict[str, List[int]]:
    """
    Get zone→indices mapping (backward compatibility).

    Returns dict with string keys (ZoneID.name) for legacy code.

    Example: {"FLOOR": [0,1,2,3], "TOP": [4,5,6,7]}
    """
    return {
        zone_id.name: self.mapper.get_indices(zone_id)
        for zone_id in self.mapper.all_zone_ids()
    }
```

**Estimated Time:** 5 minutes

---

### 3. ⚠️ AnimationEngine - Direct Strip Manipulation

**File:** `src/animations/engine.py:300, 303`
**Severity:** 🟡 **MEDIUM** - Code quality issue

**Violation:**
```python
# In _get_first_frame()
async for frame in gen:
    if len(frame) == 5:
        zone_id, pixel_index, r, g, b = frame
        self.strip.set_pixel_color(zone_id, pixel_index, r, g, b, show=False)  # ❌
    elif len(frame) == 4:
        zone_id, r, g, b = frame
        self.strip.set_zone_color(zone_id, r, g, b, show=False)  # ❌
```

**Why This is Problematic:**
- Mutates shared strip buffer while FrameManager may be rendering
- Unclear code flow (mixing buffer manipulation with frame building)
- Potential race condition between `_get_first_frame()` and render loop

**Fix:**
Build frame in memory instead of touching strip:

```python
async def _get_first_frame(self) -> Optional[Dict[ZoneID, List[Tuple[int, int, int]]]]:
    """
    Build first frame in memory without touching strip buffer.

    Returns:
        zone_pixels_dict ready for PixelFrame submission
    """
    if not self.current_animation:
        return {}

    try:
        gen = self.current_animation.run()
        zone_pixels_buffer: Dict[ZoneID, Dict[int, Tuple[int, int, int]]] = {}
        zone_colors_buffer: Dict[ZoneID, Tuple[int, int, int]] = {}

        yields_collected = 0
        max_yields = 100

        async for frame in gen:
            if len(frame) == 5:
                # Pixel-level: (zone_id, pixel_index, r, g, b)
                zone_id, pixel_index, r, g, b = frame
                zone_pixels_buffer.setdefault(zone_id, {})[pixel_index] = (r, g, b)
            elif len(frame) == 4:
                # Zone-level: (zone_id, r, g, b)
                zone_id, r, g, b = frame
                zone_colors_buffer[zone_id] = (r, g, b)

            yields_collected += 1
            await asyncio.sleep(0.005)

            if yields_collected >= 15:
                break

        await gen.aclose()

        # Convert to PixelFrame format
        zone_pixels_dict: Dict[ZoneID, List[Tuple[int, int, int]]] = {}

        # Process zone-level updates
        for zone_id, color in zone_colors_buffer.items():
            zone_length = self.zone_lengths.get(zone_id, 0)
            zone_pixels_dict[zone_id] = [color] * zone_length

        # Process pixel-level updates (overwrites zone colors if present)
        for zone_id, pixels_dict in zone_pixels_buffer.items():
            zone_length = self.zone_lengths.get(zone_id, 0)
            # Start with zone color if present, else black
            if zone_id in zone_pixels_dict:
                pixels_list = zone_pixels_dict[zone_id].copy()
            else:
                pixels_list = [(0, 0, 0)] * zone_length

            # Overlay pixel updates
            for pixel_idx, color in pixels_dict.items():
                if 0 <= pixel_idx < zone_length:
                    pixels_list[pixel_idx] = color

            zone_pixels_dict[zone_id] = pixels_list

        return zone_pixels_dict

    except Exception as e:
        log.error(f"Failed to build first frame: {e}")
        return {}
```

**Also Update Caller:**
```python
# In AnimationEngine.start() - around line 180
first_frame_dict = await self._get_first_frame()

# Convert to absolute frame for crossfade
if first_frame_dict:
    first_frame = self.strip.build_frame_from_zones(
        {zone_id: pixels[0] for zone_id, pixels in first_frame_dict.items()}
    )
    # ... existing crossfade logic
```

**Estimated Time:** 20 minutes

---

### 4. 🟢 PreviewPanel - Unused Import

**File:** `src/components/preview_panel.py:12`
**Severity:** 🟢 **LOW** - Code cleanup

**Violation:**
```python
from rpi_ws281x import PixelStrip, Color  # ❌ Unused (line 69 commented out)
```

**Fix:**
Simply delete the import line (already commented out in actual usage).

```python
# Remove this line:
from rpi_ws281x import PixelStrip, Color
```

**Estimated Time:** 1 minute

---

## Additional Notes from User Changes

### PixelFrame Enhancement
User added `clear_other_zones: bool = False` field to PixelFrame (line 65).

**Purpose:** Allows animations to explicitly clear zones not in the frame dict.

**Usage Consideration:**
- When `clear_other_zones=True`, FrameManager should zero out zones not in `zone_pixels` dict
- Current FrameManager doesn't implement this yet
- May need FrameManager update to respect this flag

### AnimationEngine Enhancements
User added:
- `freeze()` / `unfreeze()` methods for frame-by-frame debugging (lines 267-287)
- Static zone merging in render loop (lines 408-424)
- Conditional frame submission when frozen (line 428)

**Status:** ✅ These are excellent additions, no violations found

---

## Priority Fix Order

### 🔴 Phase 1: Critical Fixes (Prevents Crashes)
**Time: ~35 minutes**

1. **Add `zone_indices` property to ZoneStrip** (5 min)
   - Prevents AttributeError in FrameManager, TransitionService, frame playback
   - Backward compatibility essential for existing code

2. **Fix TransitionService `strip.clear()` violations** (30 min)
   - Replace all 4 direct `clear()` calls with PixelFrame submissions
   - Critical for FrameManager priority system integrity

### 🟡 Phase 2: Code Quality (Best Practices)
**Time: ~20 minutes**

3. **Refactor AnimationEngine `_get_first_frame()`** (20 min)
   - Build frame in memory instead of touching strip buffer
   - Eliminates potential race conditions
   - Cleaner code separation

### 🟢 Phase 3: Cleanup
**Time: ~1 minute**

4. **Remove rpi_ws281x import from preview_panel.py** (1 min)
   - Delete unused import line
   - Code hygiene

---

## Testing Checklist

After implementing fixes:

- [ ] Animations start/stop without errors
- [ ] Transitions (fade in/out/crossfade) work smoothly
- [ ] No direct hardware calls outside WS281xStrip
- [ ] Frame-by-frame mode works (pause/step/resume)
- [ ] Preview panel renders correctly
- [ ] Static zones merge properly in animations
- [ ] No AttributeError for `zone_indices`
- [ ] FrameManager priority system respected (no bypasses)

---

## Future Enhancements (Not Violations)

### 1. PreviewFrame Integration
**Status:** Preview panel exists but not integrated with FrameManager preview queue

**Missing:**
- PreviewService to consume `animation.run_preview()` generators
- Registration of PreviewPanel with FrameManager
- Preview frame submission pipeline

**Recommended:** Create `PreviewService` to bridge animations and preview panel

### 2. PixelFrame `clear_other_zones` Implementation
**Status:** Field added to model but not implemented in FrameManager

**Fix Required:**
In `FrameManager._render_pixel_frame()`, check flag:
```python
if frame.clear_other_zones:
    # Zero out zones not in frame.zone_pixels dict
    all_zones = set(strip.mapper.all_zone_ids())
    rendered_zones = set(frame.zone_pixels.keys())
    for zone_id in (all_zones - rendered_zones):
        # Clear this zone
```

---

## Conclusion

The rendering system is **architecturally sound** with only minor violations remaining. All fixes are straightforward and non-breaking. The team has done excellent work on:

- Hardware abstraction layer (WS281xStrip)
- Zone mapping (ZonePixelMapper)
- Frame-based rendering (FrameManager)
- Animation isolation (BaseAnimation)

After fixing the 4 violations listed above, the rendering system will be **production-ready** and fully compliant with the architectural design.

**Recommended Action:** Implement fixes in order of priority (Critical → Quality → Cleanup).
