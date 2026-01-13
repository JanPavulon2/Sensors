---
Last Updated: 2025-12-02
Updated By: Claude Code
Changes: Implementation patterns and best practices
---

# Lifecycle Implementation Patterns

Common patterns for working with TaskRegistry, ShutdownCoordinator, and graceful shutdown.

## Pattern 1: Create and Track a Long-Running Task

**Use when**: You have a background coroutine that needs to run for the app's lifetime.

**Template**:

```python
from lifecycle.task_registry import create_tracked_task, TaskCategory
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.YOUR_CATEGORY)

async def my_long_running_task():
    """Background worker that runs until shutdown."""
    try:
        log.debug("Starting my worker")

        while True:
            try:
                # Do work here
                result = await do_some_work()

                # Sleep without blocking shutdown
                await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                # Shutdown requested - clean up and propagate
                log.debug("Worker cancelled during operation")
                raise
            except Exception as e:
                # Unexpected error - log but continue
                log.error(f"Error in worker: {e}", exc_info=True)
                await asyncio.sleep(1.0)  # Backoff on error

    except asyncio.CancelledError:
        # Final cleanup
        log.debug("Worker shutting down")
        raise
    except Exception as e:
        log.error(f"Worker crashed: {e}", exc_info=True)
        raise

# In main():
my_task = create_tracked_task(
    my_long_running_task(),
    category=TaskCategory.SYSTEM,
    description="My background worker - does X"
)
```

**Key points**:
- Use `try/except` for both inner and outer loops
- Re-raise `CancelledError` to signal shutdown
- Use `await asyncio.sleep()` instead of `time.sleep()`
- Log errors but continue (don't crash the whole app)
- Log when cancellation is received

## Pattern 2: Task with Graceful Shutdown

**Use when**: Your task needs to clean up resources on shutdown.

**Template**:

```python
async def my_cleanup_task():
    """Task that manages resources."""
    resources = []

    try:
        log.info("Allocating resources")
        resource1 = await allocate_resource()
        resources.append(resource1)

        # Main loop
        while True:
            await do_work_with(resource1)
            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        log.info("Cleanup task cancelled, releasing resources")
        try:
            for resource in resources:
                await resource.cleanup()
            log.debug("✓ All resources released")
        except Exception as e:
            log.error(f"Error during cleanup: {e}")
        raise  # Important: re-raise to complete shutdown
```

**Key points**:
- Allocate resources before main loop
- Use try/finally or try/except for cleanup
- Always re-raise `CancelledError` after cleanup
- Log what you're cleaning up

## Pattern 3: Task with Timeout-Safe Shutdown

**Use when**: Your task has operations that might hang.

**Template**:

```python
async def my_timeout_task():
    """Task that handles hung operations."""
    try:
        while True:
            try:
                # This operation might hang
                result = await asyncio.wait_for(
                    potentially_hanging_operation(),
                    timeout=5.0  # Timeout after 5 seconds
                )
                await process(result)

            except asyncio.TimeoutError:
                log.warn("Operation timed out, retrying")
                continue

            except asyncio.CancelledError:
                # Shutdown - stop waiting
                raise

            except Exception as e:
                log.error(f"Operation failed: {e}")
                await asyncio.sleep(1.0)

    except asyncio.CancelledError:
        log.debug("Timeout task cancelled")
        raise
```

**Key points**:
- Use `asyncio.wait_for(..., timeout=X)` for timeout protection
- Catch `TimeoutError` separately from `CancelledError`
- Always let `CancelledError` propagate

## Pattern 4: Custom Shutdown Handler

**Use when**: A component needs specific shutdown logic not handled by tasks.

**Template**:

```python
# File: src/lifecycle/handlers/my_component_shutdown_handler.py

from lifecycle.shutdown_protocol import IShutdownHandler
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SHUTDOWN)

class MyComponentShutdownHandler(IShutdownHandler):
    """Gracefully shut down MyComponent."""

    def __init__(self, component: MyComponent, dependency: OtherComponent):
        self.component = component
        self.dependency = dependency

    @property
    def shutdown_priority(self) -> int:
        """
        Run after animation (90) but before tasks (40).
        Return 50 to be in the middle.
        """
        return 50

    async def shutdown(self) -> None:
        """Perform graceful shutdown."""
        log.info(f"Stopping {self.component.__class__.__name__}...")

        try:
            # Stop accepting new work
            self.component.pause()
            log.debug("  Component paused")

            # Finish in-flight operations
            await asyncio.wait_for(
                self.component.finish_pending(),
                timeout=3.0
            )
            log.debug("  Pending operations finished")

            # Release resources
            await self.component.cleanup()
            log.debug("✓ Component shutdown complete")

        except asyncio.TimeoutError:
            log.warn(f"  Component shutdown timed out")
        except Exception as e:
            log.error(f"  Error during shutdown: {e}", exc_info=True)
            # Continue anyway - don't block other handlers


# In main_asyncio.py:
my_component = MyComponent()
other_component = OtherComponent()

coordinator = ShutdownCoordinator()
coordinator.register(MyComponentShutdownHandler(my_component, other_component))
```

**Key points**:
- Choose priority to reflect dependencies
- Always catch exceptions (don't raise them)
- Use timeouts for potentially slow operations
- Log each step for debugging
- Handlers run sequentially, so don't block

## Pattern 5: Monitor Task Status

**Use when**: You need to check if a task is running or has failed.

**Template**:

```python
from lifecycle.task_registry import TaskRegistry

async def check_task_health():
    """Periodically check task health."""
    registry = TaskRegistry.instance()

    while True:
        try:
            # Check for failed tasks
            failed = registry.failed()
            if failed:
                for record in failed:
                    log.warn(
                        f"Task {record.info.id} ({record.info.description}) "
                        f"failed: {record.finished_with_error}"
                    )

            # Check for hung tasks
            active = registry.active()
            for record in active:
                elapsed = datetime.now(timezone.utc).timestamp() - record.info.created_timestamp
                if elapsed > 300:  # Running for 5+ minutes?
                    log.warn(
                        f"Task {record.info.id} ({record.info.description}) "
                        f"running for {elapsed:.0f}s"
                    )

            await asyncio.sleep(30)  # Check every 30 seconds

        except asyncio.CancelledError:
            log.debug("Health checker cancelled")
            raise
        except Exception as e:
            log.error(f"Error checking health: {e}")
            await asyncio.sleep(30)
```

**Key points**:
- Query registry periodically
- Look for failed tasks
- Look for tasks running too long
- Report but don't raise (don't crash app)

## Pattern 6: Fire-and-Forget Task

**Use when**: You have work that doesn't need to be awaited.

**Template**:

```python
# Create a tracked task without awaiting
background_task = create_tracked_task(
    my_coroutine(),
    category=TaskCategory.BACKGROUND,
    description="Fire-and-forget operation"
)
# Don't await it - it runs in background
# But it's tracked, so shutdown coordinator will cancel it

# OR, add callback to handle completion
def on_task_done(task):
    if task.exception():
        log.error(f"Background task failed: {task.exception()}")
    else:
        log.debug(f"Background task completed: {task.result()}")

background_task.add_done_callback(on_task_done)
```

**Key points**:
- Use `create_tracked_task()` to ensure tracking
- Don't use bare `asyncio.create_task()`
- Add `done_callback()` if you need to know when it completes
- Shutdown coordinator will cancel it automatically

## Pattern 7: Task with Resource Management

**Use when**: Your task manages external resources (files, network, database).

**Template**:

```python
class ResourceManager:
    """Manages a resource safely."""

    async def __aenter__(self):
        log.debug("Opening resource")
        self.resource = await open_resource()
        return self.resource

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        log.debug("Closing resource")
        try:
            await self.resource.close()
        except Exception as e:
            log.error(f"Error closing resource: {e}")
        return False  # Don't suppress exceptions

async def my_task_with_resources():
    """Task that uses managed resources."""
    try:
        async with ResourceManager() as resource:
            while True:
                result = await resource.read()
                await process(result)
                await asyncio.sleep(1)

    except asyncio.CancelledError:
        log.debug("Task cancelled (resource will auto-close)")
        raise
```

**Key points**:
- Use `async with` for automatic cleanup
- Implement `__aenter__` and `__aexit__`
- CancelledError will still trigger cleanup
- Resources are released before task completes

## Pattern 8: Task Coordination

**Use when**: Multiple tasks need to coordinate or wait for each other.

**Template**:

```python
# Shared event
startup_complete = asyncio.Event()
shutdown_requested = asyncio.Event()

async def task1():
    """First task - signals when ready."""
    try:
        log.info("Task 1 starting")
        await initialize_something()
        log.info("Task 1 ready")

        startup_complete.set()  # Signal other tasks

        # Main loop
        while not shutdown_requested.is_set():
            await do_work()
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        log.debug("Task 1 cancelled")
        raise

async def task2():
    """Second task - waits for task 1."""
    try:
        # Wait for task 1 to start
        await startup_complete.wait()
        log.info("Task 2 starting (task 1 is ready)")

        # Main loop
        while not shutdown_requested.is_set():
            await do_work()
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        log.debug("Task 2 cancelled")
        raise

# In main():
task1 = create_tracked_task(task1(), category=TaskCategory.SYSTEM, description="Task 1")
task2 = create_tracked_task(task2(), category=TaskCategory.SYSTEM, description="Task 2")

# When shutdown:
shutdown_requested.set()
```

**Key points**:
- Use `asyncio.Event()` for task coordination
- Tasks can wait for events without blocking
- Events can be checked before sleeping
- Shutdown can signal all tasks at once

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Blocking Async Code

```python
# WRONG - blocks event loop
while True:
    result = some_blocking_function()  # This BLOCKS!
    await asyncio.sleep(1)

# CORRECT - use async alternatives
while True:
    result = await some_async_function()
    await asyncio.sleep(1)
```

### ❌ Anti-Pattern 2: Ignoring CancelledError

```python
# WRONG - swallows cancellation
try:
    while True:
        await asyncio.sleep(1)
except asyncio.CancelledError:
    log.debug("Cancelled")
    # Don't re-raise! This is WRONG!

# CORRECT - re-raise to propagate shutdown
try:
    while True:
        await asyncio.sleep(1)
except asyncio.CancelledError:
    log.debug("Cancelled")
    raise  # Always re-raise!
```

### ❌ Anti-Pattern 3: Untracked Tasks

```python
# WRONG - task not tracked
asyncio.create_task(my_coroutine())

# CORRECT - use create_tracked_task()
create_tracked_task(
    my_coroutine(),
    category=TaskCategory.SYSTEM,
    description="Description"
)
```

### ❌ Anti-Pattern 4: Synchronous Shutdown

```python
# WRONG - blocking shutdown
def shutdown():
    component.stop()  # Synchronous!
    database.close()  # Synchronous!

# CORRECT - async shutdown
async def shutdown():
    await component.stop()
    await database.close()
```

### ❌ Anti-Pattern 5: Multiple Shutdown Handlers

```python
# WRONG - task cancels itself
async def my_task():
    # ...has a shutdown handler registered...
    # ...but main() also cancels it...
    # Double cancellation!

# CORRECT - either:
# Option 1: Use handler, not manual cancellation
# Option 2: Use manual cancellation, not handler
# Don't do both!
```

## Debugging Patterns

### Pattern: Add Logging for Shutdown

```python
async def my_task():
    try:
        log.debug("Task starting")
        while True:
            log.debug("About to do work")
            await do_work()
            log.debug("Work done, sleeping")
            await asyncio.sleep(1)
            log.debug("Woke up")

    except asyncio.CancelledError:
        log.debug("Task caught CancelledError")
        try:
            log.debug("Cleaning up resources")
            await cleanup()
            log.debug("Cleanup complete")
        except Exception as e:
            log.error(f"Cleanup failed: {e}")
        log.debug("Re-raising CancelledError")
        raise
```

This helps trace exactly where the task is when shutdown happens.

### Pattern: Test Task Cancellation

```python
async def test_task_shutdown():
    """Test that task shuts down cleanly."""
    task = create_tracked_task(
        my_task(),
        category=TaskCategory.SYSTEM,
        description="Test"
    )

    # Let it run briefly
    await asyncio.sleep(0.1)

    # Cancel it
    task.cancel()

    # Should complete without error
    with pytest.raises(asyncio.CancelledError):
        await task
```

## See Also

- [Agent Overview](./0_agent_overview.md) - Architecture and key classes
- [User Shutdown Sequence](../user/1_shutdown_sequence.md) - How shutdown actually happens
- Source: `src/lifecycle/task_registry.py` - Task tracking
- Source: `src/lifecycle/shutdown_coordinator.py` - Shutdown orchestration

