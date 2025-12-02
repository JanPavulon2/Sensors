# lifecycle/handlers/all_tasks_cancellation_handler.py

import asyncio
from typing import List, Optional
from datetime import datetime

from utils.logger import get_logger, LogCategory
from lifecycle.shutdown_protocol import IShutdownHandler
from lifecycle.task_registry import TaskRegistry

log = get_logger().for_category(LogCategory.SHUTDOWN)

class AllTasksCancellationHandler(IShutdownHandler):
    """
    Cancels *all* tracked asyncio tasks except the task that is currently
    executing this shutdown handler and any explicitly excluded tasks.
    This avoids recursive cancellation issues and infinite cancel cascades.
    """

    shutdown_priority = 30  # keep as before

    def __init__(self, exclude_tasks: Optional[List[asyncio.Task]] = None):
        """
        Initialize the handler with an optional list of tasks to exclude from cancellation.

        Args:
            exclude_tasks: List of asyncio.Task objects that should not be cancelled.
                          The current task is always excluded automatically.
        """
        self.exclude_tasks = exclude_tasks or []

    async def shutdown(self) -> None:
        current = asyncio.current_task()
        registry = TaskRegistry.instance()

        # ================================================================
        # 1) Build exclusion list: current task + explicitly excluded tasks
        # ================================================================
        exclude = []
        if current:
            exclude.append(current)
        exclude.extend(self.exclude_tasks)

        # ================================================================
        # 2) Receive flat list of tasks from registry
        # ================================================================
        tasks: List[asyncio.Task] = registry.get_tasks_for_shutdown(
            exclude=exclude if exclude else None
        )

        # Deduplicate (rare but safe)
        tasks = list({t for t in tasks})

        if not tasks:
            log.debug("AllTasksCancellationHandler: no tasks to cancel")
            return

        excluded_count = len(exclude)
        log.info(
            f"AllTasksCancellationHandler: cancelling {len(tasks)} background tasks "
            f"(excluding {excluded_count} task{'s' if excluded_count != 1 else ''})"
        )

        # ================================================================
        # 3) Cancel each task exactly once — SAFE CANCEL
        # ================================================================
        for t in tasks:
            if t is current:
                continue
            if t.done():
                continue

            try:
                t.cancel(msg="shutdown")
                log.debug(
                    f"[AllTasksCancellation] Cancelled task: {repr(t)}"
                )
            except Exception as e:
                log.error(
                    f"[AllTasksCancellation] Error cancelling task {t}: {e}",
                    exc_info=True
                )

        # ================================================================
        # 4) Wait a short grace period for cancellation propagation
        # ================================================================
        try:
            await asyncio.sleep(0.05)  # tiny grace for cancellations
        except asyncio.CancelledError:
            # IMPORTANT: handler cannot let cancellation propagate
            log.warn("AllTasksCancellationHandler was cancelled (ignored).")
            return

        log.info("AllTasksCancellationHandler completed successfully.")
