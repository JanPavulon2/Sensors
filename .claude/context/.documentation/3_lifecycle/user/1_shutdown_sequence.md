---
Last Updated: 2025-12-02
Updated By: Claude Code
Changes: Detailed shutdown sequence documentation
---

# Shutdown Sequence - Complete Flow

This document traces the exact sequence of events when the application shuts down, from signal to exit.

## Overview Diagram

```
User presses Ctrl+C (SIGINT) or app calls shutdown
                    ↓
        Signal handler called
                    ↓
        shutdown_event.set()
                    ↓
        main() coroutine wakes from await
                    ↓
        coordinator.shutdown_all()
                    ↓
        ┌─────────────────────────────────────────┐
        │  Run Handlers in Priority Order (DESC)  │
        ├─────────────────────────────────────────┤
        │  1. LEDShutdownHandler (priority 100)    │
        │  2. AnimationShutdownHandler (pri 90)    │
        │  3. APIServerShutdownHandler (pri 80)    │
        │  4. TaskCancellationHandler (pri 40)     │
        │  5. AllTasksCancellationHandler (pri 40) │
        │  6. GPIOShutdownHandler (pri 20)         │
        └─────────────────────────────────────────┘
                    ↓
        All handlers complete
                    ↓
        emergency_gpio_cleanup() (atexit)
                    ↓
        sys.exit(0)
```

## Detailed Timeline

### 1. Signal Reception (User Ctrl+C)

**File**: `src/main_asyncio.py:417-423`

```python
def _signal(sig):
    log.info(f"Signal received: {sig.name}")
    shutdown_event.set()

loop = asyncio.get_running_loop()
for sig in (signal.SIGINT, signal.SIGTERM):
    loop.add_signal_handler(sig, lambda s=sig: _signal(s))
```

**What happens**:
1. User presses Ctrl+C
2. OS delivers SIGINT to process
3. Asyncio's event loop calls `_signal()` handler
4. Handler logs signal name
5. **`shutdown_event.set()`** - This wakes up main loop

**Log output**:
```
Signal received: SIGINT
Shutdown requested
```

---

### 2. Main Loop Wakes Up

**File**: `src/main_asyncio.py:427-428`

```python
await shutdown_event.wait()
log.info("Shutdown requested")
```

**What happens**:
1. Main coroutine was blocked at `await shutdown_event.wait()`
2. Event is now set, so main continues
3. Logs "Shutdown requested"
4. Proceeds to shutdown_all()

**Log output**:
```
Shutdown requested
🛑 Initiating graceful shutdown sequence...
   Reason: SIGINT
```

---

### 3. Shutdown Coordinator Begins

**File**: `src/lifecycle/shutdown_coordinator.py:106-175`

```python
async def shutdown_all(self) -> None:
    log.info("🛑 Initiating graceful shutdown sequence...")
    sorted_handlers = sorted(
        self._handlers, key=lambda h: h.shutdown_priority, reverse=True
    )

    for handler in sorted_handlers:
        # Call with timeout, catch errors, continue
```

**What happens**:
1. Sorts all registered handlers by priority (descending)
2. Calculates total shutdown timeout (15 seconds default)
3. Iterates through handlers in order

---

### 4. Handler Execution (Priority Order)

Each handler follows this pattern:

```
┌─────────────────────────────────────┐
│ Handler Execution Template          │
├─────────────────────────────────────┤
│ 1. Check total timeout exceeded?    │
│    If yes: break, don't run        │
│                                     │
│ 2. Call handler.shutdown()          │
│    with 5-second timeout            │
│                                     │
│ 3. Handle exceptions:               │
│    - TimeoutError: log warning      │
│    - CancelledError: re-raise       │
│    - Other: log error, continue     │
│                                     │
│ 4. Next handler                     │
└─────────────────────────────────────┘
```

#### Handler 1: LEDShutdownHandler (Priority 100)

**File**: `src/lifecycle/handlers/led_shutdown_handler.py`

```python
async def shutdown(self) -> None:
    """Turn off all LEDs."""
    log.info("Stopping LEDs...")
    try:
        hardware.main_strip.clear()
        log.debug("✓ Main strip cleared")
    except Exception as e:
        log.error(f"Error clearing main strip: {e}")
    # ... repeat for all strips
```

**What happens**:
1. Calls `clear()` on all WS281x LED strips
2. Sends "all pixels black" via GPIO
3. LEDs turn off (important for safety!)

**Log output**:
```
🛑 Initiating graceful shutdown sequence...
   Reason: SIGINT
Shutting down LEDShutdownHandler (priority=100)...
Stopping LEDs...
✓ Main strip cleared
✓ LEDShutdownHandler shutdown complete
```

**Duration**: ~50ms

**Timeout**: 5 seconds (more than enough)

---

#### Handler 2: AnimationShutdownHandler (Priority 90)

**File**: `src/lifecycle/handlers/animation_shutdown_handler.py`

```python
async def shutdown(self) -> None:
    """Stop animation engine and service."""
    log.info("Stopping animations...")

    try:
        self.led_controller.animation_mode_controller.animation_service.stop_all()
        log.debug("✓ Animation service stopped")
    except Exception as e:
        log.error(f"Error stopping animation service: {e}")

    try:
        if self.led_controller.animation_engine.is_running():
            await self.led_controller.animation_engine.stop()
            log.debug("✓ Animation engine stopped")
    except Exception as e:
        log.error(f"Error stopping animation engine: {e}")
```

**What happens**:
1. Calls `stop_all()` on animation service
   - Clears running animation queue
   - Stops transitions
2. Calls `stop()` on animation engine
   - Cancels animation coroutines
   - Waits for them to finish

**Log output**:
```
Shutting down AnimationShutdownHandler (priority=90)...
Stopping animations...
✓ Animation service stopped
✓ Animation engine stopped
✓ AnimationShutdownHandler shutdown complete
```

**Duration**: ~100ms

**Why before API**: Need to stop visual output before network interface goes away

---

#### Handler 3: APIServerShutdownHandler (Priority 80)

**File**: `src/lifecycle/handlers/api_server_shutdown_handler.py`

```python
async def shutdown(self) -> None:
    """Gracefully shutdown FastAPI/Uvicorn server."""
    log.info("Stopping API server...")

    if self.api_task and not self.api_task.done():
        self.api_task.cancel()
        try:
            await self.api_task
        except asyncio.CancelledError:
            log.debug("API server cancelled")
        log.debug("✓ API server stopped")
```

**What happens**:
1. Calls `cancel()` on API server task
2. Awaits the task (waits for cancellation to complete)
3. API server stops accepting requests
4. Uvicorn gracefully closes listening socket

**Log output**:
```
Shutting down APIServerShutdownHandler (priority=80)...
Stopping API server...
🌐 API server cancelled (expected during shutdown)
✓ APIServerShutdownHandler shutdown complete
```

**Duration**: ~50ms

**Why here**: Clients might be making requests. Clean shutdown prevents "connection refused" errors.

---

#### Handler 4: TaskCancellationHandler (Priority 40)

**File**: `src/lifecycle/handlers/task_cancellation_handler.py`

```python
async def shutdown(self) -> None:
    """Cancel and await specific managed tasks."""
    log.info("Cancelling selected background tasks...")

    for task in self.tasks:  # keyboard_task, polling_task, api_task
        if not task.done():
            task.cancel()
            log.debug(f"Cancelled task: {task.get_name()}")

    if self.tasks:
        await asyncio.gather(*self.tasks, return_exceptions=True)

    log.debug("✓ All tasks cancelled")
```

**What happens**:
1. Cancels explicitly-tracked tasks:
   - Keyboard input adapter
   - Hardware polling loop
   - API server task (again, to be safe)
2. Uses `gather(..., return_exceptions=True)` to wait
   - This prevents one exception from blocking others

**Log output**:
```
Shutting down TaskCancellationHandler (priority=40)...
Cancelling selected background tasks...
Cancelled task: KeyboardInputAdapter
Cancelled task: ControlPanel Polling Loop
Cancelled task: FastAPI/Uvicorn Server
✓ TaskCancellationHandler shutdown complete
```

**Duration**: ~100ms

**Why separate from others**: These tasks are "managed explicitly". We cancel them first, then catch any orphans in the next handler.

---

#### Handler 5: AllTasksCancellationHandler (Priority 40)

**File**: `src/lifecycle/handlers/all_tasks_cancellation_handler.py`

```python
async def shutdown(self) -> None:
    """Cancel all remaining tracked tasks (except explicitly managed ones)."""
    log.info("Cancelling all remaining tracked tasks...")

    tasks_to_cancel = [
        record.task for record in self._registry.list_all()
        if not record.task.done() and record.task not in self.exclude_tasks
    ]

    for task in tasks_to_cancel:
        log.debug(f"Cancelling orphan task: {task.get_name()}")
        task.cancel()

    if tasks_to_cancel:
        await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

    log.debug(f"✓ Cancelled {len(tasks_to_cancel)} remaining tasks")
```

**What happens**:
1. Gets all tasks from TaskRegistry
2. Filters out ones already cancelled (already done)
3. Filters out explicitly-managed tasks (keyboard, polling, api)
4. Cancels all remaining "orphan" tasks
5. Waits for them all to finish

**Log output**:
```
Shutting down AllTasksCancellationHandler (priority=40)...
Cancelling all remaining tracked tasks...
Cancelling orphan task: AnimationEngine main loop
Cancelling orphan task: LogBroadcaster worker
Cancelling orphan task: Static mode pulse
✓ AllTasksCancellationHandler shutdown complete
```

**Duration**: ~200ms

**Why important**: Catches any tasks created with `create_tracked_task()` that aren't explicitly managed. Prevents orphaned tasks after exit.

**exclude_tasks parameter**:
```python
AllTasksCancellationHandler(exclude_tasks=[keyboard_task, polling_task, api_task])
```
This prevents double-cancelling the same tasks. Without it, we'd cancel keyboard_task twice (once in TaskCancellationHandler, again here).

---

#### Handler 6: GPIOShutdownHandler (Priority 20)

**File**: `src/lifecycle/handlers/gpio_shutdown_handler.py`

```python
async def shutdown(self) -> None:
    """Clean up GPIO pins."""
    log.info("Cleaning up GPIO...")
    try:
        self.gpio_manager.cleanup()
        log.debug("✓ GPIO cleaned up")
    except Exception as e:
        log.error(f"Error cleaning up GPIO: {e}")
```

**What happens**:
1. Calls `GPIO.cleanup()` via rpi_ws281x library
2. Resets all GPIO pins to inputs (safe state)
3. Releases GPIO memory
4. Allows GPIO to be used by other processes

**Log output**:
```
Shutting down GPIOShutdownHandler (priority=20)...
Cleaning up GPIO...
✓ GPIO cleaned up
✓ GPIOShutdownHandler shutdown complete
```

**Duration**: ~50ms

**Why last**: All tasks and hardware must be stopped before releasing GPIO pins. If we release them early, something might try to write to them during shutdown.

---

### 5. Shutdown Complete

**File**: `src/main_asyncio.py:430-431`

```python
await coordinator.shutdown_all()
log.info("👋 Diuna shut down cleanly.")
```

**What happens**:
1. All handlers completed (or timed out)
2. Logs completion message
3. main() coroutine returns
4. asyncio.run() returns
5. Finally block executes

**Log output**:
```
✓ Shutdown sequence complete
👋 Diuna shut down cleanly.
```

---

### 6. Emergency GPIO Cleanup (atexit)

**File**: `src/main_asyncio.py:255 & 437-446`

```python
atexit.register(emergency_gpio_cleanup)

# ... later in finally block:
finally:
    emergency_gpio_cleanup()
    sys.exit(0)
```

**What happens**:
1. Python's atexit handlers are called (registered at startup)
2. `emergency_gpio_cleanup()` is called
3. Attempts GPIO cleanup one more time
4. This is a safety net for crashes/segfaults
5. sys.exit(0) terminates process

**Log output**:
```
🚨 Emergency GPIO cleanup completed
```

**Why needed**: If app crashes before shutdown_all() completes, GPIO might still be initialized. This ensures cleanup happens anyway.

---

## Timeout Management

### Per-Handler Timeout
- **Default**: 5 seconds per handler
- **Enforced by**: `asyncio.wait_for(handler.shutdown(), timeout=5.0)`
- **On timeout**: Logs warning and continues to next handler

Example:
```python
try:
    await asyncio.wait_for(handler.shutdown(), timeout=5.0)
except asyncio.TimeoutError:
    log.error(
        f"⚠️  {handler_name} shutdown timeout (5.0s)"
    )
    # Continue with next handler
```

### Total Shutdown Timeout
- **Default**: 15 seconds for entire sequence
- **Enforced by**: Elapsed time check before each handler
- **On timeout**: Logs warning and stops running remaining handlers

```python
elapsed = asyncio.get_event_loop().time() - start_time
if elapsed > self._total_timeout:  # 15 seconds
    log.error(f"⚠️  Total shutdown timeout exceeded ({elapsed:.1f}s > 15.0s)")
    break  # Stop running handlers
```

### What If Handler Times Out?

If a handler takes > 5 seconds:

```
Shutting down AnimationShutdownHandler (priority=90)...
[5 seconds elapse...]
⚠️  AnimationShutdownHandler shutdown timeout (5.0s)
Shutting down APIServerShutdownHandler (priority=80)...
```

The handler is logged as timed out, but:
- The next handler still runs
- The application still exits (after total timeout)
- Users don't have to wait more than 15 seconds total

---

## Error Handling During Shutdown

### CancelledError is Expected

When a task is cancelled, it raises `asyncio.CancelledError`. This is **normal and expected**:

```python
try:
    await some_async_work()
except asyncio.CancelledError:
    # This is NORMAL during shutdown
    # Clean up if needed, then re-raise
    cleanup()
    raise  # Important: propagate the cancellation
```

### What About Other Exceptions?

If a handler raises a different exception:

```python
try:
    await handler.shutdown()
except asyncio.TimeoutError:
    log.error(f"Handler timeout")
except asyncio.CancelledError:
    log.debug("Handler cancelled")
    raise  # Re-raise to stop everything
except Exception as e:
    log.error(f"Handler error: {e}", exc_info=True)
    # Continue to next handler!
```

**Key point**: One handler failing doesn't block shutdown. All handlers run (with error logging).

---

## Monitoring Shutdown

### Check if shutdown is working

```bash
# Terminal 1: Start app
python src/main_asyncio.py

# Terminal 2: Watch what happens during shutdown
curl http://localhost:8000/api/v1/system/tasks/active

# Terminal 1: Press Ctrl+C and watch logs
```

You should see:
1. Signal received log
2. Handler execution logs (LED → Animation → API → Tasks → GPIO)
3. "Shutdown sequence complete"
4. "Diuna shut down cleanly"
5. Immediate exit (no hang)

### If shutdown hangs

If the app doesn't exit after pressing Ctrl+C:

1. Check active tasks:
   ```bash
   # In another terminal
   curl http://localhost:8000/api/v1/system/tasks/active
   ```

2. Look for tasks with very long "running_for_seconds"
   - That's likely the one blocking shutdown

3. Check logs for which handler it's stuck in
   - Task logs: "Cancelling..."
   - But never reaches: "✓ Cancelled"

4. That handler might not be properly handling `CancelledError`

---

## Summary Table

| Handler | Priority | Purpose | Timeout | If Fails |
|---------|----------|---------|---------|----------|
| LED | 100 | Turn off pixels | 5s | Warn, continue |
| Animation | 90 | Stop animations | 5s | Warn, continue |
| API | 80 | Stop server | 5s | Warn, continue |
| TaskCancellation | 40 | Cancel specific tasks | 5s | Warn, continue |
| AllTasksCancellation | 40 | Cancel orphans | 5s | Warn, continue |
| GPIO | 20 | Reset GPIO | 5s | Warn, continue |
| **Total** | - | - | **15s** | Exit anyway |

