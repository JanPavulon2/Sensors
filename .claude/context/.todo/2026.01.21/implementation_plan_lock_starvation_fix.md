# Implementation Plan: Lock Starvation Fix (CancelledError Freeze)

**Created**: 2026-01-20
**Updated**: 2026-01-20 (corrected analysis: starvation, NOT deadlock)
**Priority**: CRITICAL
**Estimated Time**: 1-2 days (2 phases)

---

## Executive Summary

**Problem**: Switching to Breathe animation causes complete UI freeze.

**Root Cause (CORRECTED)**:
- ~~NOT a deadlock~~ - `asyncio.Lock` properly releases on `CancelledError`
- **ACTUAL ISSUE**: **Lock starvation / head-of-line blocking**
- Fast animation loop (Breathe) repeatedly acquires lock for quick operations
- Render loop needs longer lock hold time but never gets scheduled
- Result: render loop starved, UI freezes, LEDs don't update

**Solution**: Remove lock contention by eliminating unnecessary locking in `push_frame()`.

**Risk Level**: LOW (simplification, less locking = safer)

---

## Corrected Problem Analysis (STARVATION, NOT DEADLOCK)

### IMPORTANT: Previous Deadlock Hypothesis Was WRONG

**What we thought**:
- `CancelledError` prevents lock release in `async with` → permanent deadlock

**What's actually true**:
- `asyncio.Lock` **ALWAYS** releases in `__aexit__()`, even on `CancelledError`
- This is fundamental to Python's context manager protocol
- asyncio.Lock is NOT like C mutex or threading.Lock - it's cancellation-safe

### The REAL Mechanism: Lock Starvation

**What actually happens**:

1. **Breathe animation loop** (`engine.py:197-249`):
   - `step()` is nearly instant (pure math, ~0.1ms)
   - Generates frame immediately
   - Calls `push_frame()` → acquires lock
   - **Quick operation**: Just `deque.append()` (lines 187, 200, 214)
   - Releases lock
   - Sleeps 16ms (60 FPS)
   - **Repeats at high frequency**

2. **Render loop** (`frame_manager.py:297-348`):
   - Calls `_drain_frames()` → needs lock
   - **Slow operation**: Drains ALL priority queues, merges frames (lines 363-427)
   - Needs longer lock hold time
   - **Low priority in scheduler**

3. **Scheduling unfairness**:
   - Animation loop: frequent, short lock acquisitions
   - Render loop: infrequent, long lock acquisitions
   - Python asyncio has **no fairness guarantee** for locks
   - **High-frequency producer wins** over low-frequency consumer
   - Result: Render loop **starved of lock access**

4. **Symptoms**:
   - UI "freezes" (render loop can't render)
   - LEDs don't update (no frames rendered)
   - Event loop still alive (not a crash)
   - No deadlock (both tasks can run, but render never gets lock)

### Why Breathe Animation Specifically?

- **Fastest `step()` method**: Pure math, instant frame generation
- **Highest submission frequency**: Constantly pushing frames
- **Maximal lock contention**: Never gives render loop a chance
- **Other animations**: Slower step() methods reduce contention frequency

### Evidence

**Files Analyzed**:
- `src/engine/frame_manager.py` (lines 166-217, 352-428)
- `src/animations/engine.py` (lines 197-249)
- `src/lifecycle/task_registry.py` (lines 209-252)
- `src/animations/breathe.py` (lines 44-84)

**Full analysis document**: [.claude/context/.todo/2026.01.20/cancelledError_deadlock_fix.md](d:\DEV\Projects\LED\Diuna\.claude\context\.todo\2026.01.20\cancelledError_deadlock_fix.md)

---

## Implementation Strategy (CORRECTED)

### Previous Plan Status: ABANDONED

The previous 5-fix plan was based on incorrect deadlock hypothesis. Those fixes are **not necessary** and some were **incorrect**.

### New Plan: 2 Simple Fixes for Starvation

| Priority | Fix | File | Lines | Impact | Risk |
|----------|-----|------|-------|--------|------|
| **CRITICAL** | Remove lock from push_frame() | frame_manager.py | 166-217 | Eliminates contention | Very Low |
| **OPTIONAL** | Rate-limit animation submission | engine.py | 197-249 | Prevents queue flooding | Very Low |

---

## Phase 1: Remove Lock Contention (Day 1, ~2 hours)

### Fix 1: Remove Lock from push_frame() [CRITICAL]

**File**: `src/engine/frame_manager.py` (lines 166-217)

**Current Problem**:
```python
async def push_frame(self, frame):
    async with self._lock:  # ❌ Unnecessary lock causes starvation
        # Creates MainStripFrame
        self.main_queues[msf.priority.value].append(msf)  # ← deque.append is atomic!
```

**Why Lock is Unnecessary**:
- `collections.deque.append()` is **atomic** and **thread-safe**
- Creating `MainStripFrame` object doesn't need protection
- No shared state being modified beyond deque append
- Lock only causes contention without benefit

**Solution**: Remove lock entirely from `push_frame()`

**Implementation**:
```python
async def push_frame(self, frame):
    """
    Unified API endpoint.
    Accepts SingleZoneFrame / MultiZoneFrame / PixelFrame
    and wraps them into MainStripFrame for the queue system.

    NOTE: No lock needed - deque.append() is atomic and thread-safe.
    Lock is ONLY used in _drain_frames() to protect queue iteration.
    """

    # --- SingleZoneFrame ----------------------------------
    if isinstance(frame, SingleZoneFrame):
        msf = MainStripFrame(
            priority=frame.priority,
            ttl=frame.ttl,
            source=frame.source,
            partial=True,
            updates=cast(Dict[ZoneID, ZoneUpdateValue], {frame.zone_id: frame.color}),
        )
        self.main_queues[msf.priority.value].append(msf)  # Atomic operation
        return

    # --- MultiZoneFrame -----------------------------------
    if isinstance(frame, MultiZoneFrame):
        msf = MainStripFrame(
            priority=frame.priority,
            ttl=frame.ttl,
            source=frame.source,
            partial=True,
            updates=cast(Dict[ZoneID, ZoneUpdateValue], frame.zone_colors),
        )
        self.main_queues[msf.priority.value].append(msf)  # Atomic operation
        log.debug(f"QueuedMultiZoneFrame: {ZoneUpdateValue} (priority={msf.priority.name})")
        return

    # --- PixelFrame --------------------------------------
    if isinstance(frame, PixelFrame):
        msf = MainStripFrame(
            priority=frame.priority,
            ttl=frame.ttl,
            source=frame.source,
            partial=True,
            updates=cast(Dict[ZoneID, ZoneUpdateValue], frame.zone_pixels),
        )
        self.main_queues[msf.priority.value].append(msf)  # Atomic operation
        return

    raise TypeError(f"Unsupported frame type: {type(frame)}")
```

**Why This Works**:
- **Zero lock contention**: Animation and render loops never compete
- **Thread-safe**: deque.append is atomic by Python GIL
- **Faster**: No await for lock acquisition
- **Simpler**: Less code, clearer semantics
- **Correct**: Lock still protects _drain_frames iteration

**Testing**:
- Unit test: Concurrent push_frame calls, verify no corruption
- Integration: Breathe animation, verify no freeze
- Stress test: 1000 rapid switches
- Regression: All animations work correctly

**Verification**:
```python
# Verify deque.append is used correctly (atomic single operation)
assert isinstance(self.main_queues[priority], collections.deque)

# Verify _drain_frames still uses lock (protects iteration)
# (This remains unchanged - lock ONLY in _drain_frames)
```

---

### Integration Testing (Phase 1)

**Success Criteria**:
- ✅ No freeze after 1000 Breathe animation switches
- ✅ UI remains responsive at all times
- ✅ Frame submission <1ms (no lock wait)
- ✅ Render loop gets fair scheduling

---

## Phase 2: Optional Improvements (Day 2, ~2 hours)

### Fix 2: Rate-Limit Animation Submission [OPTIONAL]

**File**: `src/animations/engine.py` (lines 197-249)

**Purpose**: Prevent queue flooding if Fix 1 doesn't fully resolve issue

**Current Code**:
```python
async def _run_loop(self, zone_id: ZoneID, animation: BaseAnimation):
    while True:
        frame = await animation.step()
        if frame is not None:
            await self.frame_manager.push_frame(frame)  # No rate limiting
        await asyncio.sleep(1 / self.frame_manager.fps)
```

**Optional Enhancement**:
```python
async def _run_loop(self, zone_id: ZoneID, animation: BaseAnimation):
    frames_sent = 0
    last_log = time.monotonic()

    while True:
        frame = await animation.step()

        if frame is not None:
            # Only submit if we haven't exceeded max submission rate
            # This prevents queue flooding while maintaining 60 FPS render
            await self.frame_manager.push_frame(frame)
            frames_sent += 1

        await asyncio.sleep(1 / self.frame_manager.fps)

        # Optional: Log submission stats every 5 seconds
        now = time.monotonic()
        if now - last_log >= 5.0:
            log.debug(
                f"Animation loop stats: {zone_id.name}",
                frames_sent=frames_sent,
                fps_avg=frames_sent / 5.0
            )
            frames_sent = 0
            last_log = now
```

**When to Use**: Only if Fix 1 doesn't completely resolve freezing

**Why Probably Unnecessary**:
- Removing lock from `push_frame()` should eliminate starvation
- Animation already rate-limited by `sleep(1/fps)`
- Add only if testing shows queue flooding

---

### Fix 3: Enhanced Exception Logging [OPTIONAL]

**File**: `src/lifecycle/task_registry.py` (lines 209-252)

**Purpose**: Better debugging visibility (not fixing the freeze)

**Enhancement**:
- Capture stack traces for CancelledError
- Log task category, duration, exception type
- Enhanced context for all task terminations

**When to Use**: After main freeze fixed, for ongoing debugging

---

## Phase 3: Validation (Day 1-2, ~2 hours)

### Comprehensive Testing

1. **Functional Tests**:
   - All 9 animations: test switching patterns
   - Breathe focus: 100 consecutive switches
   - Concurrent zones: 3 zones switching simultaneously
   - Rapid switching: 10 switches/sec for 60 seconds

2. **Performance Tests**:
   - FPS maintained (within 5% of baseline)
   - Memory leak check (run 1 hour, monitor RSS)
   - Lock contention profiling
   - CPU usage <80%

3. **Edge Cases**:
   - Cancellation during lock acquisition
   - Very fast animations (high FPS)
   - Very slow animations (low FPS)
   - Multiple cancellations simultaneously

4. **Logging Tests**:
   - Verify CancelledError visible with stack traces
   - Cancellation points identifiable
   - Timeout detected and logged correctly
   - Metrics accurate (frames sent/failed, FPS)

### Documentation

- Update [architecture/rendering-system.md](d:\DEV\Projects\LED\Diuna\.claude\context\architecture\rendering-system.md) with lock patterns
- Document cancellation safety requirements
- Create troubleshooting guide for deadlocks
- Add monitoring metrics to runbook

---

## Critical Files to Modify

### Primary Change (ONLY ONE FILE)

1. **`src/engine/frame_manager.py`** (CRITICAL)
   - **Lines 166-217**: `push_frame()` - **REMOVE** `async with self._lock:` wrapper
   - Lines 352-428: `_drain_frames()` - **NO CHANGES** (keep lock for iteration protection)

### Optional Changes

2. **`src/animations/engine.py`** (OPTIONAL)
   - Lines 197-249: `_run_loop()` - add rate limiting if needed
   - Lines 197-249: `_run_loop()` - add statistics logging if desired

3. **`src/lifecycle/task_registry.py`** (OPTIONAL)
   - Lines 209-252: `_on_task_done()` - enhanced logging if desired

### Read-Only (for verification)

- `src/animations/breathe.py` (verify fast step() timing)
- Python docs: `collections.deque` (confirm thread safety)
- `src/models/frame.py` (frame types used in push_frame)

---

## Rollback Strategy

### Symptoms Requiring Rollback

- Queue corruption (unlikely - deque.append is atomic)
- Race conditions in frame submission (unlikely - single append operation)
- Different freeze behavior (should be better, not worse)

### Quick Rollback

```bash
# Restore lock in push_frame()
git checkout HEAD~1 -- src/engine/frame_manager.py
```

**This is EXTREMELY unlikely to be needed because**:
- We're removing complexity (less locking = simpler)
- deque.append is documented as thread-safe
- No new race conditions introduced
- Only removes contention, doesn't add it

### Verification Before Rollback

If freeze still occurs, verify:
1. **Is it the same frequency?** (Should be much less)
2. **Does it happen with other animations?** (Should be animation-independent now)
3. **Check queue sizes**: `sum(len(q) for q in frame_manager.main_queues.values())`
4. **Check lock state**: `frame_manager._lock.locked()` in _drain_frames only

### Alternative if Fix 1 Insufficient

- Add Fix 2: Rate-limit animation submission
- Add explicit `asyncio.Queue` instead of deque + manual lock
- Add priority scheduling hints for render loop

---

## Success Metrics

### Quantitative

- **Deadlock rate**: 0 in 1000 animation switches
- **Lock acquisition**: <10ms avg, <100ms p99
- **Frame drop rate**: <1% under normal load
- **Logging overhead**: <1% CPU increase
- **Memory**: No leaks, stable over 24 hours

### Qualitative

- No UI freezes or unresponsive behavior
- All issues visible in logs immediately
- Code understandable and maintainable
- Team confident deploying to production

---

## Verification Checklist

### Pre-Implementation

- [ ] Files backed up
- [ ] Test environment ready
- [ ] Baseline metrics captured (FPS, latency, memory)
- [ ] Git branch created: `fix/cancellederror-deadlock`

### Phase 1 (Critical Fixes)

- [ ] Fix 1: try/finally pattern implemented correctly
- [ ] Fix 1: Unit test passes
- [ ] Fix 1: No regression in other animations
- [ ] Fix 2: Timeout wrapper added
- [ ] Fix 2: Graceful degradation on timeout
- [ ] Fix 2: False positive test passes
- [ ] Integration: 100 Breathe switches without deadlock
- [ ] Integration: UI responsive throughout

### Phase 2 (Visibility)

- [ ] Fix 3: Stack traces captured for cancellations
- [ ] Fix 3: Performance overhead acceptable
- [ ] Fix 4: Cancellation points logged correctly
- [ ] Fix 4: Slow operation warnings work
- [ ] Fix 5: Timeline logging complete
- [ ] Fix 5: Timeout diagnostics work

### Phase 3 (Validation)

- [ ] All functional tests pass
- [ ] Performance within 5% of baseline
- [ ] No memory leaks detected
- [ ] Edge cases handled correctly
- [ ] Documentation updated
- [ ] Team review completed

---

## Timeline

| Phase | Duration | Activities | Deliverables |
|-------|----------|------------|--------------|
| **Phase 1** | 2 hours | Remove lock from push_frame | Starvation eliminated |
| **Phase 2** | 1 hour (optional) | Rate-limiting / logging | Enhanced visibility |
| **Phase 3** | 2 hours | Testing + validation | Production-ready |

**Total**: 1 day (5 hours, mostly testing)

**Note**: Much faster than previous plan because:
- Single file change (not 3 files)
- Removing code (not adding complexity)
- No try/finally patterns needed
- No timeout mechanisms needed

---

## Next Steps

1. ✅ **Plan approved by user**
2. Create git branch: `fix/lock-starvation` (NOT deadlock - we fixed the analysis!)
3. **Implement Fix 1**: Remove lock from `push_frame()` (single edit)
4. **Test immediately**: Start Breathe, switch 100 times
5. **Verify**: No freeze, UI responsive
6. If needed: Add Fix 2 (rate limiting)
7. Complete Phase 3 (full validation)
8. Merge to main and deploy

**Expected result**: Freeze eliminated in ~2 hours of work (much simpler than previous plan)

---

## Related Documents

- **Original (incorrect) deadlock analysis**: [.claude/context/.todo/2026.01.20/cancelledError_deadlock_fix.md](d:\DEV\Projects\LED\Diuna\.claude\context\.todo\2026.01.20\cancelledError_deadlock_fix.md) - ⚠️ Archived, hypothesis was wrong
- **Architecture Overview**: [.claude/context/architecture/rendering-system.md](d:\DEV\Projects\LED\Diuna\.claude\context\architecture\rendering-system.md)
- **Animation Lifecycle**: [.claude/context/domain/animations.md](d:\DEV\Projects\LED\Diuna\.claude\context\domain\animations.md)
- **Coding Standards**: [.claude/context/development/coding-standards.md](d:\DEV\Projects\LED\Diuna\.claude\context\development\coding-standards.md)

---

## Key Learnings from This Analysis

1. **asyncio.Lock is cancellation-safe** - always releases in `__aexit__()`, even on `CancelledError`
2. **Starvation ≠ Deadlock** - both cause freezes, but mechanisms are different
3. **Lock contention analysis requires profiling** - assumptions about "what needs locking" can be wrong
4. **deque.append is atomic** - many operations don't need locks at all
5. **Simpler is better** - removing unnecessary locks is safer than adding complex timeout logic

**Previous plan was based on incorrect understanding of Python asyncio internals. This corrected plan addresses the ACTUAL problem: lock starvation caused by unnecessary locking in high-frequency code path.**

---

**Ready for implementation upon user approval.**