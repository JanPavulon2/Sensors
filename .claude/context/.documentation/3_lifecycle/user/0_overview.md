---
Last Updated: 2025-12-02
Updated By: Claude Code
Changes: Created comprehensive lifecycle and shutdown documentation
---

# Application Lifecycle and Shutdown System

**Purpose**: Understand how Diuna manages application startup, running tasks, and graceful shutdown.

## Quick Overview

Diuna uses a **priority-based shutdown system** to ensure safe, ordered cleanup of components. Every task is tracked in the **TaskRegistry** for real-time visibility, and the **ShutdownCoordinator** ensures all components shut down in the correct order.

```
Application Startup
       ↓
Long-running Tasks (tracked in TaskRegistry)
       ↓
Signal Received (Ctrl+C)
       ↓
ShutdownCoordinator triggers handlers in priority order
       ↓
Tasks cancelled and awaited
       ↓
GPIO cleaned up
       ↓
Exit
```

## Key Concepts

### 1. Application Initialization (`main()`)

The application follows a structured initialization sequence in `src/main_asyncio.py`:

1. **Infrastructure** - GPIO manager, configuration loading
2. **Services** - Event bus, animation service, zone service
3. **Hardware Coordinator** - LED strip initialization
4. **Frame Manager** - Rendering engine startup
5. **Controllers** - Mode controllers, input handlers
6. **Long-running Tasks** - API server, keyboard input, hardware polling
7. **Shutdown Coordinator** - Register shutdown handlers
8. **Signal Handlers** - Install OS signal handlers (SIGINT, SIGTERM)
9. **Main Loop** - Wait for shutdown event

**Key Pattern**: No blocking code. Everything is async tasks. Components are injected via constructors.

### 2. Task Registry - Real-Time Task Tracking

Every long-running task is registered in **TaskRegistry** with metadata:

- **Task ID** - Unique identifier
- **Category** - What type of work (API, HARDWARE, RENDER, ANIMATION, INPUT, SYSTEM, etc.)
- **Description** - Human-readable purpose
- **Created At** - Timestamp when task started
- **Status** - Running, completed, cancelled, or failed with exception

**Why it matters**:
- Frontend can show users "what is your app doing right now?"
- Debugging hangs: "is task X still running?"
- Monitoring: "did any tasks crash?"

### 3. Shutdown Coordinator - Ordered Component Cleanup

When you press Ctrl+C (SIGINT), the **ShutdownCoordinator** runs through all registered shutdown handlers in **priority order** (highest first):

```
Priority  Handler                      Purpose
────────  ──────────────────────────  ──────────────────────
100       LEDShutdownHandler           Clear LED pixels
90        AnimationShutdownHandler     Stop animation engine
80        APIServerShutdownHandler     Stop FastAPI server
50        TaskCancellationHandler      Cancel specific tasks
40        AllTasksCancellationHandler  Cancel remaining orphan tasks
20        GPIOShutdownHandler          Clean up GPIO pins
```

Each handler:
- Gets 5 seconds to complete
- Total shutdown sequence gets 15 seconds max
- Errors in one handler don't block others

### 4. Critical Tracked Tasks

These 5 tasks are explicitly tracked and used during shutdown:

1. **API Server** (`run_api_server()`)
   - FastAPI/Uvicorn on port 8000
   - Accepts HTTP requests for mode control, data retrieval
   - Priority: REST API

2. **Keyboard Input** (`KeyboardInputAdapter.run()`)
   - Listens for key presses for manual control
   - Emits events to event bus
   - Priority: User input

3. **Hardware Polling** (`hardware_polling_loop()`)
   - Polls control panel buttons at 50Hz
   - Detects user knob/button changes
   - Priority: Hardware input

4. **Animation Engine** (`AnimationEngine._main_loop()`)
   - Yields animation frames at 60 FPS
   - Runs active animations and transitions
   - Priority: Visual output

5. **LogBroadcaster** (`LogBroadcaster._broadcast_worker()`)
   - Broadcasts logs to WebSocket clients
   - Sends real-time logs to frontend
   - Priority: Monitoring/debugging

Plus additional infrastructure tasks:
- **Static Mode Pulse** - Brightness pulsing animation
- **Frame Playback** - Frame-by-frame debugging playback
- **Data Assembler** - State persistence to disk

## Normal Shutdown Flow

```
1. User presses Ctrl+C
   ↓
2. Signal handler sets shutdown_event
   ↓
3. Main loop awakens and calls coordinator.shutdown_all()
   ↓
4. Handlers execute in priority order:
   └─ LED Handler: Turn off all pixels
   └─ Animation Handler: Stop animations
   └─ API Handler: Stop FastAPI server
   └─ Task Handler: Cancel keyboard/polling/api tasks
   └─ All Tasks Handler: Cancel any orphan tasks
   └─ GPIO Handler: Cleanup GPIO pins
   ↓
5. Application exits cleanly
```

## Task Lifecycle

```
                 create_tracked_task()
                         ↓
         TaskRegistry.register(task, category, description)
                         ↓
         TaskInfo created with metadata (id, timestamp, etc)
                         ↓
          Task runs to completion (normal or exception)
                         ↓
         Task.add_done_callback() fires
                         ↓
      TaskRegistry._on_task_done() updates TaskRecord
                         ↓
      Task marked as completed/cancelled/failed in registry
```

## How to Monitor Tasks in Real-Time

Use the **REST API endpoints** to see what tasks are running:

```bash
# Get summary of all tasks
curl http://localhost:8000/api/v1/system/tasks/summary

# Get detailed info on all tasks
curl http://localhost:8000/api/v1/system/tasks

# Get only currently running tasks (useful for debugging hangs)
curl http://localhost:8000/api/v1/system/tasks/active

# Get failed tasks with exception details
curl http://localhost:8000/api/v1/system/tasks/failed

# Health check including task statistics
curl http://localhost:8000/api/v1/system/health
```

**Example Response** (`/tasks/active`):
```json
{
  "count": 5,
  "tasks": [
    {
      "id": 2,
      "category": "API",
      "description": "FastAPI/Uvicorn Server",
      "created_at": "2025-12-02T10:30:45.123456+00:00",
      "running_for_seconds": 45.2
    },
    {
      "id": 4,
      "category": "RENDER",
      "description": "Frame Manager renders loops",
      "created_at": "2025-12-02T10:30:46.234567+00:00",
      "running_for_seconds": 44.1
    }
  ]
}
```

## Common Issues

### Issue: App doesn't shut down cleanly

**Symptoms**: Pressing Ctrl+C doesn't exit, hangs for 15 seconds then force-quits

**Cause**: A task isn't responding to cancellation or is blocked in synchronous code

**Debug**:
```bash
# While app is running, check active tasks
curl http://localhost:8000/api/v1/system/tasks/active

# Look for tasks with very long running_for_seconds
# That's likely the one blocking shutdown
```

**Fix**: Make sure the task's coroutine handles `asyncio.CancelledError` properly:
```python
async def some_task():
    try:
        while True:
            # Do work
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        # Clean up
        log.debug("Task cancelled")
        raise  # Let cancellation propagate
```

### Issue: Untracked tasks not cleaned up

**Symptoms**: After shutdown, some tasks still running (zombie tasks)

**Cause**: Task created with `asyncio.create_task()` instead of `create_tracked_task()`

**Fix**: Use `create_tracked_task()` for any long-running background work:
```python
# ❌ WRONG - untracked
asyncio.create_task(some_coroutine())

# ✅ CORRECT - tracked in registry
create_tracked_task(
    some_coroutine(),
    category=TaskCategory.SYSTEM,
    description="Description of what this task does"
)
```

### Issue: "LED not turning off on exit"

**Symptoms**: LEDs stay on/show previous color after shutdown

**Cause**: LEDShutdownHandler not running or completing before GPIO cleanup

**Why it happens**: LEDShutdownHandler has priority 100 (first to run). If animations or frame manager haven't cleanly stopped, LED pixels may not be cleared properly.

**Fix**: Check animation and frame manager shutdown:
1. AnimationShutdownHandler (priority 90) stops animation engine
2. Frame manager should stop generating new frames
3. LEDShutdownHandler can then safely clear all pixels

## Performance & Constraints

### Shutdown Timeout Budget
- **Per handler**: 5 seconds
- **Total sequence**: 15 seconds

If a handler exceeds its timeout, it's logged as a warning but shutdown continues.

### Task Overhead
Each tracked task carries minimal overhead:
- ~200 bytes metadata per task
- No polling or periodic checks
- Done callbacks only execute when task completes

### Frame Rate
- **Render loop**: 60 FPS target (FrameManager)
- **Hardware polling**: 50 Hz (control panel buttons)
- **API server**: Runs in separate task, doesn't block rendering

## Hands-On Example: Adding a New Task

Want to add a new background task? Here's the process:

### Step 1: Create the coroutine
```python
async def my_background_work():
    try:
        while True:
            # Do work
            result = await do_something()
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        log.debug("My task cancelled")
        raise  # Important: re-raise to let shutdown handler know
    except Exception as e:
        log.error(f"Unexpected error: {e}", exc_info=True)
        raise
```

### Step 2: Register the task
```python
from lifecycle.task_registry import create_tracked_task, TaskCategory

# In your initialization code:
my_task = create_tracked_task(
    my_background_work(),
    category=TaskCategory.SYSTEM,  # or BACKGROUND, ANIMATION, etc.
    description="My background worker - does X, Y, and Z"
)
```

### Step 3: If needed, add shutdown handler
```python
from lifecycle.shutdown_protocol import IShutdownHandler

class MyTaskShutdownHandler(IShutdownHandler):
    def __init__(self, my_task: asyncio.Task):
        self.my_task = my_task

    @property
    def shutdown_priority(self) -> int:
        return 50  # When to run relative to other handlers

    async def shutdown(self) -> None:
        log.info("Stopping my task...")
        if not self.my_task.done():
            self.my_task.cancel()
            try:
                await self.my_task
            except asyncio.CancelledError:
                pass
        log.debug("My task stopped")

# In main():
coordinator.register(MyTaskShutdownHandler(my_task))
```

### Step 4: Verify task appears in REST API
```bash
curl http://localhost:8000/api/v1/system/tasks
# Should see your task in the list
```

## References

- **Entry Point**: `src/main_asyncio.py` - Complete initialization sequence
- **Task Registry**: `src/lifecycle/task_registry.py` - Task tracking and introspection
- **Shutdown System**: `src/lifecycle/shutdown_coordinator.py` - Handler orchestration
- **REST API**: `src/api/routes/system.py` - Task introspection endpoints
- **Emergency Cleanup**: `src/main_asyncio.py:109-120` - Last-resort GPIO cleanup via atexit

