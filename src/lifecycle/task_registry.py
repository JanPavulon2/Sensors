"""
Task Registry
-------------

Centralized tracking of asyncio tasks created across the application.
Provides introspection, debugging utilities, and controlled task lifecycle
management.

Features:
- Register tasks with metadata (category, description, origin)
- Track creation time, completion state, cancellation, errors
- Introspection API for debugging & frontend panels
- Optional automatic cleanup hooks during shutdown
"""

from __future__ import annotations

import asyncio
import traceback
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional, List, Callable, Any
from datetime import datetime, timezone

from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.TASK)


# ---------------------------------------------------------------------------
# TASK CATEGORY ENUM
# ---------------------------------------------------------------------------

class TaskCategory(Enum):
    """Logical grouping of asynchronous tasks."""
    API = auto()
    HARDWARE = auto()
    RENDER = auto()
    ANIMATION = auto()
    INPUT = auto()
    EVENTBUS = auto()
    TRANSITION = auto()
    SYSTEM = auto()
    BACKGROUND = auto()
    GENERAL = auto()


# ---------------------------------------------------------------------------
# TASK METADATA
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TaskInfo:
    """Immutable metadata captured at task creation time."""
    id: int
    category: TaskCategory
    description: str
    created_at: str  # ISO UTC string
    created_timestamp: float  # monotonic or epoch for sorting
    origin_stack: str  # short stack trace where create_tracked_task was called
    created_by: Optional[str] = None  # optional hint (module / function)


@dataclass
class TaskRecord:
    """Internal structure tracking task state."""
    task: asyncio.Task
    info: TaskInfo
    cancelled: bool = False
    finished_with_error: Optional[BaseException] = None
    finished_return: Optional[Any] = None
    finished_at: Optional[str] = None  # ISO time when finished
    finished_timestamp: Optional[float] = None  # monotonic/epoch

# ---------------------------------------------------------------------------
# TASK REGISTRY SINGLETON
# ---------------------------------------------------------------------------

class TaskRegistry:
    """
    Global registry for all asyncio tasks in the application.

    Responsibilities:
    - Track tasks and metadata
    - Detect and log task failures
    - Provide debugging API
    - Assist shutdown coordinator by exposing active tasks
    """

    _instance: Optional["TaskRegistry"] = None

    def __init__(self) -> None:
        # Protected by self._lock
        self._lock = asyncio.Lock()
        self._records: Dict[int, TaskRecord] = {}
        self._next_id: int = 1

    # -----------------------------
    # Singleton accessor
    # -----------------------------
    @classmethod
    def instance(cls) -> "TaskRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -----------------------------
    # Register new task
    # -----------------------------
    def register(
        self,
        task: asyncio.Task,
        category: TaskCategory,
        description: str,
        created_by: Optional[str] = None
    ) -> int:

        """Register a new task with metadata. Synchronous version."""
        task_id = self._next_id
        self._next_id += 1

        # Capture short stack (exclude internal frames)
        stack_lines = traceback.format_stack(limit=8)
        # Drop the last frame which will be inside this module
        origin_stack = "".join(stack_lines[:-1])

        now = datetime.now(timezone.utc)
        ts = now.timestamp()

        info = TaskInfo(
            id=task_id,
            category=category,
            description=description,
            created_at=now.isoformat(),
            created_timestamp=ts,
            origin_stack=origin_stack,
            created_by=created_by,
        )

        record = TaskRecord(task=task, info=info)
        self._records[task_id] = record

        log.debug(
            f"[Task {task_id}] Registered ({category.name}) - {description}"
        )

        # Auto-attach callback to track completion
        task.add_done_callback(self._on_task_done)

        return task_id

    # -----------------------------
    # Internal completion handler
    # -----------------------------
    def _on_task_done(self, task: asyncio.Task) -> None:
        """Internal callback whenever a task finishes."""
        record = self._get_record_by_task(task)
        if record is None:
            return

        if task.cancelled():
            record.cancelled = True
            log.debug(f"[Task {record.info.id}] Cancelled")
        else:
            exc = task.exception()
            if exc:
                record.finished_with_error = exc
                log.error(
                    f"[Task {record.info.id}] FAILED: {exc}",
                    exc_info=True
                )
            else:
                record.finished_return = task.result()
                log.debug(
                    f"[Task {record.info.id}] Completed successfully"
                )
                
    # -----------------------------
    # Utility: find record by task instance
    # -----------------------------
    def _get_record_by_task(self, task: asyncio.Task) -> Optional[TaskRecord]:
        for record in self._records.values():
            if record.task is task:
                return record
        return None

    # -----------------------------
    # Public API
    # -----------------------------

    def list_all(self) -> List[TaskRecord]:
        """Return a list of all tracked task records."""
        return list(self._records.values())

    def active(self) -> List[TaskRecord]:
        """Return only tasks that are still running."""
        return [
            r for r in self._records.values()
            if not r.task.done()
        ]

    def failed(self) -> List[TaskRecord]:
        """Return tasks that ended with an exception."""
        return [
            r for r in self._records.values()
            if r.finished_with_error is not None
        ]

    def cancelled(self) -> List[TaskRecord]:
        """Return cancelled tasks."""
        return [
            r for r in self._records.values()
            if r.cancelled
        ]

    def summary(self) -> str:
        """Return human-readable summary for logs."""
        total = len(self._records)
        running = len(self.active())
        failed = len(self.failed())
        cancelled = len(self.cancelled())

        return (
            f"Tasks: total={total}, running={running}, "
            f"failed={failed}, cancelled={cancelled}"
        )

    # -----------------------------
    # Shutdown helpers
    # -----------------------------

    def get_tasks_for_shutdown(
        self,
        exclude: Optional[List[asyncio.Task]] = None
    ) -> List[asyncio.Task]:
        """Return all tasks that should be cancelled during shutdown."""
        exclude = exclude or []
        tasks = [
            r.task for r in self._records.values()
            if not r.task.done() and r.task not in exclude
        ]

        log.debug(f"Shutdown: {len(tasks)} tasks to cancel")
        return tasks


# ---------------------------------------------------------------------------
# Convenience wrapper function
# ---------------------------------------------------------------------------

def create_tracked_task(
    coro,
    *,
    category: TaskCategory,
    description: str,
    loop: Optional[asyncio.AbstractEventLoop] = None
) -> asyncio.Task:
    """
    Create and register a task in a single call.
    """
    loop = loop or asyncio.get_running_loop()
    task = loop.create_task(coro)

    TaskRegistry.instance().register(
        task=task,
        category=category,
        description=description
    )

    return task
