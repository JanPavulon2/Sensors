
"""
Shutdown coordinator that orchestrates graceful shutdown of all components.

Manages signal handlers, shutdown sequencing, and error handling across
multiple shutdown handlers in priority order.
"""

import asyncio
import signal
from typing import List, Optional, Dict, Any, Set
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SYSTEM)

# Import TaskRegistry for critical task monitoring
# (deferred import to avoid circular dependencies)
TaskRegistry = None
TaskCategory = None

def _get_task_registry():
    """Lazy import to avoid circular dependencies."""
    global TaskRegistry, TaskCategory
    if TaskRegistry is None:
        from lifecycle.task_registry import TaskRegistry as TR, TaskCategory as TC
        TaskRegistry = TR
        TaskCategory = TC
    return TaskRegistry, TaskCategory


class ShutdownCoordinator:
    """
    Coordinates graceful shutdown of multiple components.

    Maintains a list of shutdown handlers and executes them in priority order
    when shutdown is triggered. Handles signal registration, timeout management,
    and error logging.

    Example:
        coordinator = ShutdownCoordinator()
        coordinator.register(LEDShutdownHandler(...))
        coordinator.register(APIServerShutdownHandler(...))
        coordinator.register(GPIOShutdownHandler(...))

        coordinator.setup_signal_handlers()
        await coordinator.wait_for_shutdown()
        await coordinator.shutdown_all()
    """

    def __init__(self, timeout_per_handler: float = 5.0, total_timeout: float = 15.0):
        """
        Initialize shutdown coordinator.

        Args:
            timeout_per_handler: Timeout for each individual handler (seconds)
            total_timeout: Total timeout for entire shutdown sequence (seconds)
        """
        self._handlers: List = []
        self._shutdown_event: Optional[asyncio.Event] = None
        self._timeout_per_handler = timeout_per_handler
        self._total_timeout = total_timeout
        self._shutdown_trigger: Dict[str, Optional[str]] = {"reason": None}

    def register(self, handler) -> None:
        """
        Register a shutdown handler.

        Handler must have:
        - shutdown_priority property (int)
        - async shutdown() method

        Args:
            handler: Object implementing ShutdownHandler protocol
        """
        if not hasattr(handler, "shutdown_priority"):
            raise ValueError(f"Handler {handler} missing shutdown_priority property")
        if not hasattr(handler, "shutdown"):
            raise ValueError(f"Handler {handler} missing shutdown() method")

        self._handlers.append(handler)
        log.debug(f"Registered shutdown handler: {handler.__class__.__name__}")

    def setup_signal_handlers(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        Install OS signal handlers for graceful shutdown.

        Registers SIGINT (Ctrl+C) and SIGTERM for graceful shutdown.

        Args:
            loop: Running asyncio event loop
        """
        self._shutdown_event = asyncio.Event()
        shutdown_event = self._shutdown_event  # Capture for closure

        def signal_handler(sig: signal.Signals) -> None:
            """Handle OS signal by triggering shutdown event."""
            self._shutdown_trigger["reason"] = sig.name
            log.info(f"Signal {sig.name} received → triggering shutdown")
            shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

        log.info("Signal handlers installed (SIGINT, SIGTERM)")

    def _get_critical_task_categories(self) -> Set[str]:
        """
        Define which task categories are critical to the application.

        Returns:
            Set of TaskCategory names that should trigger shutdown if they fail.
        """
        return {
            "API",       # API server must remain healthy
            "HARDWARE",  # Hardware polling/control panel
            "RENDER",    # Frame manager for LED rendering
            "INPUT",     # User input handling
        }

    def _get_critical_tasks_from_registry(
        self, critical_categories: Set[str]
    ) -> List[asyncio.Task]:
        """
        Query TaskRegistry for all active tasks in critical categories.

        Args:
            critical_categories: Set of TaskCategory names to monitor

        Returns:
            List of active asyncio.Task objects in critical categories
        """
        TR, TC = _get_task_registry()
        if TR is None:
            return []

        registry = TR.instance()
        active_records = registry.active()

        return [
            r.task for r in active_records
            if r.info.category.name in critical_categories
        ]

    def _check_critical_task_failures(self, critical_categories: Set[str]) -> bool:
        """
        Check if any critical task has already failed.

        Sets shutdown trigger and logs the failure.

        Args:
            critical_categories: Set of TaskCategory names to check

        Returns:
            True if a critical task failure was detected, False otherwise
        """
        TR, TC = _get_task_registry()
        if TR is None:
            return False

        registry = TR.instance()
        failed_records = registry.failed()

        for failed_record in failed_records:
            if failed_record.info.category.name in critical_categories:
                log.error(
                    f"❌ Critical task failed: {failed_record.info.description} "
                    f"(category: {failed_record.info.category.name})"
                )
                self._shutdown_trigger["reason"] = (
                    f"Task failure: {failed_record.info.description}"
                )
                return True

        return False

    async def _wait_for_critical_task_completion(
        self, critical_tasks: List[asyncio.Task]
    ) -> Optional[bool]:
        """
        Wait for either shutdown signal or critical task failure.

        Args:
            critical_tasks: Tasks to monitor

        Returns:
            True if shutdown signal received
            False if a critical task FAILED (not just completed)
            None if timeout (continue monitoring)
        """
        if not critical_tasks:
            # No tasks to monitor, wait for signal with timeout
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=0.2
                )
                return True  # Signal received
            except asyncio.TimeoutError:
                return None  # Keep monitoring

        # Build wait set
        wait_set: Set[asyncio.Task] = set(critical_tasks)
        shutdown_waiter = asyncio.create_task(self._shutdown_event.wait())
        wait_set.add(shutdown_waiter)

        try:
            done, pending = await asyncio.wait(
                wait_set,
                return_when=asyncio.FIRST_COMPLETED
            )

            # Check what completed
            for completed_task in done:
                if completed_task is shutdown_waiter:
                    return True  # Shutdown signal received

                # Critical task completed - check if it failed
                task_failed = self._handle_critical_task_completion(completed_task)
                if task_failed:
                    return False  # Task failed, trigger shutdown
                # else: task completed cleanly, continue monitoring
                return None  # Keep waiting
        finally:
            # IMPORTANT: Only cancel the shutdown_waiter, NOT the critical tasks.
            # Critical tasks are long-lived and should persist across loop iterations.
            # They will be monitored again in the next call.
            if not shutdown_waiter.done():
                shutdown_waiter.cancel()

    def _handle_critical_task_completion(self, completed_task: asyncio.Task) -> bool:
        """
        Handle the completion of a critical task.

        ONLY triggers shutdown if the task FAILED (threw exception).
        If a task completed cleanly (no exception), log it but don't shutdown.

        Rationale: Some tasks (like FrameManager.start()) are designed to
        complete quickly after spawning background work. Clean completion ≠ failure.

        Args:
            completed_task: The task that completed

        Returns:
            True if task failed (should trigger shutdown), False if completed cleanly
        """
        if completed_task.cancelled():
            return False  # Cancellation is expected during shutdown

        TR, TC = _get_task_registry()
        if TR is None:
            task_name = completed_task.get_name()
            # No registry access, can't determine if it failed
            log.debug(f"ℹ️  Critical task completed: {task_name}")
            return False  # Assume it's fine without error info

        registry = TR.instance()
        record = registry._get_record_by_task(completed_task)
        task_name = (
            record.info.description
            if record
            else completed_task.get_name()
        )

        # Check if task actually FAILED (has exception)
        if record and record.finished_with_error:
            log.error(f"❌ Critical task failed: {task_name} - {record.finished_with_error}")
            self._shutdown_trigger["reason"] = f"Task failure: {task_name}"
            return True  # Task failed, should trigger shutdown

        # Task completed cleanly - that's fine
        log.debug(f"ℹ️  Critical task completed cleanly: {task_name}")
        return False  # Don't trigger shutdown

    async def wait_for_shutdown(self) -> None:
        """
        Wait for shutdown event or critical task failure.

        Monitors both:
        1. OS signals (Ctrl+C, SIGTERM)
        2. Critical application tasks via TaskRegistry

        Returns immediately when:
        - Shutdown signal is received, OR
        - Any critical task fails/completes unexpectedly

        Raises:
            RuntimeError: If signal handlers weren't setup
        """
        if self._shutdown_event is None:
            raise RuntimeError("Call setup_signal_handlers() first")

        critical_categories = self._get_critical_task_categories()

        # Main monitoring loop
        while not self._shutdown_event.is_set():
            # Check if any critical task already failed
            if self._check_critical_task_failures(critical_categories):
                return

            # Get current active critical tasks
            critical_tasks = self._get_critical_tasks_from_registry(
                critical_categories
            )

            # Wait for shutdown signal or task completion
            result = await self._wait_for_critical_task_completion(critical_tasks)

            if result is True or self._shutdown_event.is_set():
                # Shutdown signal received
                log.debug("Shutdown triggered by signal handler")
                return
            elif result is False:
                # Critical task failed
                return
            # else: timeout, loop again

    async def shutdown_all(self) -> None:
        """
        Execute graceful shutdown of all handlers in priority order.

        Handlers are called in descending priority order (highest first).
        Includes timeout management and error handling.

        Each handler has its own timeout (timeout_per_handler) and the entire
        shutdown sequence has a global timeout (total_timeout).
        """
        log.info("🛑 Initiating graceful shutdown sequence...")
        reason = self._shutdown_trigger.get("reason", "UNKNOWN")
        log.info(f"   Reason: {reason}")

        # Sort by priority (highest first)
        sorted_handlers = sorted(
            self._handlers, key=lambda h: h.shutdown_priority, reverse=True
        )

        start_time = asyncio.get_event_loop().time()

        try:
            for handler in sorted_handlers:
                handler_name = handler.__class__.__name__
                priority = handler.shutdown_priority

                # Check if total timeout exceeded
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self._total_timeout:
                    log.error(
                        f"⚠️  Total shutdown timeout exceeded ({elapsed:.1f}s > {self._total_timeout}s)"
                    )
                    break

                try:
                    log.debug(
                        f"Shutting down {handler_name} (priority={priority})..."
                    )

                    # Call shutdown with timeout
                    await asyncio.wait_for(
                        handler.shutdown(), timeout=self._timeout_per_handler
                    )

                    log.debug(f"✓ {handler_name} shutdown complete")

                except asyncio.TimeoutError:
                    log.error(
                        f"⚠️  {handler_name} shutdown timeout "
                        f"({self._timeout_per_handler}s)"
                    )

                except asyncio.CancelledError:
                    log.debug(f"{handler_name} shutdown was cancelled")
                    raise

                except Exception as e:
                    log.error(
                        f"❌ Error shutting down {handler_name}: {e}", exc_info=True
                    )
                    # Continue with other handlers even if one fails

            log.info("✓ Shutdown sequence complete")

        except asyncio.CancelledError:
            log.warn("Shutdown sequence was cancelled")
            raise
        except Exception as e:
            log.error(f"Unexpected error during shutdown: {e}", exc_info=True)

    def get_handler(self, handler_type: type):
        """
        Get a registered handler by type.

        Useful for testing or debugging.

        Args:
            handler_type: The handler class to find

        Returns:
            Handler instance or None if not found
        """
        for handler in self._handlers:
            if isinstance(handler, handler_type):
                return handler
        return None