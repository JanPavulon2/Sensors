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
from dataclasses import dataclass, field, asdict
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

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON transmission."""
        return {
            "id": self.id,
            "category": self.category.name,
            "description": self.description,
            "created_at": self.created_at,
            "created_timestamp": self.created_timestamp,
            "created_by": self.created_by,
            # origin_stack skipped for frontend (too verbose, breaks serialization)
        }


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
    parent_task_id: Optional[int] = None  # Track parent task if hierarchical

    def get_status(self) -> str:
        """Return current task status."""
        if self.cancelled:
            return "cancelled"
        elif self.finished_with_error is not None:
            return "failed"
        elif self.task.done():
            return "completed"
        else:
            return "running"

    def get_duration(self) -> Optional[float]:
        """Return task duration in seconds (or None if still running)."""
        if self.finished_timestamp is None:
            return None
        return self.finished_timestamp - self.info.created_timestamp

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON transmission."""
        error_str = None
        if self.finished_with_error is not None:
            error_str = f"{type(self.finished_with_error).__name__}: {str(self.finished_with_error)}"

        return {
            **self.info.to_dict(),
            "status": self.get_status(),
            "finished_at": self.finished_at,
            "finished_timestamp": self.finished_timestamp,
            "error": error_str,
            "duration": self.get_duration(),
            "parent_task_id": self.parent_task_id,
        }

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

    broadcasting_enabled = True
    
    _instance: Optional["TaskRegistry"] = None

    def __init__(self) -> None:
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

        # Broadcast task creation event (non-blocking)
        try:
            asyncio.create_task(self._broadcast_task_event("task:created", record.to_dict()))
        except RuntimeError:
            # No event loop running (e.g., during app shutdown)
            pass

        return task_id

    # -----------------------------
    # Internal completion handler
    # -----------------------------
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
            log.debug(f"{task_label} - Cancelled")
            # Broadcast cancellation event
            try:
                asyncio.create_task(self._broadcast_task_event("task:cancelled", record.to_dict()))
            except RuntimeError:
                pass
        else:
            exc = task.exception()
            if exc:
                record.finished_with_error = exc
                log.error(
                    f"{task_label} - FAILED: {exc}",
                    exc_info=True
                )
                # Broadcast failure event
                try:
                    asyncio.create_task(self._broadcast_task_event("task:failed", record.to_dict()))
                except RuntimeError:
                    pass
            else:
                record.finished_return = task.result()
                log.info(
                    f"{task_label} - Completed successfully"
                )
                # Broadcast completion event
                try:
                    asyncio.create_task(self._broadcast_task_event("task:completed", record.to_dict()))
                except RuntimeError:
                    pass

    # -----------------------------
    # Internal broadcast helper
    # -----------------------------
    async def _broadcast_task_event(self, event_type: str, task_data: dict[str, Any]) -> None:
        """Broadcast a task event to connected WebSocket clients."""
        if not TaskRegistry.broadcasting_enabled:
            return
        
        try:
            from api.websocket_tasks import broadcast_task_update
            await broadcast_task_update(event_type, task_data)
        except ImportError:
            # API module not available (e.g., test environment)
            pass
        except Exception as e:
            log.debug(f"Error broadcasting task event: {e}")

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

    def get_stats(self) -> dict[str, Any]:
        """Return task statistics for frontend dashboard."""
        all_tasks = self.list_all()
        active_tasks = self.active()
        failed_tasks = self.failed()
        cancelled_tasks = self.cancelled()
        completed_tasks = [t for t in all_tasks if t.task.done() and not t.finished_with_error]

        # Durations for running tasks (estimated)
        now = datetime.now(timezone.utc).timestamp()
        running_durations = [
            now - t.info.created_timestamp for t in active_tasks
        ]
        avg_running_duration = sum(running_durations) / len(running_durations) if running_durations else 0

        # Durations for completed tasks
        completed_durations = [
            t.get_duration() for t in completed_tasks
            if t.get_duration() is not None
        ]
        avg_completed_duration = sum(completed_durations) / len(completed_durations) if completed_durations else 0

        # Category breakdown
        category_counts: Dict[str, int] = {}
        for task in all_tasks:
            cat_name = task.info.category.name
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

        return {
            "total": len(all_tasks),
            "running": len(active_tasks),
            "completed": len(completed_tasks),
            "failed": len(failed_tasks),
            "cancelled": len(cancelled_tasks),
            "avg_running_duration": round(avg_running_duration, 2),
            "avg_completed_duration": round(avg_completed_duration, 2),
            "categories": category_counts,
        }

    def get_all_as_dicts(self) -> list[dict[str, Any]]:
        """Return all tasks as JSON-serializable dictionaries."""
        return [record.to_dict() for record in self._records.values()]

    def get_active_as_dicts(self) -> list[dict[str, Any]]:
        """Return active tasks as JSON-serializable dictionaries."""
        return [record.to_dict() for record in self.active()]

    def get_task_tree(self) -> dict[str, Any]:
        """Return tasks organized by hierarchy (parent-child relationships)."""
        all_records = self._records
        tree_nodes: Dict[int, dict[str, Any]] = {}

        # Convert all records to dicts and organize by parent
        for task_id, record in all_records.items():
            task_dict = record.to_dict()
            task_dict["children"] = []
            tree_nodes[task_id] = task_dict

        # Build parent-child relationships
        for task_id, node in tree_nodes.items():
            parent_id = all_records[task_id].parent_task_id
            if parent_id and parent_id in tree_nodes:
                tree_nodes[parent_id]["children"].append(node)

        # Return only root tasks (no parent)
        roots = [
            node for task_id, node in tree_nodes.items()
            if all_records[task_id].parent_task_id is None
        ]

        return {"tasks": roots, "total": len(all_records)}

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

    # Set task name to description for better logging in shutdown
    task.set_name(description)

    TaskRegistry.instance().register(
        task=task,
        category=category,
        description=description
    )

    return task
