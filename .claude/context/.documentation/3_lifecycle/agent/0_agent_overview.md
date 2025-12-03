---
Last Updated: 2025-12-02
Updated By: Claude Code
Changes: Agent documentation for lifecycle system
---

# Lifecycle System - Agent Implementation Guide

This document is for AI agents implementing changes to the task management and shutdown system.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                    Application (main)                    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  TaskRegistry ◄─── create_tracked_task()               │
│  (singleton)       (helper function)                    │
│      │                                                  │
│      │ (register)                                       │
│      ▼                                                  │
│  All tasks tracked with metadata                        │
│  - ID, category, description, timestamps               │
│  - Done callbacks monitor completion/exceptions        │
│                                                        │
│  ShutdownCoordinator ◄─── Signal Handler (SIGINT)     │
│      │                         │                        │
│      │ register()              │ sets event             │
│      ▼                         ▼                        │
│  Shutdown Handlers             shutdown_event          │
│  - Sorted by priority (DESC)                          │
│  - Called sequentially with timeout                    │
│  - Each handler has access to managed components      │
│                                                        │
│  REST API Routes ◄─── HTTP Requests                   │
│  /api/v1/system/*                                     │
│      │                                                  │
│      └─► Query TaskRegistry for introspection         │
│                                                        │
└──────────────────────────────────────────────────────────┘
```

## Key Classes

### 1. TaskRegistry (Singleton)

**File**: `src/lifecycle/task_registry.py`

**Responsibility**: Central registry of all asyncio tasks with metadata.

**Key Methods**:

```python
class TaskRegistry:
    @classmethod
    def instance(cls) -> "TaskRegistry":
        """Get singleton instance"""

    def register(
        self,
        task: asyncio.Task,
        category: TaskCategory,
        description: str,
        created_by: Optional[str] = None
    ) -> int:
        """Register task, return task ID"""

    def list_all(self) -> List[TaskRecord]:
        """Get all task records"""

    def active(self) -> List[TaskRecord]:
        """Get currently running tasks"""

    def failed(self) -> List[TaskRecord]:
        """Get tasks that ended with exceptions"""

    def cancelled(self) -> List[TaskRecord]:
        """Get tasks that were cancelled"""

    def summary(self) -> str:
        """Get human-readable summary"""
```

**How it works**:

1. Task is created via `create_tracked_task()`
2. Stored in `self._records` with metadata
3. Done callback attached to task
4. When task completes, callback updates record (stores exception, return value, etc.)
5. REST API queries registry for reports

**Thread Safety**: Uses `asyncio.Lock()` for async-safe access.

### 2. create_tracked_task() (Helper Function)

**File**: `src/lifecycle/task_registry.py`

**Purpose**: Convenience wrapper around `asyncio.create_task()` + `TaskRegistry.register()`

**Signature**:
```python
def create_tracked_task(
    coro: Awaitable,
    category: TaskCategory,
    description: str,
    created_by: Optional[str] = None
) -> asyncio.Task:
    """Create and register task in one call."""
```

**Usage**:
```python
# Instead of: asyncio.create_task(my_coroutine())
# Use:
create_tracked_task(
    my_coroutine(),
    category=TaskCategory.SYSTEM,
    description="My background worker"
)
```

**Why use it**:
- Ensures all tasks are tracked
- Provides metadata for debugging
- Allows REST API introspection
- Centralized task creation

### 3. ShutdownCoordinator

**File**: `src/lifecycle/shutdown_coordinator.py`

**Responsibility**: Orchestrates graceful shutdown of all components.

**Key Methods**:

```python
class ShutdownCoordinator:
    def __init__(self, timeout_per_handler: float = 5.0, total_timeout: float = 15.0):
        """Initialize with timeout settings"""

    def register(self, handler: IShutdownHandler) -> None:
        """Register a shutdown handler"""

    def setup_signal_handlers(self, loop: asyncio.AbstractEventLoop) -> None:
        """Install OS signal handlers (SIGINT, SIGTERM)"""

    async def wait_for_shutdown(self) -> None:
        """Block until shutdown event triggered"""

    async def shutdown_all(self) -> None:
        """Execute all handlers in priority order"""
```

**Timeout Management**:
- Each handler: 5 seconds (configurable)
- Total sequence: 15 seconds (configurable)
- On timeout: Logs warning and continues

### 4. IShutdownHandler Protocol

**File**: `src/lifecycle/shutdown_protocol.py`

**Definition**:
```python
class IShutdownHandler(Protocol):
    @property
    def shutdown_priority(self) -> int:
        """Priority for handler execution (higher = first)"""
        ...

    async def shutdown(self) -> None:
        """Perform shutdown for this component"""
        ...
```

**Priority Levels** (Convention):
```
100 - Hardware/LED shutdown (must happen first)
90  - Animation shutdown
80  - API server shutdown
50  - Controller shutdown
40  - Task cancellation
20  - GPIO cleanup (must happen last)
```

**Implementation Example**:
```python
class MyComponentShutdownHandler(IShutdownHandler):
    def __init__(self, component: MyComponent):
        self.component = component

    @property
    def shutdown_priority(self) -> int:
        return 50  # When to run relative to others

    async def shutdown(self) -> None:
        log.info("Stopping my component...")
        try:
            await self.component.stop()
            log.debug("✓ Component stopped")
        except Exception as e:
            log.error(f"Error stopping component: {e}")
```

## Core Files

### Implementation Files

| File | Purpose | Key Classes |
|------|---------|-------------|
| `src/lifecycle/task_registry.py` | Task tracking singleton | TaskRegistry, TaskInfo, TaskRecord |
| `src/lifecycle/shutdown_coordinator.py` | Shutdown orchestration | ShutdownCoordinator |
| `src/lifecycle/shutdown_protocol.py` | Shutdown interface | IShutdownHandler |
| `src/lifecycle/handlers/*.py` | Individual handlers | LEDShutdownHandler, APIServerShutdownHandler, etc. |
| `src/api/routes/system.py` | REST API endpoints | Task introspection endpoints |

### Entry Point

| File | Purpose | Key Function |
|------|---------|--------------|
| `src/main_asyncio.py` | App initialization | main() |

## Common Tasks

### Task 1: Add a New Shutdown Handler

**When**: A new component needs graceful shutdown.

**Steps**:

1. **Create handler file**: `src/lifecycle/handlers/my_component_shutdown_handler.py`

```python
from lifecycle.shutdown_protocol import IShutdownHandler
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SHUTDOWN)

class MyComponentShutdownHandler(IShutdownHandler):
    def __init__(self, component: MyComponent):
        self.component = component

    @property
    def shutdown_priority(self) -> int:
        return 50  # Choose appropriate priority

    async def shutdown(self) -> None:
        log.info("Stopping my component...")
        try:
            await self.component.stop()
            log.debug("✓ Component stopped")
        except Exception as e:
            log.error(f"Error stopping component: {e}")
```

2. **Register handler**: In `src/main_asyncio.py:main()`, after ShutdownCoordinator creation:

```python
coordinator = ShutdownCoordinator()
coordinator.register(LEDShutdownHandler(hardware))
coordinator.register(AnimationShutdownHandler(lighting_controller))
# ... existing handlers ...
coordinator.register(MyComponentShutdownHandler(my_component))  # ← Add here
```

3. **Choose priority**:
   - 100+ : Hardware/output (must be first)
   - 50 : Component-specific shutdown
   - 20- : Cleanup (must be last)

4. **Test shutdown**: Run app, press Ctrl+C, verify handler logs appear.

### Task 2: Add Task Category

**When**: You have a new type of background task.

**Steps**:

1. **Add to enum**: `src/lifecycle/task_registry.py:TaskCategory`

```python
class TaskCategory(Enum):
    API = auto()
    HARDWARE = auto()
    RENDER = auto()
    # ... existing ...
    MY_NEW_CATEGORY = auto()  # ← Add here
```

2. **Use in task creation**:

```python
create_tracked_task(
    my_coroutine(),
    category=TaskCategory.MY_NEW_CATEGORY,
    description="My task description"
)
```

3. **Check REST API**: `curl http://localhost:8000/api/v1/system/tasks`
   - New category should appear in task listings

### Task 3: Register a Long-Running Task

**When**: You have a background coroutine that should be tracked.

**Before** (untracked):
```python
async def some_work():
    while True:
        # do work
        await asyncio.sleep(1)

# In main():
asyncio.create_task(some_work())  # Not tracked!
```

**After** (tracked):
```python
from lifecycle.task_registry import create_tracked_task, TaskCategory

async def some_work():
    try:
        while True:
            # do work
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        log.debug("some_work cancelled")
        raise  # Important!

# In main():
task = create_tracked_task(
    some_work(),
    category=TaskCategory.SYSTEM,
    description="My background worker"
)
```

**Critical**: Always handle `asyncio.CancelledError` and re-raise!

### Task 4: Query Task Registry for Monitoring

**When**: Building dashboard/monitoring features.

**Usage**:
```python
from lifecycle.task_registry import TaskRegistry

registry = TaskRegistry.instance()

# Get all tasks
all_tasks = registry.list_all()

# Get running tasks
active = registry.active()

# Get failed tasks
failed = registry.failed()

# Get summary
summary = registry.summary()  # "Total: 8 | Active: 7 | Failed: 0 | Cancelled: 1"

# Iterate through task metadata
for record in all_tasks:
    print(f"Task {record.info.id}: {record.info.description}")
    print(f"  Status: {'running' if not record.task.done() else 'done'}")
    if record.finished_with_error:
        print(f"  Error: {record.finished_with_error}")
```

### Task 5: Improve Shutdown Robustness

**When**: Shutdown is hanging or tasks aren't cleaning up properly.

**Checklist**:

1. **Does handler re-raise CancelledError?**
   ```python
   # ✓ Correct
   try:
       while True:
           await asyncio.sleep(0.1)
   except asyncio.CancelledError:
       raise  # Re-raise!
   ```

2. **Is task waiting on something synchronous?**
   ```python
   # ✗ Wrong - will block shutdown
   result = some_sync_function()  # Blocks!

   # ✓ Correct - use async alternatives
   result = await async_function()  # Can be cancelled
   ```

3. **Does handler have appropriate timeout?**
   - If handler typically takes 100ms, 5s timeout is fine
   - If handler might take 2s, still fine
   - If handler might take 10s, increase timeout or refactor

4. **Is handler registered with correct priority?**
   - Handlers should run in dependency order
   - If handler depends on another (e.g., animations depend on frame manager), the dependency should shutdown first

## Debugging

### Debug: Task won't cancel

```python
# Add logging to see what's happening
async def my_task():
    log.debug("Task starting")
    try:
        while True:
            log.debug("About to sleep")
            await asyncio.sleep(1)
            log.debug("Woke up from sleep")
    except asyncio.CancelledError:
        log.debug("Caught CancelledError, cleaning up")
        raise
    except Exception as e:
        log.error(f"Unexpected error: {e}", exc_info=True)
        raise

# Run app and Ctrl+C
# Look for logs to see where it's stuck
```

### Debug: Find untracked tasks

```bash
# Get all tasks
curl -s http://localhost:8000/api/v1/system/tasks | jq '.count'

# Compare to expected task count
# If count keeps increasing, something is creating untracked tasks

# Or check with Python:
import asyncio
all_tasks = asyncio.all_tasks()
print(f"Total asyncio tasks: {len(all_tasks)}")

from lifecycle.task_registry import TaskRegistry
registry = TaskRegistry.instance()
print(f"Tracked tasks: {len(registry.list_all())}")

# If counts differ, something is untracked
```

### Debug: Shutdown timeout

Increase timeout if handlers are legitimately slow:

```python
# In main_asyncio.py:
coordinator = ShutdownCoordinator(
    timeout_per_handler=10.0,  # 10 seconds per handler
    total_timeout=60.0         # 60 seconds total
)
```

## Testing

### Test Shutdown Handler

```python
import pytest
import asyncio

async def test_my_handler_shutdown():
    """Test that handler shuts down cleanly"""
    mock_component = AsyncMock()
    handler = MyComponentShutdownHandler(mock_component)

    # Run handler
    await handler.shutdown()

    # Verify
    mock_component.stop.assert_called_once()
```

### Test Task Registration

```python
async def test_task_registration():
    """Test that tasks are tracked"""
    from lifecycle.task_registry import create_tracked_task, TaskRegistry

    async def dummy_task():
        await asyncio.sleep(0.1)

    task = create_tracked_task(
        dummy_task(),
        category=TaskCategory.SYSTEM,
        description="Test task"
    )

    registry = TaskRegistry.instance()
    active = registry.active()

    assert len(active) > 0
    assert any(r.info.description == "Test task" for r in active)

    # Wait for completion
    await task
```

## Performance Considerations

### Memory

- Each task adds ~300 bytes
- 100 tasks = ~30 KB
- 1000 tasks = ~300 KB
- Negligible for Raspberry Pi

### CPU

- Task registration: O(1)
- Querying registry: O(n) where n = task count
- Done callbacks: Minimal overhead
- REST API queries: <5ms even with 100 tasks

### Shutdown Time

- Per handler: 5 seconds (configurable)
- 6 handlers = ~30 seconds worst case
- But handlers run sequentially, typically < 1 second total

## See Also

- [User Overview](../user/0_overview.md) - Conceptual overview
- [Shutdown Sequence](../user/1_shutdown_sequence.md) - Detailed shutdown flow
- [Task Monitoring API](../user/2_task_monitoring_api.md) - REST API reference
- Source: `src/lifecycle/` - Implementation details
- Source: `src/api/routes/system.py` - API endpoints

