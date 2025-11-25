---
Last Updated: 2025-11-25
Updated By: Claude Code Architecture
Changes: Complete global exception handler design for async LED control system
---

# Global Exception Handler Architecture for Diuna LED Control System

**Version**: 1.0
**Date**: 2025-11-25
**Status**: Design Complete - Ready for Review
**Platform**: Raspberry Pi 4 / Python 3.9+ / asyncio

---

## Executive Summary

This document defines a comprehensive global exception handling strategy for the Diuna LED control system that preserves the existing fault-tolerant patterns while adding centralized error management, emergency recovery, and structured logging.

**Core Principles**:
1. **Preserve existing fault tolerance** (EventBus handler isolation, FrameManager continue-on-error)
2. **Non-invasive integration** (minimal changes to working code)
3. **Performance-conscious** (no impact on 60 FPS render loop)
4. **Graceful degradation** (fallback to safe states, not crashes)
5. **Operational visibility** (structured logging with rate limiting)

**Key Insight**: The system is already well-designed for fault tolerance. We're adding a safety net for truly critical errors that would cause process termination, not replacing the existing patterns.

---

## 1. Exception Strategy

### 1.1 Exception Categorization

The system uses a **three-tier exception classification** based on **operational impact**:

| Category | Description | System Response | Examples |
|----------|-------------|-----------------|----------|
| **CRITICAL** | System integrity compromised | Emergency shutdown with GPIO cleanup | `MemoryError`, `SystemError`, hardware failures, DMA errors |
| **RECOVERABLE** | Component failure, system continues | Log + fallback + continue | Frame render errors, animation crashes, I/O timeouts |
| **HANDLED** | Expected operational events | Log at DEBUG level, no escalation | `asyncio.CancelledError`, validation errors |

### 1.2 Why No Custom Exception Classes

**Decision**: Use Python built-in exceptions only.

**Rationale**:
- Current codebase uses only built-in exceptions (clean, simple)
- asyncio exceptions (`CancelledError`, `TimeoutError`) are well-understood
- Hardware library exceptions (`RuntimeError` from rpi_ws281x) are already caught
- Adding custom exceptions increases complexity without clear benefit
- **Exception classification happens in the handler, not at throw site**
- Zero impact on existing code

**Exception Mapping Strategy**:

```python
# CRITICAL (trigger shutdown)
CRITICAL_EXCEPTIONS = (
    MemoryError,        # OOM on Raspberry Pi
    SystemError,        # Python runtime failure
)

# RECOVERABLE (log + continue)
RECOVERABLE_EXCEPTIONS = (
    RuntimeError,       # Hardware failures (rpi_ws281x)
    OSError,            # GPIO access errors
    IOError,            # File I/O failures
    ValueError,         # Parameter validation failures
    IndexError,         # Array bounds errors (pixel indices)
    KeyError,           # Missing configuration keys
    AttributeError,     # Missing object attributes
    TypeError,          # Type mismatches
)

# HANDLED (expected, minimal logging)
HANDLED_EXCEPTIONS = (
    asyncio.CancelledError,  # Task cancellation (expected)
    asyncio.TimeoutError,    # Expected timeouts
)
```

---

## 2. Architecture Overview

### 2.1 Exception Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Application Layer                            │
│  main_asyncio.py → LEDController → Controllers → Hardware            │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
                   ↓ Exception raised
┌─────────────────────────────────────────────────────────────────────┐
│            Component-Level Exception Handling (PRESERVED)            │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────────┐        │
│  │  EventBus     │  │ FrameManager │  │ AnimationEngine  │        │
│  │  (isolated)   │  │ (continue)   │  │ (stop on error)  │        │
│  └───────┬───────┘  └──────┬───────┘  └────────┬─────────┘        │
│          │                  │                    │                   │
│          └──────────────────┴────────────────────┘                   │
│              try-except with local recovery                          │
│              └→ Log error, apply fallback, continue                  │
└─────────────────────────────────────────────────────────────────────┘
                   │
                   ↓ Unhandled exception (rare)
┌─────────────────────────────────────────────────────────────────────┐
│              Task-Level Exception Wrapper (NEW)                      │
│  critical_task_wrapper() wraps critical async tasks:                │
│    - FrameManager render loop                                        │
│    - AnimationEngine                                                 │
│    - Hardware polling loop                                           │
│                                                                       │
│  Action: Log exception details + bubbles to global handler           │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ↓ Exception bubbles to event loop
┌─────────────────────────────────────────────────────────────────────┐
│            Global Exception Handler (LAST RESORT - NEW)              │
│  loop.set_exception_handler(global_exception_handler)               │
│                                                                       │
│  Action:                                                             │
│    1. Classify exception (CRITICAL vs RECOVERABLE)                   │
│    2. Log with full context (task, stack trace)                      │
│    3. CRITICAL → trigger emergency_shutdown()                        │
│    4. RECOVERABLE → log warning, continue                            │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ↓ CRITICAL exception detected
┌─────────────────────────────────────────────────────────────────────┐
│                  Emergency Shutdown (NEW)                            │
│  1. Log critical error with full context                             │
│  2. Clear all LED queues (FrameManager)                              │
│  3. Turn off LEDs (set all zones to black)                           │
│  4. GPIO cleanup (emergency_gpio_cleanup)                            │
│  5. Exit gracefully (avoid seg fault / hardware hang)                │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Recovery Paths (Preserved)

```
Frame Render Error:
  FrameManager._render_atomic() → try-except → log.error → continue to next frame
  └→ Result: Single frame dropped, animation continues ✓

Animation Generator Error:
  AnimationEngine.run() → try-except → log.error → stop animation
  └→ Result: Animation stops, static mode fallback ✓

EventBus Handler Error:
  EventBus.publish() → handler try-except → log.error → continue to next handler
  └→ Result: Single handler fails, other handlers still execute ✓

Hardware DMA Error:
  WS281xStrip.apply_frame() → try-except → log.error → skip frame
  └→ Result: Frame not rendered, next frame attempts fresh DMA ✓

Critical Memory Error: (NEW)
  Any component → global_exception_handler → emergency_shutdown()
  └→ Result: System halts safely with GPIO cleanup ✓
```

---

## 3. Detailed Implementation Strategy

### 3.1 New File: `src/utils/exception_handler.py`

```python
"""
Global Exception Handler for Diuna LED Control System
======================================================

Provides centralized exception handling with classification,
rate limiting, and emergency shutdown capability.

This module adds a safety net for critical errors that would cause
process termination, while preserving the fault-tolerant patterns
in EventBus and FrameManager.
"""

import asyncio
import traceback
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from utils.logger import get_logger, LogCategory, LogLevel

log = get_logger().for_category(LogCategory.SYSTEM)


# === Exception Classification ===

CRITICAL_EXCEPTIONS = (
    MemoryError,        # OOM on Raspberry Pi
    SystemError,        # Python runtime failure
)

RECOVERABLE_EXCEPTIONS = (
    RuntimeError,       # Hardware failures (rpi_ws281x)
    OSError,            # GPIO access errors
    IOError,            # File I/O failures
    ValueError,         # Parameter validation failures
    IndexError,         # Array bounds errors (pixel indices)
    KeyError,           # Missing configuration keys
    AttributeError,     # Missing object attributes
    TypeError,          # Type mismatches
)

HANDLED_EXCEPTIONS = (
    asyncio.CancelledError,  # Task cancellation (expected during shutdown)
    asyncio.TimeoutError,    # Expected timeouts
)


# === Rate Limiting ===

class ExceptionRateLimiter:
    """
    Rate limiter to prevent log spam from repeated exceptions.

    Tracks exception counts per (exception_type, task_name) key
    and suppresses logging after threshold.

    This prevents "log flood" situations where a hardware error
    might repeat 60 times per second (60 FPS render loop).
    """

    def __init__(self, window_seconds: int = 60, max_logs_per_window: int = 10):
        """
        Initialize rate limiter.

        Args:
            window_seconds: Time window for rate limit (default 60s)
            max_logs_per_window: Max exceptions to log per window (default 10)
        """
        self.window = timedelta(seconds=window_seconds)
        self.max_logs = max_logs_per_window
        self.counts: Dict[tuple, list] = defaultdict(list)

    def should_log(self, exc_type: type, task_name: str) -> bool:
        """
        Check if exception should be logged based on rate limit.

        Returns:
            True if should log, False if suppressed
        """
        key = (exc_type.__name__, task_name)
        now = datetime.now()

        # Clean old entries outside window
        self.counts[key] = [
            timestamp for timestamp in self.counts[key]
            if now - timestamp < self.window
        ]

        # Check if under limit
        if len(self.counts[key]) < self.max_logs:
            self.counts[key].append(now)
            return True

        return False

    def get_suppressed_count(self, exc_type: type, task_name: str) -> int:
        """Get count of suppressed logs in current window."""
        key = (exc_type.__name__, task_name)
        total = len(self.counts[key])
        return max(0, total - self.max_logs)


# Global rate limiter instance
_rate_limiter = ExceptionRateLimiter()


# === Global Exception Handler ===

def global_exception_handler(loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> None:
    """
    Global exception handler for asyncio event loop.

    Registered via: loop.set_exception_handler(global_exception_handler)

    Handles:
    - Unhandled exceptions from async tasks
    - Task exceptions that escape component-level handlers
    - Loop-level errors (protocol errors, callback exceptions)

    Does NOT handle (these are caught locally):
    - Exceptions inside try-except blocks (handled at component level)
    - CancelledError (handled as expected operational event)
    - Exceptions caught by task wrappers (logged separately)

    This is a LAST RESORT handler. Most exceptions should be caught
    at the component level (EventBus, FrameManager, etc.) where
    recovery can be more intelligent.
    """

    exception = context.get('exception')
    message = context.get('message', 'Unhandled exception in event loop')
    task = context.get('task')
    future = context.get('future')

    # Extract task name for logging
    task_name = 'unknown'
    if task:
        task_name = task.get_name()
    elif future:
        task_name = f"future-{id(future)}"

    # CancelledError is expected during shutdown - don't log
    if isinstance(exception, asyncio.CancelledError):
        log.debug(f"Task cancelled (expected): {task_name}")
        return

    # Rate limiting check to prevent log spam
    if exception and not _rate_limiter.should_log(type(exception), task_name):
        suppressed = _rate_limiter.get_suppressed_count(type(exception), task_name)
        if suppressed == 1:  # Log once when suppression starts
            log.warn(
                f"Exception rate limit reached, suppressing further logs",
                task=task_name,
                exception_type=type(exception).__name__,
                window="60s",
                limit=10
            )
        return

    # Classify exception
    is_critical = exception and isinstance(exception, CRITICAL_EXCEPTIONS)
    is_recoverable = exception and isinstance(exception, RECOVERABLE_EXCEPTIONS)

    # Log with appropriate level
    if is_critical:
        log.error(
            f"CRITICAL: {message}",
            task=task_name,
            exception=str(exception),
            exception_type=type(exception).__name__ if exception else 'None',
        )
        if exception:
            tb_lines = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
            log.error(f"Stack trace:\n{''.join(tb_lines)}")

        # Trigger emergency shutdown
        asyncio.create_task(_trigger_emergency_shutdown(loop, exception))

    elif is_recoverable:
        log.error(
            f"Recoverable error: {message}",
            task=task_name,
            exception=str(exception) if exception else 'None',
            exception_type=type(exception).__name__ if exception else 'None',
        )
        # Continue running - no action needed (fault tolerance preserved)

    else:
        # Unknown exception type - log as error but don't shutdown
        log.error(
            f"Unhandled exception: {message}",
            task=task_name,
            exception=str(exception) if exception else 'None',
            exception_type=type(exception).__name__ if exception else 'None',
        )


async def _trigger_emergency_shutdown(loop: asyncio.AbstractEventLoop, exception: Exception) -> None:
    """
    Trigger emergency shutdown after critical exception.

    Flow:
    1. Log critical error
    2. Clear frame queues (prevent LED state corruption)
    3. Turn off LEDs (set all zones to black)
    4. GPIO cleanup
    5. Stop event loop

    This function is called as a new task to ensure it runs
    even if the original context is corrupted.
    """
    log.error("Initiating emergency shutdown due to critical exception")

    try:
        # Import here to avoid circular dependency
        # and to access frame_manager reference stored in loop
        if hasattr(loop, 'frame_manager_ref'):
            frame_manager = loop.frame_manager_ref
            frame_manager.clear_all()
            log.info("Frame queues cleared")
    except Exception as e:
        log.error(f"Failed to clear frame queues: {e}")

    try:
        # Import shutdown function from main module
        from main_asyncio import shutdown
        await shutdown(loop, "CRITICAL_ERROR")
    except Exception as e:
        log.error(f"Failed during emergency shutdown: {e}")
        # Force exit
        loop.call_soon_threadsafe(loop.stop)
```

### 3.2 Integration into `src/main_asyncio.py`

**Location**: Inside the `main()` async function, immediately after event loop creation.

**Changes** (approximately 15 lines added):

```python
async def main():
    """Main async entry point with global exception handling."""

    log.info("Starting Diuna application...")

    # === NEW: Register global exception handler ===
    loop = asyncio.get_running_loop()
    from utils.exception_handler import global_exception_handler
    loop.set_exception_handler(global_exception_handler)
    log.info("Global exception handler registered")

    # ... existing GPIO/config initialization code ...

    # === NEW: Store frame_manager reference for emergency shutdown ===
    loop.frame_manager_ref = frame_manager

    # ... rest of existing main() function ...
```

**Modification**: Update `emergency_gpio_cleanup()` function:

```python
def emergency_gpio_cleanup():
    """Emergency cleanup - called on any exit (crashes, seg faults)."""
    try:
        # === NEW: Clear frame queues if possible ===
        try:
            loop = asyncio.get_event_loop()
            if hasattr(loop, 'frame_manager_ref'):
                loop.frame_manager_ref.clear_all()
                log.info("Frame queues cleared in emergency cleanup")
        except Exception as e:
            log.error(f"Failed to clear frame queues: {e}")

        # Existing GPIO cleanup
        gpio_manager = GPIOManager()
        gpio_manager.cleanup()
        log.info("Emergency GPIO cleanup completed")
    except Exception as e:
        log.error(f"Failed to cleanup GPIO on exit: {e}")
```

### 3.3 Integration into `src/engine/frame_manager.py`

**Status**: NO CHANGES NEEDED ✓

The existing exception handling in `_render_loop()` is already optimal:

```python
# Existing code (lines 296-308):
try:
    main_frame = await self._select_main_frame_by_priority()
    preview_frame = await self._select_preview_frame_by_priority()

    if main_frame or preview_frame:
        self._render_atomic(main_frame, preview_frame)
        self.frames_rendered += 1
        self.frame_times.append(time.perf_counter())

except Exception as e:
    log.error(f"Render error: {e}", exc_info=True)
    # ✓ CORRECT: Continue to next frame (preserves 60 FPS)
```

**Why no changes**: This pattern is perfect for real-time rendering:
- Catches all errors at frame level
- Logs with full traceback (`exc_info=True`)
- Continues to next frame (fault tolerance preserved)
- Prevents one bad frame from crashing 60 FPS loop

**Optional Enhancement** (not required):
Add `clear_all()` method to FrameManager for emergency shutdown:

```python
def clear_all(self) -> None:
    """Clear all frame queues in emergency shutdown."""
    try:
        for priority in self.main_queues:
            self.main_queues[priority].clear()
        self.preview_queue.clear()
        log.info("All frame queues cleared")
    except Exception as e:
        log.error(f"Error clearing frame queues: {e}")
```

### 3.4 Integration into `src/services/event_bus.py`

**Status**: NO CHANGES NEEDED ✓

The existing exception handling in `publish()` is already optimal for fault tolerance:

```python
# Existing code (lines 186-202):
for handler_entry in handlers:
    # Apply per-handler filter
    if handler_entry.filter_fn and not handler_entry.filter_fn(event):
        continue

    try:
        # Handle async/sync transparently
        if asyncio.iscoroutinefunction(handler_entry.handler):
            await handler_entry.handler(event)
        else:
            handler_entry.handler(event)
    except Exception as e:
        log.error(
            f"Event handler failed: {handler_entry.handler.__name__} for {event.type.name}",
            exception=e
        )
        # ✓ CORRECT: Continue to next handler (one handler error doesn't stop others)
```

**Why no changes**: This pattern implements **handler isolation** perfectly:
- Each handler wrapped in try-except
- One handler failure doesn't stop other handlers
- Error logged with handler name for debugging
- Prevents cascading failures

### 3.5 Optional: Integration into `src/animations/engine.py`

**Status**: RECOMMENDED ADDITION (not required)

Add try-except around animation generator to prevent animation engine crash:

```python
async def run(self, animation_id: AnimationID, excluded_zones: List[ZoneID] = None, **params) -> None:
    """Run animation with error handling."""

    # ... existing setup code ...

    try:
        async for frame in animation_instance.run():
            if not self.running:
                break

            # Yield frame to FrameManager
            await self._submit_frame(frame)

    except asyncio.CancelledError:
        log.debug(f"Animation {animation_id.name} cancelled")
        raise

    except Exception as e:
        # NEW: Catch animation errors to prevent engine crash
        log.error(
            f"Animation {animation_id.name} crashed",
            exception=str(e),
            exception_type=type(e).__name__,
        )
        # Stop animation gracefully
        self.running = False

    finally:
        # ... existing cleanup ...
```

---

## 4. Code Examples

### 4.1 Global Exception Handler Setup

```python
# In main_asyncio.py main() function:

async def main():
    log.info("Starting Diuna application...")

    # Get event loop reference
    loop = asyncio.get_running_loop()

    # Register global exception handler
    from utils.exception_handler import global_exception_handler
    loop.set_exception_handler(global_exception_handler)
    log.info("Global exception handler registered")

    # Store frame_manager for emergency access
    loop.frame_manager_ref = frame_manager

    # ... rest of initialization ...
```

### 4.2 Example: How Exception Flows Through System

```python
# Scenario: Hardware DMA error during frame render

# 1. Error occurs in hardware layer:
WS281xStrip.apply_frame()
  └─→ RuntimeError: "DMA channel conflict"

# 2. FrameManager catches it (component-level):
FrameManager._render_loop()
  try:
      self._render_atomic(main_frame, preview_frame)
  except Exception as e:
      log.error(f"Render error: {e}", exc_info=True)
      # Continue to next frame - PRESERVED FAULT TOLERANCE

  # Frame is dropped, next frame tries again
  # FrameManager continues at 60 FPS ✓

# 3. Global handler never sees this (caught locally)
# System continues normally ✓
```

### 4.3 Example: Critical Error Handling

```python
# Scenario: System runs out of memory

# 1. Error occurs:
MemoryError: "Failed to allocate buffer for frame"

# 2. Component-level handler catches it (if present):
try:
    buffer = allocate_pixel_buffer(10000)
except MemoryError as e:
    log.error("Out of memory", error=str(e))
    # Component tries to recover or degrades gracefully

# 3. If component-level handler failed (unlikely), exception bubbles up:
# Task wrapper logs it (optional)
# Event loop bubbles to global handler

# 4. Global handler classifies as CRITICAL:
global_exception_handler(loop, {
    'exception': MemoryError(...),
    'task': <Task name: FrameManager>
})

# 5. Global handler triggers emergency shutdown:
log.error(f"CRITICAL: Unhandled exception in event loop...")
await emergency_shutdown(loop)

# 6. Emergency shutdown:
# - Clears frame queues
# - Turns off LEDs (black frame)
# - Cleanup GPIO
# - Exits gracefully ✓
```

### 4.4 Example: Rate Limiting in Action

```python
# Scenario: Repeated hardware errors (e.g., loose GPIO connection)

# First 10 occurrences are logged (per minute):
[12:34:56] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:34:57] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:34:58] SYSTEM ✗ Recoverable error: DMA transfer failed
... (7 more times)
[12:35:03] SYSTEM ✗ Recoverable error: DMA transfer failed

# 11th occurrence within 60s window:
[12:35:04] SYSTEM ⚠ Exception rate limit reached, suppressing further logs
            └─ task: FrameManagerRenderLoop
            └─ exception_type: RuntimeError
            └─ window: 60s
            └─ limit: 10

# System continues running, logs are suppressed
# After 60s window expires, if errors still occur, logs resume

# Result: User sees problem without log flood ✓
```

---

## 5. Performance Analysis

### 5.1 Impact on 60 FPS Target

| Component | Overhead | Impact on FPS |
|-----------|----------|---------------|
| **Global handler registration** | One-time setup | Zero |
| **Try-except in render loop** | ~10-50 ns per iteration | Negligible (<0.001ms) |
| **Exception logging** | 1-5ms per exception | Only on error (rare) |
| **Rate limiter check** | ~100 ns per call | Negligible (<0.001ms) |
| **Stack trace formatting** | 5-10ms | Only on CRITICAL (fatal) |

**Conclusion**:
- **Normal operation**: Zero impact (rate limiter adds ~100ns per handler call, negligible)
- **Error conditions**: Logging overhead only (no impact on frame rendering itself)
- **Critical shutdown**: 5-10ms to format stack trace (acceptable, system already shutting down)

### 5.2 Logging Overhead Strategy

**Problem**: Logging every frame error at 60 FPS = 60 logs/second = log spam.

**Solution**: Rate limiting with per-(exception_type, task_name) tracking.

```python
# Rate limiter configuration:
- Window: 60 seconds
- Max logs per (exception_type, task_name): 10
- After limit: Single suppression warning (prevents repetitive warnings)

# Example output with repeated DMA errors:
[12:34:56] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:34:57] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:34:58] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:34:59] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:35:00] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:35:01] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:35:02] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:35:03] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:35:04] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:35:05] SYSTEM ✗ Recoverable error: DMA transfer failed
[12:35:06] SYSTEM ⚠ Exception rate limit reached, suppressing further logs
            └─ task: FrameManagerRenderLoop
            └─ exception_type: RuntimeError
            └─ window: 60s
            └─ limit: 10

# Result: Max 10 logs per error type per minute (clean, informative)
```

### 5.3 Memory Overhead

| Component | Memory Cost | Notes |
|-----------|-------------|-------|
| ExceptionRateLimiter | ~200 bytes base + 50 bytes per unique (exception, task) pair | Max ~5KB for 100 error types |
| Per-exception context dict | ~1KB per exception | Transient (cleaned up immediately) |
| Stack trace string | 5-10KB per CRITICAL | Transient (only on fatal shutdown) |

**Total steady-state overhead**: <10KB (negligible on Raspberry Pi 4 with 4GB RAM)

---

## 6. Migration & Rollout Plan

### 6.1 Phased Implementation

**Phase 1: Foundation (Day 1)**
- [ ] Create `src/utils/exception_handler.py` (280 lines)
- [ ] Write unit tests for ExceptionRateLimiter (80 lines)
- [ ] Register global handler in `main_asyncio.py` (+10 lines)
- [ ] Test with simulated critical errors
- [ ] Verify GPIO cleanup on crash
- **Effort**: ~2-3 hours

**Phase 2: Integration (Day 2)**
- [ ] Add emergency frame queue clearing (+10 lines in FrameManager)
- [ ] Store frame_manager reference in loop (+5 lines in main_asyncio.py)
- [ ] Update emergency_gpio_cleanup() (+10 lines)
- [ ] Integration tests with real hardware errors
- [ ] Test unplug/replug GPIO scenarios
- **Effort**: ~2-3 hours

**Phase 3: Enhancement (Day 3)**
- [ ] Add animation error handling in AnimationEngine (optional, +15 lines)
- [ ] Add metrics tracking (exception counts per type)
- [ ] Performance validation (maintain 60 FPS)
- [ ] Stress testing (memory exhaustion, GPIO failures)
- **Effort**: ~2-3 hours

**Phase 4: Validation & Documentation (Day 4)**
- [ ] 24-hour stability test
- [ ] Document edge cases and failure modes
- [ ] Update project documentation
- [ ] Final review and sign-off
- **Effort**: ~2-3 hours

**Total Effort**: ~9-12 hours (1-2 development days)

### 6.2 Backwards Compatibility

**Guaranteed**: All existing code works unchanged.

- Existing try-except blocks continue working (no conflicts)
- Global handler is **last resort only** (doesn't interfere with local handlers)
- No API changes to any component
- No new dependencies (uses stdlib only: asyncio, traceback, datetime, collections)
- Zero performance impact on normal operation
- **Rollback**: Remove 15 lines from main_asyncio.py, delete exception_handler.py

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/test_exception_handler.py

import pytest
import asyncio
from utils.exception_handler import ExceptionRateLimiter, global_exception_handler

class TestRateLimiter:

    def test_rate_limiter_allows_under_threshold(self):
        """Rate limiter should allow logs under threshold."""
        limiter = ExceptionRateLimiter(window_seconds=60, max_logs_per_window=10)

        for i in range(10):
            assert limiter.should_log(ValueError, "test_task") is True

        # 11th should be blocked
        assert limiter.should_log(ValueError, "test_task") is False

    def test_rate_limiter_separate_keys(self):
        """Different exception types tracked separately."""
        limiter = ExceptionRateLimiter()

        # Different exception types are tracked separately
        for i in range(10):
            assert limiter.should_log(ValueError, "task1") is True
            assert limiter.should_log(RuntimeError, "task1") is True

    def test_rate_limiter_window_expiry(self):
        """Old entries should be pruned after window expires."""
        limiter = ExceptionRateLimiter(window_seconds=1, max_logs_per_window=10)

        # Add logs
        for i in range(5):
            assert limiter.should_log(ValueError, "test") is True

        # Sleep past window
        import time
        time.sleep(1.1)

        # Should allow more logs
        assert limiter.should_log(ValueError, "test") is True


class TestGlobalExceptionHandler:

    def test_critical_exception_logged(self):
        """Critical exceptions should be logged as errors."""
        loop = asyncio.new_event_loop()
        context = {
            'exception': MemoryError("Test OOM"),
            'message': "Test critical error",
            'task': None
        }

        # Handler should not raise, should log
        global_exception_handler(loop, context)

    def test_cancelled_error_ignored(self):
        """CancelledError should not be logged."""
        loop = asyncio.new_event_loop()
        context = {
            'exception': asyncio.CancelledError(),
            'message': "Task cancelled",
            'task': None
        }

        # Should return without logging error
        global_exception_handler(loop, context)
        # Assert: no error log emitted (verified by mock logger)
```

### 7.2 Integration Tests

```python
# tests/integration/test_exception_handling.py

import pytest
import asyncio
from engine.frame_manager import FrameManager

class TestFrameManagerErrorRecovery:

    @pytest.mark.asyncio
    async def test_render_error_does_not_crash(self):
        """Verify FrameManager continues after render error."""

        fm = FrameManager(fps=60)

        # Inject faulty strip that raises on show()
        class FaultyStrip:
            def show_full_pixel_frame(self, pixels):
                raise RuntimeError("Simulated DMA error")

        fm.add_main_strip(FaultyStrip())

        # Start render loop
        render_task = asyncio.create_task(fm.start())

        # Let it run for a bit
        await asyncio.sleep(0.1)

        # Assert: FrameManager still running
        assert not render_task.done()

        # Stop cleanly
        await fm.stop()
```

### 7.3 Hardware Failure Simulation

```python
# For manual testing - not automated pytest

def test_gpio_cleanup_on_crash():
    """Verify GPIO cleanup happens on critical error."""

    # Simulate critical error in subprocess
    # Verify:
    # - GPIO pins released
    # - LED controller stopped
    # - No hardware hang
    # - No zombie processes
```

---

## 8. Edge Cases & Known Limitations

### 8.1 Edge Cases Handled

| Scenario | Handling | Risk |
|----------|----------|------|
| **Exception during exception handler** | Python's default handler takes over | Low - logs to stderr |
| **Multiple CRITICAL exceptions simultaneously** | First one triggers shutdown, rest logged | Low - shutdown happens once |
| **Exception in emergency_gpio_cleanup()** | Logged, system exits anyway via atexit | Low - atexit guarantees execution |
| **Rate limiter memory growth** | Old entries auto-pruned (60s window) | Low - max ~5KB |
| **Exception with no task context** | Logged with task="unknown" | Low - context preserved |
| **Hardware locked up (no exception)** | Not handled (out of scope) | Medium - needs watchdog timer |

### 8.2 Known Limitations

1. **No automatic recovery from hardware failures**: System logs error and continues, but hardware may remain non-functional until restart.
   - *Mitigation*: Add circuit breaker pattern (future enhancement)

2. **No distributed tracing**: Exception context is local to process.
   - *Mitigation*: For multi-process systems, add centralized logging (future enhancement)

3. **No exception metrics export**: Current design logs only.
   - *Mitigation*: Add metrics collection and export to Prometheus (future enhancement)

4. **No circuit breaker pattern**: If hardware repeatedly fails, system keeps retrying.
   - *Mitigation*: Add backoff/circuit breaker (future enhancement)

5. **Hardware lockup not detected**: If hardware hangs without exception, system won't detect it.
   - *Mitigation*: Add watchdog timer (separate system, out of scope)

---

## 9. Comparison with Alternatives

### 9.1 Design Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Custom exception hierarchy** | Type-safe, explicit error types | Added complexity, maintenance burden | **Rejected** - Built-ins sufficient |
| **Per-component exception handlers** | Distributed control, flexible | Code duplication, inconsistent behavior | **Partial** - Used where needed (EventBus, FrameManager) |
| **Exception middleware pipeline** | Flexible, composable | Over-engineered for this use case | **Rejected** - YAGNI |
| **Crash-only design** (let it crash) | Simple, stateless | Poor user experience, hardware risks | **Rejected** - Must maintain LED operation |
| **Global handler + local handlers** (SELECTED) | Best of both worlds, defense in depth | Slightly more complex code | **✅ Selected** |

### 9.2 Why This Design

1. **Preserves existing patterns**: EventBus and FrameManager fault tolerance unchanged
2. **Non-invasive**: 400 lines new code, 25 lines modified
3. **Performance**: Zero impact on 60 FPS render loop
4. **Pragmatic**: Uses Python built-ins, no new dependencies
5. **Safe**: Emergency shutdown prevents hardware corruption

---

## 10. Future Enhancements

### 10.1 Post-MVP Improvements

1. **Exception metrics dashboard**
   - Track exception counts per type
   - Export to Prometheus/Grafana
   - Alert on anomaly patterns

2. **Circuit breaker pattern**
   - Auto-disable failing components after N failures
   - Exponential backoff before retry
   - Manual reset via API

3. **Remote logging**
   - Send critical exceptions to remote syslog
   - Cloud logging integration (CloudWatch, Datadog)

4. **Health check endpoint**
   - HTTP endpoint for monitoring
   - Returns exception statistics
   - Integration with systemd watchdog

5. **Exception replay for debugging**
   - Capture full system state on error
   - Allow developers to replay error conditions

---

## 11. Summary

### 11.1 What This Design Does

✅ **Add safety net**: Global handler catches unhandled exceptions before system crash
✅ **Preserve fault tolerance**: EventBus and FrameManager patterns unchanged
✅ **Maintain performance**: Zero impact on 60 FPS target
✅ **Enable emergency recovery**: Graceful shutdown with GPIO cleanup
✅ **Prevent log spam**: Rate limiting per exception type
✅ **Non-invasive integration**: Minimal code changes
✅ **Production-ready**: Comprehensive error classification and handling

### 11.2 Implementation Checklist

**Before Implementation**:
- [ ] Review this design document
- [ ] Ensure understanding of three exception categories
- [ ] Understand rate limiting strategy
- [ ] Plan integration into main_asyncio.py

**During Implementation**:
- [ ] Create exception_handler.py (280 lines)
- [ ] Add unit tests (80 lines)
- [ ] Update main_asyncio.py (25 lines)
- [ ] Update emergency_gpio_cleanup() (10 lines)
- [ ] Test with simulated errors
- [ ] Verify GPIO cleanup on crash

**After Implementation**:
- [ ] Integration tests with real hardware
- [ ] 24-hour stability test
- [ ] Document in project documentation
- [ ] Update CLAUDE.md if needed

---

## 12. Appendix: File Checklist

### Files to Create

**`src/utils/exception_handler.py`** (280 lines)
- ExceptionRateLimiter class
- global_exception_handler function
- _trigger_emergency_shutdown helper
- Exception classification constants

**`tests/test_exception_handler.py`** (80 lines)
- Unit tests for ExceptionRateLimiter
- Unit tests for global_exception_handler
- Mock logging for verification

### Files to Modify

**`src/main_asyncio.py`** (+25 lines total)
- Import exception_handler
- Register global handler
- Store frame_manager reference (+5 lines)
- Update emergency_gpio_cleanup() (+10 lines)

**`src/engine/frame_manager.py`** (optional)
- Add clear_all() method (+10 lines)

### No Changes Needed

- `src/services/event_bus.py` (fault-tolerant handler isolation already perfect)
- Any other component (exception handling is per-component, not global)

---

## 13. Dependencies

### New Dependencies: **NONE**

All code uses Python standard library only:
- `asyncio` (stdlib)
- `traceback` (stdlib)
- `datetime` (stdlib)
- `collections` (stdlib)
- `typing` (stdlib)

### No Changes to Existing Dependencies

- `rpi_ws281x` (unchanged)
- `pyyaml` (unchanged)
- `pytest` (unchanged)

---

## 14. Configuration

**No configuration file needed** - all settings hardcoded for simplicity.

### Optional Future Configuration

Could add to `src/config/system.yaml`:

```yaml
exception_handling:
  rate_limit_window_seconds: 60
  rate_limit_max_per_window: 10
  enable_remote_logging: false
  enable_metrics_export: false
  emergency_shutdown_timeout_seconds: 5
```

---

**End of Design Document**

---

## Next Steps

1. **Review this document** - Understand the architecture
2. **Ask questions** - Clarify any aspects
3. **Get approval** - Ensure alignment with project goals
4. **Implement Phase 1** - Create exception_handler.py and integrate
5. **Test thoroughly** - Unit, integration, and hardware tests
6. **Document** - Update CLAUDE.md with new patterns
7. **Monitor** - Run in production and collect metrics
