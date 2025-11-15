# Phase 5 DevTest Failures Report

**Date**: 2025-11-08
**Tester**: Harki
**Phase**: 5 - TransitionService Integration

## Issues Found

### 1. Startup Fade-In Flickering ⚠️
**Status**: Intermittent (can't reproduce consistently)
- **Test Case**: App startup
- **Expected**: Smooth 2-second fade from black
- **Actual**: Flickering at first attempt
- **Frequency**: Inconsistent (first test attempt sometimes)
- **Likely Cause**: Race condition in fade_in_from_black() - black frame timing issue

### 2. Animation Switch Glitches ⚠️
**Status**: Reproducible
- **Test Case**: Switch between animations (particularly Color Cycle, Color Fade)
- **Expected**: Smooth 400ms fade transition
- **Actual**: Flash/glitch at animation start
- **Pattern**: Happens at animation start, not during fade
- **Affected Animations**: Color Cycle, Color Fade
- **Likely Cause**: AnimationEngine frame submission to FrameManager not synchronized with transition end

### 3. Power Off in Animation Mode 🔴
**Status**: Complete failure
- **Test Case**: BTN3 press while in ANIMATION mode
- **Expected**: All LEDs fade to black
- **Actual**: No response - LEDs stay on
- **Likely Cause**: Power toggle handler doesn't work with ANIMATION mode / FrameManager integration

### 4. Power On After Power Off (Animation Mode) ⚠️
**Status**: Reproducible
- **Test Case**: BTN3 press to turn back on after turning off in ANIMATION mode
- **Expected**: Smooth fade back to current animation
- **Actual**: Flicker observed
- **Likely Cause**: Animation engine state not properly managed during power toggle

### 5. Power Off in Static Mode (Partial Failure) ⚠️
**Status**: Reproducible
- **Test Case**: BTN3 press while in STATIC mode
- **Expected**: All zones fade to black
- **Actual**: Some zones flicker, some don't go fully black
- **Pattern**: Inconsistent zone behavior
- **Likely Cause**: Frame priority conflict between MANUAL (static) and TRANSITION (power off)

## Root Cause Analysis

### Problem 1: Transition + Animation Race Condition
- `fade_in()` uses lock to submit frames
- But animation engine starts rendering immediately after transition ends
- First frame from animation may not be ready when transition ends
- Result: Flash or glitch visible

### Problem 2: Power Toggle Not Integrated with FrameManager
- Power toggle uses old TransitionService APIs
- Doesn't account for FrameManager priority system
- Animation engine still running during power off
- Result: LEDs don't respond, animation continues

### Problem 3: Priority Queue Conflict
- MANUAL (static) frames and TRANSITION (power off) frames competing
- FrameManager selects highest priority (TRANSITION)
- But if animation stops between frames, MANUAL doesn't kick in smoothly
- Result: Zones show inconsistent behavior

## Next Steps (Investigation + Fixes)

1. **Investigate animation start glitch**
   - Check if animation engine waits for crossfade to complete
   - Add synchronization point before animation loop starts

2. **Fix power toggle in animation mode**
   - Add power state handling to LEDController
   - Ensure animation engine properly stops during power off
   - Re-sync animation on power on

3. **Fix static mode power toggle**
   - Ensure MANUAL frames properly fallback when TRANSITION ends
   - Check zone visibility after transition

4. **Race condition in fade_in_from_black**
   - Verify timing between clear() and fade_in()
   - Add minimum delay between clear and fade start
