---
Last Updated: 2025-11-19
Updated By: @architecture-expert-sonnet
Changes: Comprehensive TODO list from codebase scan (Nov 19)
---

# Diuna Project - Critical TODO List

**Status**: Dual GPIO LED strips working! ✅ Color order fixed, startup/shutdown fixed.

---

## 🔴 CRITICAL (Blocking Core Functionality)

### 1. Preview Panel Complete Re-enable
**Severity**: CRITICAL | **Status**: BLOCKED
**Files**: `main_asyncio.py:263-286`, `controllers/led_controller/led_controller.py:69-70`

**What's needed**:
- [ ] Uncomment PreviewPanelController initialization
- [ ] Pass preview_panel to FrameManager
- [ ] Create transition service for preview strip
- [ ] Route animation previews through FrameManager (not direct calls)
- [ ] Test: PIXEL and PREVIEW zones light up at startup
- [ ] Test: Preview responds to zone selection

**Why**: 8 LEDs (CJMCU-2812-8 module) on GPIO 19 currently unused. Blocks zone feedback visualization.

**Estimate**: 1-2 hours (mostly testing)

---

### 2. Multi-GPIO Architecture Complete
**Severity**: CRITICAL | **Status**: PARTIAL (both GPIOs init, only 18 used)
**Files**: `main_asyncio.py:232-277`, `controllers/led_controller/led_controller.py:67`, `animations/engine.py`

**What's needed**:
- [ ] Add zone-to-GPIO mapping in Zone domain model
- [ ] Route zone state updates to correct GPIO's FrameManager queue
- [ ] Update AnimationEngine to support multi-GPIO (currently binds to GPIO 18 only)
- [ ] Verify FrameManager renders both GPIO 18 and GPIO 19 simultaneously
- [ ] Test: Animation on LAMP zone (GPIO 18), PIXEL zone lights independently with different color

**Why**: GPIO 19 (PIXEL + PREVIEW) zones created but unreachable from controllers.

**Estimate**: 2-3 hours

---

### 3. Per-Zone Animation Exclusion Actually Works
**Severity**: CRITICAL | **Status**: FAKE (accepts exclusion, ignores it)
**Files**: `animations/engine.py:432-449`, `controllers/led_controller/led_controller.py:353-441`

**What's needed**:
- [ ] Verify animation implementations actually filter excluded zones
- [ ] Check BaseAnimation and all subclasses (snake, matrix, breathe, etc.)
- [ ] Update frame merge logic to respect zone exclusions
- [ ] Test: Press Button 4 to isolate LAMP animation, verify other zones don't animate

**Current bug**:
```python
excluded_zone_ids = [z.config.id for z in ... if z.config.id != zone_id]
await self.animation_engine.start(anim_id, excluded_zones=excluded_zone_ids, **safe_params)
# ^ Animation accepts parameter but ignores it
```

**Why**: Can't run animation on single zone. Core UI feature (Button 4) doesn't work.

**Estimate**: 1-2 hours (debugging animation logic)

---

## 🟠 HIGH (Impacts Stability & Features)

### 4. Zone State Persistence Across Restart
**Severity**: HIGH | **Status**: BROKEN
**Files**: `state.json`, `services/data_assembler.py`, `models/domain/zone.py`

**What's needed**:
- [ ] Ensure state.json always saves zone.mode (STATIC, ANIMATION, etc.)
- [ ] DataAssembler must restore mode for each zone on load
- [ ] Add schema validation (reject state files with missing mode)
- [ ] Test: Toggle zone to ANIMATION mode, restart app, verify mode persists

**Current issue**:
- Zone mode saved in memory but not always in state.json
- Power cycle loses which zones are in animation mode
- State file inconsistent (some zones have mode, others don't)

**Estimate**: 1 hour

---

### 5. FrameManager Lock Contention & Frame Drops
**Severity**: HIGH | **Status**: UNFIXED
**Files**: `engine/frame_manager.py:127-129, 179-197, 326-336`

**What's needed**:
- [ ] Replace asyncio.Lock with lock-free queue (or triple-buffer)
- [ ] Or: increase deque maxlen from 2 to 10 and add drop counter logging
- [ ] Add metrics: submission_wait_time, dropped_frames per priority
- [ ] Stress test: 60 animations running, verify no frame loss

**Current issue**:
- Frame deques max 2 items (very small)
- Lock held during frame selection (~1-2ms)
- If submission blocked, frame is silently dropped
- Causes animation stutter under load

**Estimate**: 2-3 hours

---

### 6. Control Panel Input Debouncing
**Severity**: HIGH | **Status**: UNKNOWN
**Files**: `components/rotary_encoder.py`, `components/button.py`, `controllers/control_panel_controller.py`

**What's needed**:
- [ ] Verify RotaryEncoder and Button classes exist (may be missing)
- [ ] Check if they implement debouncing (20-50ms delay)
- [ ] If missing: implement debouncing in rotary_encoder.py and button.py
- [ ] Test: Rotate encoder rapidly, verify no duplicate events
- [ ] Test: Press button, verify single event (not 2-3x from bounce)

**Why**: Bouncing contacts cause multiple events per action. UI feels unresponsive.

**Estimate**: 1-2 hours (if classes need implementation)

---

### 7. Static Mode Pulse Task Memory Leaks
**Severity**: HIGH | **Status**: REAL ISSUE
**Files**: `controllers/led_controller/static_mode_controller.py:49-50, 177-206`

**What's needed**:
- [ ] Add task names: `asyncio.create_task(self._pulse_task(), name=f"pulse_{zone_id}")`
- [ ] Fix cancellation: add `await self.pulse_task` in _stop_pulse()
- [ ] Add pulse_task counter to metrics
- [ ] Test: Toggle edit mode 100x, verify pulse_task count stays 0-1

**Current issue**:
```python
def _stop_pulse(self):
    self.pulse_active = False
    if self.pulse_task:
        self.pulse_task.cancel()  # ← Doesn't wait for completion
        # Task may still be running in background
```

After 1000 zone changes: 1000 orphaned pulse tasks consuming memory.

**Estimate**: 30 min

---

## 🟡 MEDIUM (Polish & Correctness)

### 8. Animation Engine First Frame Race Condition
**Severity**: MEDIUM | **Status**: UNFIXED
**Files**: `animations/engine.py:296-355`

**What's needed**:
- [ ] Capture single first frame without running animator
- [ ] Render to buffer without starting loop
- [ ] Then fade in from buffer
- [ ] Then start animation loop fresh
- [ ] Test: Watch animation startup, verify no flicker

**Current issue**:
- First frame collection takes ~75ms while animator is running
- Stale yields in buffer when transition starts
- Causes animation flicker on startup

**Estimate**: 1-2 hours

---

### 9. Hardware State Capture with Zone Reversal
**Severity**: MEDIUM | **Status**: PARTIAL BUG
**Files**: `components/led_channel.py:238-246`

**What's needed**:
- [ ] Decide: use `components/led_channel.py` OR `zone_layer/led_channel.py` (don't keep both!)
- [ ] In `get_frame()`, apply zone reversal mapping
- [ ] Or: transition service accounts for reversal
- [ ] Test: Capture frame from reversed zone, fade to black, verify pixels match

**Current issue**:
- Two ZoneStrip implementations exist (confusing)
- `get_frame()` returns raw buffer without reversal
- But `show_full_pixel_frame()` applies reversal during render
- Mismatch: captured frame ≠ rendered frame

**Estimate**: 1 hour

---

### 10. Preview FrameManager Integration
**Severity**: MEDIUM | **Status**: ORPHANED
**Files**: `engine/frame_manager.py:144-148, 390-396`

**What's needed**:
- [ ] Uncomment preview strip registration (blocked by #1)
- [ ] Route animation preview updates through FrameManager (not direct calls)
- [ ] PreviewPanelController queues frames instead of calling directly
- [ ] Test: Verify preview responds to animation priority

**Current issue**:
- PreviewPanelController calls `preview_panel.show_frame()` directly
- Bypasses FrameManager priority system
- Can't interrupt preview with high-priority updates

**Estimate**: 1 hour (blocked by #1)

---

## 📋 Quick Reference: File Locations

| Component | Files |
|-----------|-------|
| **Preview Panel** | `main_asyncio.py:263-286`, `controllers/preview_panel_controller.py` |
| **Multi-GPIO** | `main_asyncio.py:232-277`, `models/domain/zone.py`, `animations/engine.py` |
| **Animation** | `animations/engine.py`, `animations/base.py`, all animation classes |
| **Zone State** | `models/domain/zone.py`, `services/data_assembler.py`, `state/state.json` |
| **FrameManager** | `engine/frame_manager.py` |
| **Control Panel** | `components/rotary_encoder.py`, `components/button.py`, `controllers/control_panel_controller.py` |
| **Static Mode** | `controllers/led_controller/static_mode_controller.py` |

---

## 🎯 Recommended Fix Order

**Phase 1 (This Week)**: Critical path to working dual-GPIO
1. Fix #2 (Multi-GPIO Architecture) → unblock GPIO 19 zones
2. Fix #3 (Animation Exclusion) → Button 4 works
3. Re-enable #1 (Preview Panel) → 8 LEDs usable

**Phase 2 (Next Week)**: Stability
4. Fix #4 (State Persistence)
5. Fix #5 (Frame Lock)
6. Fix #7 (Pulse Leaks)

**Phase 3**: Polish
7. Fix #8 (First Frame Race)
8. Fix #6 (Input Debouncing)
9. Fix #9 (Reversal)
10. Fix #10 (Preview Integration)

---

## ✅ Recently Fixed

- ✅ PWM channel mapping (GPIO 18→0, GPIO 19→1)
- ✅ DMA channel (both use 10, not 11)
- ✅ Color order (GPIO 18: BGR, GPIO 19: GRB)
- ✅ Brightness (255 for full visibility)
- ✅ Startup fade for all GPIO strips
- ✅ Shutdown clear for all GPIO strips
- ✅ EVENT log color (BRIGHT_MAGENTA, not BRIGHT_RED)

---

## 🧪 Testing Checklist

Before considering "done":
- [ ] All 8 zones light independently with correct colors
- [ ] Both GPIO strips (18 + 19) render simultaneously
- [ ] Animations run on selected zone only (Button 4 isolation)
- [ ] PIXEL and PREVIEW zones operational
- [ ] Power cycle: all state persists
- [ ] App shutdown: all LEDs turn off
- [ ] App startup: all LEDs light with initial colors
- [ ] 1-hour stress test: no frame drops, no memory leaks
- [ ] Rapid encoder/button: no duplicate events

