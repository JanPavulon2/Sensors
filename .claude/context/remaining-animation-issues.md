# Remaining Animation System Issues

**Status**: Phase 5 refactoring completed, but critical animation bugs remain.
**Priority**: HIGH - Blocks Phase 6 work
**Last Updated**: 2025-11-08

---

## Issues Identified

### 1. Power Off Animation Mode - Stale Pixels Remain
**Severity**: CRITICAL
**Observed Behavior**:
- When powering off while in ANIMATION mode
- Fade out occurs, but pixels don't fully go dark
- Last animation pixels remain lit

**Expected**: All pixels fade to black smoothly

**Attempted Fixes**:
- Clearing buffer when stopping animation ✗
- Clearing buffer before fade_out ✗
- Separate zone/pixel buffers ✗

**Hypothesis**:
- FrameManager priority issue (TRANSITION=40 vs ANIMATION=30)
- Stale animation frames still being submitted during fade
- TransitionService not properly capturing current strip state before fade
- Possible: Animation loop still running after stop() is called

---

### 2. Animation Cycling - Ghost Pixels When Transitioning
**Severity**: HIGH
**Observed Behavior**:
- When switching between animations (e.g., ColorFade → ColorSnake)
- Old animation pixels don't fully clear
- Some pixels fade out gradually while others stay lit briefly
- "Most pixels stay, then they go black after snake 'runs over them'"

**Expected**: Clean transition with no ghost pixels

**Attempted Fixes**:
- Clearing buffer when starting new animation ✗
- Clearing buffer in start() before _get_first_frame() ✗
- Separate zone/pixel buffers ✗

**Hypothesis**:
- Old animation still submitting frames during crossfade
- Task cancellation not fast enough
- Buffer not cleared between animation yields
- Possible: Transitions using stale pixel data

---

### 3. App Startup Flicker
**Severity**: MEDIUM
**Observed Behavior**:
- When app starts in ANIMATION mode
- Brief flicker/flash before animation stabilizes

**Status**: May be acceptable (inherent to transition system)

---

## Code Architecture Issues to Investigate

### AnimationEngine._run_loop()
- Submits frame on EVERY yield (not every complete animation frame)
- Buffer accumulation strategy unclear
- No frame-boundary detection

### TransitionService.fade_out()
- Uses current_frame from strip.get_frame()
- No verification that animation has stopped before capture
- Concurrent fades might interfere

### FrameManager Priority Handling
- TRANSITION (40) > ANIMATION (30)
- Verify transition frames aren't persisting after fade completes
- Check queue cleanup after submission

### Power Toggle Sequence
1. Stop animation (skip_fade=True)
2. Fade out strip (TransitionService)
3. Set brightness to 0
- Verify step 1 fully stops before step 2 begins
- Check if animation task cancellation is awaited properly

---

## Next Actions Recommended

1. **Trace execution flow**:
   - Add detailed logging to AnimationEngine._run_loop()
   - Log frame submissions to FrameManager
   - Log buffer state before/after transitions

2. **Verify animation stop**:
   - Confirm animation task is fully cancelled before fade
   - Check if new animation frames are still being submitted during fade_out

3. **Review FrameManager queue management**:
   - Ensure old ANIMATION frames are not selected after TRANSITION completes
   - Verify TTL/priority expiration is working

4. **Investigate TransitionService**:
   - Check if fade captures correct strip state
   - Verify concurrent fades (main + preview) don't interfere

5. **Consider redesign**:
   - Animation loop might need different buffering strategy
   - May need frame-boundary detection (sleep as frame marker)
   - Consider double-buffering approach

---

## Files Modified
- `src/animations/engine.py` - Multiple buffer handling changes
- `src/services/transition_service.py` - Removed parallel rendering
- `src/controllers/led_controller/power_toggle_controller.py` - Added mode-specific logic

---

## Known Good State
- Phase 1-4: FrameManager, TransitionService, AnimationEngine initialization
- Parallel rendering eliminated (no more direct show() calls)
- Startup fade and power on in STATIC mode work correctly
