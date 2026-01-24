# CancelledError Deadlock Bug - Implementation Plan

**Created**: 2026-01-20
**Priority**: CRITICAL
**Status**: Ready for Implementation

---

## Executive Summary

When switching to Breathe animation, a deadlock occurs in FrameManager's `_lock` causing complete UI freeze. The root cause is `CancelledError` propagating while holding the lock in `push_frame()`, preventing the render loop from ever acquiring it again in `_drain_frames()`.

**Impact**: Complete LED system freeze, unresponsive UI, no error visibility
**Trigger**: Animation task cancellation (especially Breathe due to timing)
**Fix Complexity**: 5 targeted changes, 2 CRITICAL

---

## Problem Summary

### Deadlock Mechanism

1. **Animation task running** (`AnimationEngine._run_loop`)
   - Calls `frame_manager.push_frame(frame)` at line 226
   - Enters `push_frame()` at line 166
   - **Acquires `self._lock`** via `async with self._lock:` at line 176

2. **Cancellation signal arrives** (from `AnimationEngine.stop_for_zone()`)
   - Task cancelled at line 148: `task.cancel()`
   - `CancelledError` raised inside `push_frame()` while lock is held
   - **Lock NEVER released** - `async with` context manager doesn't execute cleanup

3. **Render loop blocked forever** (`FrameManager._render_loop`)
   - Calls `_drain_frames()` at line 319
   - Tries to acquire lock at line 363: `async with self._lock:`
   - **Waits forever** for lock that will never be released
   - No frames rendered → LED preview frozen
   - No timeouts → permanent deadlock

### Why Breathe Animation is Affected Most

**File**: `src/animations/breathe.py`

**Characteristics**:
- **Synchronous `step()` method** (lines 44-84): Pure math calculations, no async delays
- **Fast execution**: Simple sine wave computation (~0.1ms)
- **Predictable timing**: Cancellation consistently arrives during `push_frame()`
- **High probability window**: Very narrow execution window increases chance of hitting the lock

**Contrast with other animations**:
- ColorFade, Snake, etc. have async operations spreading out the timing
- Longer `step()` methods reduce probability of being inside `push_frame()` during cancellation
- Random timing windows make deadlock less reproducible

---

## Root Cause Analysis

### The Lock Lifecycle Problem

**Normal Flow** (no cancellation):
```python
async def push_frame(self, frame):
    async with self._lock:        # 1. Acquire lock
        # ... process frame ...    # 2. Do work
        self.main_queues[...].append(msf)  # 3. Queue frame
    # 4. Lock released automatically
```

**Broken Flow** (with cancellation):
```python
async def push_frame(self, frame):
    async with self._lock:        # 1. Acquire lock ✓
        # ... process frame ...    # 2. Do work ✓
        # ❌ CancelledError raised HERE
        # 3. Context manager __aexit__ NEVER runs
        # 4. Lock NEVER released
```

**Why Context Manager Fails**:
- `CancelledError` is a special exception that bypasses normal cleanup in async contexts
- `async with` relies on `__aexit__` being called
- When cancellation happens, Python's async machinery propagates the exception immediately
- Lock remains in acquired state with no owner

### Evidence from Code

**FrameManager.push_frame** (lines 166-217):
```python
async def push_frame(self, frame):
    async with self._lock:  # ← PROBLEM: Lock acquired here
        # Lines 178-215: Frame processing
        # If CancelledError raised here, lock never released
        if isinstance(frame, SingleZoneFrame):
            msf = MainStripFrame(...)  # Can be cancelled here
            self.main_queues[msf.priority.value].append(msf)  # Or here
            return
        # ... similar for other frame types
```

**FrameManager._drain_frames** (lines 352-428):
```python
async def _drain_frames(self) -> Optional[MainStripFrame]:
    async with self._lock:  # ← BLOCKS FOREVER waiting for lock
        merged_updates = {}
        # ... frame merging logic never executes
```

**AnimationEngine._run_loop** (lines 197-249):
```python
async def _run_loop(self, zone_id: ZoneID, animation: BaseAnimation):
    try:
        while True:
            frame = await animation.step()  # Fast for Breathe
            if frame is not None:
                await self.frame_manager.push_frame(frame)  # ← Cancellation here
            await asyncio.sleep(1 / self.frame_manager.fps)
    except asyncio.CancelledError:
        log.debug(f"Animation task for {zone_id.name} canceled")  # ← Never logs!
```

---

## Impact Assessment

### What Breaks

1. **LED Preview Panel**: Completely frozen, no updates
2. **Animation Switching**: UI becomes unresponsive after first Breathe switch
3. **Error Visibility**: No stack trace, no error message, silent failure
4. **User Experience**: System appears hung, requires restart
5. **Debugging**: Impossible to diagnose without code-level inspection

### Symptoms Observed

- ✅ CancelledError occurs (confirmed by investigation)
- ✅ No exception logging (TaskRegistry not capturing)
- ✅ UI freeze (render loop blocked)
- ✅ Reproducible with Breathe animation
- ✅ Other animations show same bug but less frequently

### What Still Works

- Backend API (separate event loop)
- Config changes
- Non-animation LED operations (manual color sets)

---

## Fix Strategy

### Priority Classification

| Priority | Fix | Files | Impact | Risk |
|----------|-----|-------|--------|------|
| **CRITICAL** | Lock cleanup in push_frame | frame_manager.py | Prevents deadlock | Low |
| **CRITICAL** | Lock timeout in _drain_frames | frame_manager.py | Recovery mechanism | Low |
| **HIGH** | Exception logging in TaskRegistry | task_registry.py | Visibility | Very Low |
| **MEDIUM** | Animation loop logging | engine.py | Debugging aid | Very Low |
| **LOW** | stop_for_zone logging | engine.py | Process visibility | Very Low |

### Overall Approach

1. **Prevent deadlock**: Guarantee lock release even during cancellation
2. **Add safety net**: Timeout mechanism to detect and recover from deadlock
3. **Improve visibility**: Full stack traces for all exceptions
4. **Enhance debugging**: Better logging throughout cancellation lifecycle

---

## Implementation Plan

### Fix 1: Lock Cleanup in FrameManager.push_frame() [CRITICAL]

**File**: `d:\DEV\Projects\LED\Diuna\src\engine\frame_manager.py`
**Lines**: 166-217
**Priority**: CRITICAL (Prevents deadlock)

#### Current Problematic Code

```python
async def push_frame(self, frame):
    """
    Unified API endpoint.
    Accepts SingleZoneFrame / MultiZoneFrame / PixelFrame
    and wraps them into MainStripFrame for the queue system.
    """
    async with self._lock:  # ← PROBLEM: Lock not released on CancelledError
        # --- SingleZoneFrame ----------------------------------
        if isinstance(frame, SingleZoneFrame):
            msf = MainStripFrame(
                priority=frame.priority,
                ttl=frame.ttl,
                source=frame.source,
                partial=True,
                updates=cast(Dict[ZoneID, ZoneUpdateValue], {frame.zone_id: frame.color}),
            )
            self.main_queues[msf.priority.value].append(msf)
            return

        # ... similar for MultiZoneFrame, PixelFrame ...

        raise TypeError(f"Unsupported frame type: {type(frame)}")
```

#### Proposed Fix

```python
async def push_frame(self, frame):
    """
    Unified API endpoint.
    Accepts SingleZoneFrame / MultiZoneFrame / PixelFrame
    and wraps them into MainStripFrame for the queue system.

    CRITICAL: Uses try/finally to guarantee lock release even during cancellation.
    Without this, CancelledError during frame processing causes permanent deadlock.
    """
    # Explicitly acquire lock with proper cancellation handling
    await self._lock.acquire()

    try:
        # --- SingleZoneFrame ----------------------------------
        if isinstance(frame, SingleZoneFrame):
            msf = MainStripFrame(
                priority=frame.priority,
                ttl=frame.ttl,
                source=frame.source,
                partial=True,
                updates=cast(Dict[ZoneID, ZoneUpdateValue], {frame.zone_id: frame.color}),
            )
            self.main_queues[msf.priority.value].append(msf)
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
            self.main_queues[msf.priority.value].append(msf)
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
            self.main_queues[msf.priority.value].append(msf)
            return

        raise TypeError(f"Unsupported frame type: {type(frame)}")

    except asyncio.CancelledError:
        # Task was cancelled while processing frame
        # Log this explicitly since it's a critical path
        log.debug(
            f"push_frame cancelled during frame processing",
            frame_type=type(frame).__name__,
            zone_id=getattr(frame, 'zone_id', None)
        )
        # Re-raise to propagate cancellation
        raise

    except Exception as e:
        # Unexpected error during frame processing
        log.error(
            f"push_frame error: {e}",
            frame_type=type(frame).__name__,
            exc_info=True
        )
        # Don't swallow the exception
        raise

    finally:
        # CRITICAL: Always release lock, even during cancellation
        # This prevents deadlock when animation tasks are cancelled
        self._lock.release()
```

#### Why This Works

1. **Explicit lock management**: `acquire()` + `try/finally/release()` pattern guarantees cleanup
2. **CancelledError handling**: Exception caught, logged, then re-raised (proper propagation)
3. **finally block**: Executes even during cancellation, releasing lock
4. **No behavior change**: Normal operation identical, only cancellation path improved
5. **Type safety preserved**: All frame types handled identically

#### Testing Strategy

1. **Unit test**: Mock cancellation during `push_frame()`, verify lock released
2. **Integration test**: Start Breathe animation, cancel immediately, verify no deadlock
3. **Stress test**: Rapid animation switches (10/sec) for 60 seconds
4. **Regression test**: Verify normal frame submission still works
5. **Lock state test**: Check `_lock.locked()` before/after cancellation

**Test Code Snippet**:
```python
async def test_push_frame_cancellation_releases_lock():
    """Verify lock is released even when push_frame is cancelled."""
    frame_manager = FrameManager(fps=60)

    # Create a frame
    frame = SingleZoneFrame(
        zone_id=ZoneID.ZONE_1,
        color=Color.red(),
        priority=FramePriority.ANIMATION,
        source=FrameSource.ANIMATION,
        ttl=0.1
    )

    # Start push_frame and cancel it mid-execution
    task = asyncio.create_task(frame_manager.push_frame(frame))
    await asyncio.sleep(0.001)  # Let it acquire lock
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify lock is released
    assert not frame_manager._lock.locked(), "Lock should be released after cancellation"

    # Verify we can acquire lock again
    async with frame_manager._lock:
        pass  # Should not block
```

---

### Fix 2: Lock Timeout in FrameManager._drain_frames() [CRITICAL]

**File**: `d:\DEV\Projects\LED\Diuna\src\engine\frame_manager.py`
**Lines**: 352-428
**Priority**: CRITICAL (Recovery mechanism)

#### Current Problematic Code

```python
async def _drain_frames(self) -> Optional[MainStripFrame]:
    """
    Drain and merge frames from all priority queues.
    """
    async with self._lock:  # ← BLOCKS FOREVER if lock not released
        merged_updates = {}
        highest_priority = None
        ttl = 0.0
        source = None

        # ... frame merging logic (lines 369-427)

        return MainStripFrame(...)
```

#### Proposed Fix

```python
async def _drain_frames(self) -> Optional[MainStripFrame]:
    """
    Drain and merge frames from all priority queues.

    CRITICAL: Uses timeout to detect deadlock conditions.
    If lock cannot be acquired within 1 second, logs error and returns None
    to prevent permanent render loop freeze.

    This is a safety net for the push_frame() lock release fix.
    """
    # Attempt to acquire lock with timeout
    try:
        async with asyncio.timeout(1.0):  # 1 second timeout
            async with self._lock:
                merged_updates = {}
                highest_priority = None
                ttl = 0.0
                source = None

                # 1. Always collect ANIMATION first (base layer - continuous animations)
                anim_queue = self.main_queues.get(FramePriority.ANIMATION.value)
                if anim_queue:
                    while anim_queue:
                        frame = anim_queue.popleft()
                        if frame.is_expired():
                            continue
                        for zid, val in frame.updates.items():
                            merged_updates[zid] = val
                        ttl = max(ttl, frame.ttl)
                        source = source or frame.source
                        highest_priority = FramePriority.ANIMATION

                # 2. Apply overlays (PULSE, DEBUG, TRANSITION - higher priority than ANIMATION)
                for priority_value in sorted(self.main_queues.keys(), reverse=True):
                    if priority_value <= FramePriority.ANIMATION.value:
                        continue

                    queue = self.main_queues[priority_value]
                    while queue:
                        frame = queue.popleft()
                        if frame.is_expired():
                            continue
                        for zid, val in frame.updates.items():
                            merged_updates[zid] = val
                        ttl = max(ttl, frame.ttl)
                        source = source or frame.source
                        highest_priority = frame.priority

                # 3. Fill gaps with lower priorities (MANUAL for static zones, IDLE fallback)
                for priority_value in sorted(self.main_queues.keys()):
                    if priority_value >= FramePriority.ANIMATION.value:
                        continue

                    queue = self.main_queues[priority_value]
                    while queue:
                        frame = queue.popleft()
                        if frame.is_expired():
                            continue
                        for zid, val in frame.updates.items():
                            if zid not in merged_updates:
                                merged_updates[zid] = val
                        ttl = max(ttl, frame.ttl)
                        if source is None:
                            source = frame.source
                        if highest_priority is None:
                            highest_priority = frame.priority

                if not merged_updates or not source:
                    return None

                return MainStripFrame(
                    priority=highest_priority or FramePriority.ANIMATION,
                    ttl=ttl or 0.1,
                    source=source,
                    partial=True,
                    updates=merged_updates,
                )

    except asyncio.TimeoutError:
        # Lock acquisition timed out - likely deadlock
        log.error(
            "DEADLOCK DETECTED: _drain_frames could not acquire lock within 1.0s",
            lock_locked=self._lock.locked(),
            pending_frames=sum(len(q) for q in self.main_queues.values())
        )

        # Increment dropped frames counter
        self.dropped_frames += 1

        # Return None to skip this frame
        # Render loop will continue and retry next frame
        return None
```

#### Why This Works

1. **Timeout protection**: `asyncio.timeout(1.0)` prevents infinite blocking
2. **Graceful degradation**: Returns `None` on timeout, render loop continues
3. **Visibility**: Logs deadlock with diagnostic info (lock state, queue sizes)
4. **Non-destructive**: Doesn't break the lock or corrupt state
5. **Recovery**: Next frame attempt may succeed if lock released by then

#### Alternative: Try-Lock Pattern (Considered but Rejected)

```python
# Alternative approach - non-blocking lock acquisition
if self._lock.locked():
    log.warn("Lock busy, skipping frame drain")
    return None

async with self._lock:
    # ... frame merging logic
```

**Why Rejected**:
- Doesn't detect deadlock, just busy lock
- Could skip many frames unnecessarily
- No diagnostic information
- Timeout approach provides better visibility

#### Testing Strategy

1. **Deadlock simulation**: Hold lock artificially, verify timeout triggers
2. **Recovery test**: After timeout, verify render loop continues
3. **Performance test**: Measure timeout overhead (should be negligible)
4. **False positive test**: High-load scenarios shouldn't trigger timeout
5. **Metrics test**: Verify `dropped_frames` increments on timeout

**Test Code Snippet**:
```python
async def test_drain_frames_timeout_recovery():
    """Verify _drain_frames recovers from deadlock via timeout."""
    frame_manager = FrameManager(fps=60)

    # Simulate deadlock by holding lock
    await frame_manager._lock.acquire()

    # Try to drain frames (should timeout)
    start = time.monotonic()
    result = await frame_manager._drain_frames()
    elapsed = time.monotonic() - start

    # Verify timeout occurred
    assert result is None, "Should return None on timeout"
    assert 0.9 < elapsed < 1.2, f"Should timeout around 1.0s, got {elapsed}s"
    assert frame_manager.dropped_frames > 0, "Should increment dropped_frames"

    # Release lock and verify recovery
    frame_manager._lock.release()

    # Next drain should work
    result = await frame_manager._drain_frames()
    # result may be None (no frames), but shouldn't timeout
```

---

### Fix 3: Exception Logging in TaskRegistry [HIGH]

**File**: `d:\DEV\Projects\LED\Diuna\src\lifecycle\task_registry.py`
**Lines**: 209-252
**Priority**: HIGH (Visibility)

#### Current Problematic Code

```python
def _on_task_done(self, task: asyncio.Task) -> None:
    """Internal callback whenever a task finishes."""
    record = self._get_record_by_task(task)
    if record is None:
        return

    task_label = f"[Task {record.info.id}] {record.info.description}"

    # Record finish time
    now = datetime.now(timezone.utc)
    record.finished_at = now.isoformat()
    record.finished_timestamp = now.timestamp()

    if task.cancelled():
        record.cancelled = True
        log.debug(f"{task_label} - Cancelled")  # ← No stack trace
        # ... broadcast event
    else:
        exc = task.exception()
        if exc:
            record.finished_with_error = exc
            log.error(
                f"{task_label} - FAILED: {exc}",
                exc_info=True  # ← Only logs for exceptions, not cancellations
            )
```

#### Proposed Fix

```python
def _on_task_done(self, task: asyncio.Task) -> None:
    """
    Internal callback whenever a task finishes.

    Enhanced to provide full stack traces for all task terminations,
    including cancellations. This is critical for debugging deadlock
    scenarios where CancelledError is raised.
    """
    record = self._get_record_by_task(task)
    if record is None:
        return

    task_label = f"[Task {record.info.id}] {record.info.description}"

    # Record finish time
    now = datetime.now(timezone.utc)
    record.finished_at = now.isoformat()
    record.finished_timestamp = now.timestamp()

    if task.cancelled():
        record.cancelled = True

        # ENHANCED: Try to get cancellation stack trace
        # CancelledError doesn't provide exc_info, so we capture the stack manually
        try:
            # Attempt to extract where cancellation occurred
            # This uses the task's internal state to get the cancellation point
            import sys
            import traceback

            # Get stack from task if available (Python 3.9+)
            stack = None
            if hasattr(task, 'get_stack'):
                try:
                    frames = task.get_stack()
                    if frames:
                        stack = ''.join(traceback.format_list(
                            traceback.extract_stack(frame) for frame in frames
                        ))
                except Exception:
                    pass

            if stack:
                log.info(
                    f"{task_label} - Cancelled",
                    category=record.info.category.name,
                    duration=record.get_duration(),
                    stack_trace=stack
                )
            else:
                log.info(
                    f"{task_label} - Cancelled",
                    category=record.info.category.name,
                    duration=record.get_duration()
                )
        except Exception as e:
            # Fallback to simple logging if stack extraction fails
            log.info(
                f"{task_label} - Cancelled (stack unavailable: {e})",
                category=record.info.category.name,
                duration=record.get_duration()
            )

        # Broadcast cancellation event
        try:
            asyncio.create_task(self._broadcast_task_event("task:cancelled", record.to_dict()))
        except RuntimeError:
            pass

    else:
        exc = task.exception()
        if exc:
            record.finished_with_error = exc

            # ENHANCED: Include full context for all exceptions
            log.error(
                f"{task_label} - FAILED: {type(exc).__name__}: {exc}",
                category=record.info.category.name,
                exception_type=type(exc).__name__,
                duration=record.get_duration(),
                exc_info=True  # Full stack trace
            )

            # Broadcast failure event
            try:
                asyncio.create_task(self._broadcast_task_event("task:failed", record.to_dict()))
            except RuntimeError:
                pass
        else:
            record.finished_return = task.result()
            log.info(
                f"{task_label} - Completed successfully",
                category=record.info.category.name,
                duration=record.get_duration()
            )

            # Broadcast completion event
            try:
                asyncio.create_task(self._broadcast_task_event("task:completed", record.to_dict()))
            except RuntimeError:
                pass
```

#### Why This Works

1. **Stack trace capture**: Uses `task.get_stack()` to extract cancellation point
2. **Graceful fallback**: If stack unavailable, logs without it (no failure)
3. **Enhanced context**: Includes task category, duration in all log messages
4. **Type visibility**: Shows exception type name in error messages
5. **Backward compatible**: Doesn't change API or behavior

#### Testing Strategy

1. **Cancellation test**: Cancel task, verify stack trace logged
2. **Exception test**: Task with exception, verify full traceback
3. **Normal completion**: Verify successful completion still logged
4. **Stack unavailable**: Simulate `get_stack()` failure, verify fallback
5. **Performance test**: Verify logging overhead acceptable (<1ms)

---

### Fix 4: Animation Loop Logging [MEDIUM]

**File**: `d:\DEV\Projects\LED\Diuna\src\animations\engine.py`
**Lines**: 197-249
**Priority**: MEDIUM (Debugging aid)

#### Current Problematic Code

```python
async def _run_loop(self, zone_id: ZoneID, animation: BaseAnimation):
    """Run an animation until stopped."""

    log.info(f"_run_loop started for {zone_id.name}")

    frames_sent = 0
    last_log = time.monotonic()

    try:
        while True:
            frame = await animation.step()

            # ... FPS logging (commented out) ...

            if frame is not None:
                await self.frame_manager.push_frame(frame)
                frames_sent += 1

            await asyncio.sleep(1 / self.frame_manager.fps)

    except asyncio.CancelledError:
        log.debug(f"Animation task for {zone_id.name} canceled")  # ← Minimal info

    except Exception as e:
        log.error(
            f"Animation error on {zone_id.name}: {e}",
            exc_info=True
        )

    finally:
        log.info(
            f"Animation task for {zone_id.name} finished, "
            f"frames sent: {frames_sent}"
        )
```

#### Proposed Fix

```python
async def _run_loop(self, zone_id: ZoneID, animation: BaseAnimation):
    """
    Run an animation until stopped.

    Animation loop:
    - animation.step() decides WHEN a frame exists
    - engine forwards frames immediately
    - renderer (FrameManager) controls FPS

    Enhanced with detailed logging for debugging cancellation deadlocks.
    """

    log.info(
        f"Animation loop started",
        zone=zone_id.name,
        animation=type(animation).__name__,
        fps=self.frame_manager.fps
    )

    frames_sent = 0
    frames_failed = 0
    last_log = time.monotonic()
    start_time = time.monotonic()

    try:
        while True:
            # Generate next frame
            frame_start = time.perf_counter()
            frame = await animation.step()
            frame_duration = time.perf_counter() - frame_start

            now = time.monotonic()
            if now - last_log >= 5.0:  # Log every 5 seconds
                log.debug(
                    "Animation loop stats",
                    zone=zone_id.name,
                    frames_sent=frames_sent,
                    frames_failed=frames_failed,
                    fps_avg=frames_sent / 5.0,
                    frame_time_avg_ms=frame_duration * 1000
                )
                frames_sent = 0
                frames_failed = 0
                last_log = now

            if frame is not None:
                try:
                    # Submit frame to FrameManager
                    push_start = time.perf_counter()
                    await self.frame_manager.push_frame(frame)
                    push_duration = time.perf_counter() - push_start

                    frames_sent += 1

                    # Warn if push_frame takes too long (potential lock contention)
                    if push_duration > 0.1:  # 100ms threshold
                        log.warn(
                            "Slow push_frame detected",
                            zone=zone_id.name,
                            duration_ms=push_duration * 1000,
                            frame_type=type(frame).__name__
                        )

                except asyncio.CancelledError:
                    # Cancellation during push_frame - this is the critical path
                    log.warn(
                        "Animation loop cancelled during push_frame",
                        zone=zone_id.name,
                        frames_sent=frames_sent,
                        frames_failed=frames_failed,
                        elapsed_sec=time.monotonic() - start_time
                    )
                    raise  # Re-raise to propagate cancellation

                except Exception as e:
                    frames_failed += 1
                    log.error(
                        f"Failed to push frame for {zone_id.name}: {e}",
                        exc_info=True
                    )
                    # Continue animation loop despite push failure

            await asyncio.sleep(1 / self.frame_manager.fps)

    except asyncio.CancelledError:
        # Top-level cancellation (outside push_frame)
        log.info(
            "Animation loop cancelled",
            zone=zone_id.name,
            frames_sent=frames_sent,
            frames_failed=frames_failed,
            elapsed_sec=time.monotonic() - start_time,
            cancellation_point="main_loop"
        )
        # Don't re-raise - stop_for_zone expects clean exit

    except Exception as e:
        log.error(
            f"Animation loop error on {zone_id.name}: {e}",
            frames_sent=frames_sent,
            frames_failed=frames_failed,
            elapsed_sec=time.monotonic() - start_time,
            exc_info=True
        )

    finally:
        # NOTE: Do NOT acquire lock here - would cause deadlock with stop_for_zone()
        # The caller is responsible for cleaning up task dictionaries

        total_duration = time.monotonic() - start_time
        avg_fps = frames_sent / total_duration if total_duration > 0 else 0

        log.info(
            "Animation loop finished",
            zone=zone_id.name,
            frames_sent=frames_sent,
            frames_failed=frames_failed,
            duration_sec=total_duration,
            avg_fps=avg_fps
        )
```

#### Why This Works

1. **Cancellation point visibility**: Logs exactly where cancellation occurred
2. **Performance metrics**: Frame timing helps identify slow operations
3. **Lock contention detection**: Warns if `push_frame()` takes >100ms
4. **Detailed statistics**: Frames sent/failed, duration, FPS
5. **Non-intrusive**: Doesn't affect normal operation, only adds logging

#### Testing Strategy

1. **Normal operation**: Verify logging doesn't impact FPS
2. **Cancellation test**: Verify cancellation point logged correctly
3. **Slow push test**: Artificially delay `push_frame()`, verify warning
4. **Exception test**: Inject exception, verify error logging
5. **Performance test**: Measure logging overhead (<0.1ms per frame)

---

### Fix 5: stop_for_zone() Logging [LOW]

**File**: `d:\DEV\Projects\LED\Diuna\src\animations\engine.py`
**Lines**: 133-167
**Priority**: LOW (Process visibility)

#### Current Problematic Code

```python
async def stop_for_zone(self, zone_id: ZoneID):
    """Stop animation for a single zone."""

    log.info(f"Stopping animation on zone {zone_id.name}")

    # Extract task without holding lock during await
    task = None
    async with self._lock:
        task = self.tasks.pop(zone_id, None)
        self.active_anim_ids.pop(zone_id, None)
        self.active_animations.pop(zone_id, None)

    if not task:
        return

    task.cancel()

    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.CancelledError:
        pass
    except asyncio.TimeoutError:
        log.warn(f"Animation task for {zone_id.name} did not respond to cancellation")

    # ... cleanup and event publishing

    log.info(f"Stopped animation on zone {zone_id.name}")
```

#### Proposed Fix

```python
async def stop_for_zone(self, zone_id: ZoneID):
    """
    Stop animation for a single zone.

    Enhanced with detailed logging to track cancellation process and
    detect if tasks fail to respond to cancellation signals.
    """

    animation_id = self.active_anim_ids.get(zone_id)
    log.info(
        "Stopping animation",
        zone=zone_id.name,
        animation=animation_id.name if animation_id else "unknown"
    )

    # Extract task without holding lock during await
    task = None
    cancel_start = time.monotonic()

    async with self._lock:
        task = self.tasks.pop(zone_id, None)
        self.active_anim_ids.pop(zone_id, None)
        self.active_animations.pop(zone_id, None)

    if not task:
        log.debug(
            "No active animation to stop",
            zone=zone_id.name
        )
        return

    # Send cancellation signal
    log.debug(
        "Sending cancellation signal",
        zone=zone_id.name,
        task_done=task.done(),
        task_cancelled=task.cancelled()
    )

    task.cancel()

    # Wait for task to complete with timeout
    try:
        await asyncio.wait_for(task, timeout=1.0)
        cancel_duration = time.monotonic() - cancel_start

        log.debug(
            "Animation task completed",
            zone=zone_id.name,
            duration_ms=cancel_duration * 1000
        )

    except asyncio.CancelledError:
        # Expected - task was cancelled successfully
        cancel_duration = time.monotonic() - cancel_start
        log.debug(
            "Animation task cancelled successfully",
            zone=zone_id.name,
            duration_ms=cancel_duration * 1000
        )

    except asyncio.TimeoutError:
        # Task did not respond to cancellation within 1 second
        # This may indicate a deadlock or blocking operation
        log.error(
            "Animation task did not respond to cancellation",
            zone=zone_id.name,
            timeout_sec=1.0,
            task_done=task.done(),
            task_cancelled=task.cancelled()
        )

        # Try to get task state for debugging
        try:
            if hasattr(task, 'get_stack'):
                frames = task.get_stack()
                if frames:
                    import traceback
                    stack = ''.join(traceback.format_list(
                        traceback.extract_stack(frame) for frame in frames
                    ))
                    log.error(
                        "Stuck task stack trace",
                        zone=zone_id.name,
                        stack=stack
                    )
        except Exception as e:
            log.debug(f"Could not extract task stack: {e}")

    # Clean up state (redundant but defensive)
    async with self._lock:
        self.active_anim_ids.pop(zone_id, None)
        self.active_animations.pop(zone_id, None)

    # Publish animation stopped event
    try:
        await self.event_bus.publish(
            AnimationStoppedEvent(zone_id=zone_id)
        )
    except Exception as e:
        log.error(f"Failed to publish AnimationStoppedEvent: {e}")

    total_duration = time.monotonic() - cancel_start
    log.info(
        "Animation stopped",
        zone=zone_id.name,
        total_duration_ms=total_duration * 1000
    )
```

#### Why This Works

1. **Timeline visibility**: Logs each step of cancellation process
2. **Timeout detection**: Enhanced logging when task doesn't respond
3. **Stack trace on hang**: Attempts to capture where task is stuck
4. **Defensive cleanup**: Ensures state cleaned even on timeout
5. **Performance tracking**: Measures how long cancellation takes

#### Testing Strategy

1. **Normal stop**: Verify logs show clean cancellation
2. **Timeout test**: Simulate stuck task, verify enhanced logging
3. **Stack extraction**: Verify stack trace captured on timeout
4. **Performance test**: Verify typical cancellation <50ms
5. **Concurrent stops**: Multiple zones, verify no interference

---

## Migration Plan

### Phase 1: Critical Fixes [Day 1]

**Goal**: Prevent and recover from deadlock

1. **Fix 1: Lock cleanup in push_frame()** [2 hours]
   - Implement try/finally pattern
   - Add CancelledError handling
   - Write unit tests
   - Test with Breathe animation
   - Verify no regressions in other animations

2. **Fix 2: Lock timeout in _drain_frames()** [1 hour]
   - Add asyncio.timeout() wrapper
   - Implement timeout logging
   - Test timeout recovery
   - Verify no false positives under load

3. **Integration Testing** [2 hours]
   - Rapid animation switching (Breathe focus)
   - Stress test: 100 switches without deadlock
   - Monitor lock state throughout
   - Verify LED preview stays responsive
   - Check metrics: dropped_frames acceptable

**Success Criteria**:
- ✅ No deadlock after 100 Breathe animation switches
- ✅ UI remains responsive at all times
- ✅ Lock always released within 100ms
- ✅ Render loop never freezes

---

### Phase 2: Visibility Improvements [Day 2]

**Goal**: Make future issues visible immediately

4. **Fix 3: TaskRegistry exception logging** [2 hours]
   - Implement stack trace capture
   - Add enhanced context to logs
   - Test cancellation visibility
   - Verify performance acceptable

5. **Fix 4: Animation loop logging** [1 hour]
   - Add detailed loop metrics
   - Implement cancellation point logging
   - Add slow operation warnings
   - Test performance impact

6. **Fix 5: stop_for_zone() logging** [1 hour]
   - Enhance cancellation timeline logging
   - Add timeout diagnostics
   - Implement stack trace on hang
   - Test with various scenarios

**Success Criteria**:
- ✅ All CancelledErrors visible in logs with context
- ✅ Can identify exact cancellation point
- ✅ Performance impact <1% overhead
- ✅ Timeout issues detected immediately

---

### Phase 3: Validation [Day 3]

**Goal**: Ensure production readiness

7. **Comprehensive Testing** [4 hours]
   - All animations: test switching patterns
   - Load testing: sustained high-frequency switching
   - Edge cases: rapid start/stop, concurrent zones
   - Memory leak check: run for 1 hour
   - Performance profiling: verify no slowdown

8. **Documentation** [2 hours]
   - Update architecture docs with lock patterns
   - Document cancellation safety requirements
   - Add troubleshooting guide for deadlocks
   - Create runbook for monitoring metrics

**Success Criteria**:
- ✅ All tests pass (unit, integration, stress)
- ✅ No memory leaks detected
- ✅ Performance within 5% of baseline
- ✅ Documentation complete and accurate

---

## Verification Checklist

### Pre-Implementation
- [ ] All 4 files backed up
- [ ] Test environment prepared
- [ ] Baseline metrics captured (FPS, latency)
- [ ] Git branch created: `fix/cancellederror-deadlock`

### During Implementation

**Fix 1: push_frame() lock cleanup**
- [ ] try/finally pattern implemented
- [ ] CancelledError caught and re-raised
- [ ] Lock always released (verified in debugger)
- [ ] Unit test passes
- [ ] No regression in normal operation

**Fix 2: _drain_frames() timeout**
- [ ] asyncio.timeout(1.0) wrapper added
- [ ] Timeout returns None gracefully
- [ ] Error logging includes diagnostics
- [ ] dropped_frames increments correctly
- [ ] False positive test passes

**Fix 3: TaskRegistry logging**
- [ ] Stack trace captured for cancellations
- [ ] Enhanced context in all log messages
- [ ] Fallback works if stack unavailable
- [ ] Performance overhead acceptable
- [ ] All task types logged correctly

**Fix 4: Animation loop logging**
- [ ] Cancellation point logged
- [ ] Performance metrics included
- [ ] Slow operation warnings work
- [ ] Statistics accurate
- [ ] No FPS impact

**Fix 5: stop_for_zone() logging**
- [ ] Timeline logging complete
- [ ] Timeout diagnostics work
- [ ] Stack trace on hang captured
- [ ] Defensive cleanup runs
- [ ] Event publishing still works

### Post-Implementation

**Functional Tests**
- [ ] Breathe animation: no deadlock after 100 switches
- [ ] All animations: no deadlock after 10 switches each
- [ ] Concurrent zones: 3 zones switching simultaneously
- [ ] Rapid switching: 10 switches/sec for 60 sec
- [ ] UI responsive throughout all tests

**Performance Tests**
- [ ] FPS maintained (within 5% of baseline)
- [ ] Latency acceptable (<50ms)
- [ ] Memory stable (no leaks)
- [ ] CPU usage reasonable (<80%)
- [ ] Lock contention minimal

**Logging Tests**
- [ ] CancelledError visible in logs
- [ ] Stack traces present
- [ ] Cancellation points identified
- [ ] Timeout detected and logged
- [ ] Metrics accurate

**Edge Case Tests**
- [ ] Cancellation during lock acquisition
- [ ] Cancellation during frame processing
- [ ] Multiple cancellations simultaneously
- [ ] Very fast animations (high FPS)
- [ ] Very slow animations (low FPS)

---

## Rollback Strategy

### Symptoms Indicating Rollback Needed

1. **Performance degradation**: FPS drops >10%
2. **New deadlocks**: Introduced by fixes
3. **Excessive logging**: Disk space issues
4. **False timeouts**: Normal operations timing out
5. **Exception handling broken**: Other exceptions not caught

### Rollback Procedure

#### Immediate Rollback (if critical)
```bash
# Revert all changes
git checkout HEAD~1 -- src/engine/frame_manager.py
git checkout HEAD~1 -- src/animations/engine.py
git checkout HEAD~1 -- src/lifecycle/task_registry.py

# Restart application
systemctl restart led-control
```

#### Selective Rollback (if specific fix problematic)

**Rollback Fix 1 (push_frame)**:
```python
# Revert to async with pattern
async def push_frame(self, frame):
    async with self._lock:
        # ... original code
```

**Rollback Fix 2 (_drain_frames)**:
```python
# Remove timeout wrapper
async def _drain_frames(self) -> Optional[MainStripFrame]:
    async with self._lock:
        # ... original code
```

**Rollback Fixes 3-5 (logging)**:
- Simply comment out enhanced logging
- Minimal risk - doesn't affect logic

### Contingency Plans

#### Plan A: Timeout Too Short
**Symptom**: False positives under load
**Fix**: Increase timeout from 1.0s to 2.0s or 5.0s
**Test**: Run load test to find optimal value

#### Plan B: Logging Overhead Too High
**Symptom**: FPS drops, CPU spikes
**Fix**: Reduce logging frequency or disable debug logs
**Test**: Profile with and without logging

#### Plan C: Lock Release Still Failing
**Symptom**: Deadlock persists despite Fix 1
**Fix**: Investigate async context manager implementation
**Alternative**: Use threading.Lock instead of asyncio.Lock

---

## Risk Assessment

### Low Risk (Safe to implement)
- ✅ Fix 3: TaskRegistry logging (no logic changes)
- ✅ Fix 4: Animation loop logging (no logic changes)
- ✅ Fix 5: stop_for_zone() logging (no logic changes)

### Medium Risk (Test thoroughly)
- ⚠️ Fix 2: _drain_frames() timeout (adds new error path)
  - **Mitigation**: Conservative timeout (1.0s), graceful None return
  - **Test**: Load testing to rule out false positives

### High Risk (Requires validation)
- ⚠️⚠️ Fix 1: push_frame() lock pattern (core rendering path)
  - **Mitigation**: Extensive unit and integration testing
  - **Test**: All animations, all frame types, rapid switching
  - **Fallback**: Easy to revert if issues arise

### Overall Risk: MEDIUM
- Most critical fix (Fix 1) is well-understood pattern
- try/finally is standard Python idiom for resource cleanup
- All fixes are additive (no removals)
- Rollback is straightforward

---

## Expected Outcomes

### Immediate (After Phase 1)
- ✅ No deadlock with Breathe animation
- ✅ UI remains responsive during animation switches
- ✅ Lock always released within 100ms
- ✅ System recovers from any deadlock within 1 second

### Short-term (After Phase 2)
- ✅ All task failures visible in logs
- ✅ Cancellation points identifiable
- ✅ Performance monitoring in place
- ✅ Early warning for lock contention

### Long-term (After Phase 3)
- ✅ Production-ready system
- ✅ Comprehensive test coverage
- ✅ Documentation complete
- ✅ Monitoring and alerting configured

---

## Success Metrics

### Quantitative
- **Deadlock rate**: 0 occurrences in 1000 animation switches
- **Lock acquisition time**: <10ms average, <100ms p99
- **Frame drop rate**: <1% under normal load
- **Logging overhead**: <1% CPU increase
- **Memory usage**: No leaks, stable over 24 hours

### Qualitative
- **User experience**: No freezes or unresponsive UI
- **Debugging**: Issues visible in logs immediately
- **Maintenance**: Code is understandable and maintainable
- **Confidence**: Team confident deploying to production

---

## Next Steps

1. **Review this plan** with team
2. **Approve implementation** strategy
3. **Create git branch**: `fix/cancellederror-deadlock`
4. **Begin Phase 1**: Implement critical fixes
5. **Daily standup**: Share progress and blockers
6. **Complete testing**: Run full verification checklist
7. **Merge to main**: After all tests pass
8. **Deploy**: Monitor metrics closely
9. **Document lessons learned**: Update coding standards

---

## Related Documentation

- `.claude/context/architecture/rendering-system.md` - FrameManager architecture
- `.claude/context/domain/animations.md` - Animation lifecycle
- `.claude/context/technical/performance.md` - Performance requirements
- `.claude/context/development/coding-standards.md` - Code style rules

---

## Appendix A: Deadlock Timeline

**Example sequence showing exact deadlock mechanism:**

```
T=0.000s  [Animation Task] Enters _run_loop()
T=0.016s  [Animation Task] Calls animation.step() (Breathe)
T=0.017s  [Animation Task] step() returns SingleZoneFrame
T=0.017s  [Animation Task] Calls frame_manager.push_frame(frame)
T=0.017s  [Animation Task] Enters push_frame()
T=0.018s  [Animation Task] Acquires _lock via async with
T=0.018s  [Animation Task] Creates MainStripFrame
T=0.018s  [Stop Command]  User switches animation
T=0.019s  [Stop Command]  Calls stop_for_zone()
T=0.019s  [Stop Command]  Calls task.cancel()
T=0.019s  [Animation Task] ❌ CancelledError raised inside push_frame()
T=0.019s  [Animation Task] ❌ Lock still held (async with __aexit__ not reached)
T=0.019s  [Animation Task] Task terminates
T=0.020s  [Render Loop]    Calls _drain_frames()
T=0.020s  [Render Loop]    ⏳ Tries to acquire _lock
T=0.020s  [Render Loop]    ⏳ BLOCKS FOREVER (lock orphaned)
T=1.000s  [Render Loop]    ⏳ Still waiting...
T=5.000s  [Render Loop]    ⏳ Still waiting...
T=∞       [DEADLOCK]       System frozen, manual restart required
```

---

## Appendix B: Lock State Diagram

**Normal Operation (no cancellation)**:
```
┌─────────────────────────────────────────┐
│  push_frame()                           │
│                                         │
│  async with self._lock:   ← acquire   │
│      [frame processing]                 │
│      self.main_queues[...].append(msf) │
│  [end of with block]      ← release   │
└─────────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────┐
│  _drain_frames()                        │
│                                         │
│  async with self._lock:   ← acquire ✓ │
│      [frame merging]                    │
│      return MainStripFrame(...)         │
│  [end of with block]      ← release   │
└─────────────────────────────────────────┘
```

**Broken Operation (with cancellation)**:
```
┌─────────────────────────────────────────┐
│  push_frame()                           │
│                                         │
│  async with self._lock:   ← acquire   │
│      [frame processing]                 │
│      ❌ CancelledError HERE            │
│  [with block NEVER exits]  ← no release│
└─────────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────┐
│  _drain_frames()                        │
│                                         │
│  async with self._lock:   ← ⏳ BLOCKS  │
│      [NEVER REACHED]                    │
└─────────────────────────────────────────┘
```

**Fixed Operation (with try/finally)**:
```
┌─────────────────────────────────────────┐
│  push_frame()                           │
│                                         │
│  await self._lock.acquire() ← acquire │
│  try:                                   │
│      [frame processing]                 │
│      ❌ CancelledError HERE            │
│  finally:                               │
│      self._lock.release()  ← release ✓│
└─────────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────┐
│  _drain_frames()                        │
│                                         │
│  async with self._lock:   ← acquire ✓ │
│      [frame merging]                    │
│      return MainStripFrame(...)         │
└─────────────────────────────────────────┘
```

---

**End of Implementation Plan**
