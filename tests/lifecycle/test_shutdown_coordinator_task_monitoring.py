"""
Test shutdown coordinator's critical task monitoring capability.
"""

import asyncio
import sys
import contextlib
from pathlib import Path

# Set UTF-8 encoding for output (fixes Unicode symbol rendering)
if hasattr(sys.stdout, 'reconfigure') and sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
if hasattr(sys.stderr, 'reconfigure') and sys.stderr.encoding != 'UTF-8':
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from lifecycle.shutdown_coordinator import ShutdownCoordinator
from lifecycle.task_registry import create_tracked_task, TaskCategory, TaskRegistry


async def test_wait_for_shutdown_on_signal():
    """Test that wait_for_shutdown returns on SIGINT."""
    print("\n[TEST 1] Testing normal shutdown signal...")

    coordinator = ShutdownCoordinator()
    loop = asyncio.get_running_loop()
    coordinator.setup_signal_handlers(loop)

    # Create a dummy critical task that won't fail
    async def dummy_task():
        """A task that just sleeps."""
        while True:
            await asyncio.sleep(0.1)

    task = create_tracked_task(
        dummy_task(),
        category=TaskCategory.HARDWARE,
        description="Dummy test task"
    )

    # Simulate SIGINT after 0.5 seconds
    async def send_signal():
        await asyncio.sleep(0.5)
        coordinator._shutdown_event.set()

    signal_task = asyncio.create_task(send_signal())

    try:
        # Should return when signal is set
        await asyncio.wait_for(
            coordinator.wait_for_shutdown(),
            timeout=2.0
        )
        print("  ✓ Shutdown coordinator returned on signal")
        return True
    except asyncio.TimeoutError:
        print("  ❌ Timeout - coordinator didn't return on signal")
        return False
    finally:
        task.cancel()
        signal_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
            await signal_task


async def test_wait_for_shutdown_on_task_failure():
    """Test that wait_for_shutdown returns when critical task fails."""
    print("\n[TEST 2] Testing critical task failure detection...")

    coordinator = ShutdownCoordinator()
    loop = asyncio.get_running_loop()
    coordinator.setup_signal_handlers(loop)

    # Create a critical task that will fail
    async def failing_task():
        """A task that fails immediately."""
        await asyncio.sleep(0.1)
        raise RuntimeError("Simulated critical task failure")

    critical_task = create_tracked_task(
        failing_task(),
        category=TaskCategory.API,
        description="Failing API task"
    )

    # Create a background task to prevent hang
    async def timeout_handler():
        await asyncio.sleep(3.0)
        # Force stop if timeout
        if not coordinator._shutdown_event.is_set():
            coordinator._shutdown_event.set()

    timeout_task = asyncio.create_task(timeout_handler())

    try:
        # Should return when critical task fails
        await asyncio.wait_for(
            coordinator.wait_for_shutdown(),
            timeout=2.0
        )

        # Check that shutdown was triggered due to task failure
        reason = coordinator._shutdown_trigger.get("reason")
        if "Task failure" in str(reason):
            print(f"  ✓ Shutdown triggered on task failure: {reason}")
            return True
        else:
            print(f"  ❌ Shutdown triggered but reason unclear: {reason}")
            return False
    except asyncio.TimeoutError:
        print("  ❌ Timeout - coordinator didn't detect task failure")
        return False
    finally:
        timeout_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, RuntimeError):
            await critical_task
            await timeout_task


async def test_registry_query():
    """Test that coordinator can query TaskRegistry."""
    print("\n[TEST 3] Testing TaskRegistry integration...")

    coordinator = ShutdownCoordinator()

    # Create some tracked tasks
    async def dummy():
        await asyncio.sleep(10)

    t1 = create_tracked_task(dummy(), category=TaskCategory.API, description="API task")
    t2 = create_tracked_task(dummy(), category=TaskCategory.HARDWARE, description="HW task")
    t3 = create_tracked_task(dummy(), category=TaskCategory.ANIMATION, description="Animation task")

    try:
        # Get critical tasks
        categories = coordinator._get_critical_task_categories()
        critical_tasks = coordinator._get_critical_tasks_from_registry(categories)

        # Should have 2 critical tasks (API, HARDWARE)
        if len(critical_tasks) >= 2:
            print(f"  ✓ Found {len(critical_tasks)} critical tasks (expected >= 2)")
            return True
        else:
            print(f"  ❌ Found {len(critical_tasks)} critical tasks (expected >= 2)")
            return False
    finally:
        t1.cancel()
        t2.cancel()
        t3.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.gather(t1, t2, t3)


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing ShutdownCoordinator Task Monitoring")
    print("=" * 60)

    results = []

    try:
        results.append(await test_registry_query())
        results.append(await test_wait_for_shutdown_on_signal())
        results.append(await test_wait_for_shutdown_on_task_failure())
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
