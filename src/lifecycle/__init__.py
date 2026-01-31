"""
Lifecycle subsystem
-------------------

Exports the public API for:
- graceful shutdown
- task tracking & introspection
- shutdown handlers

Internal modules remain private. External code should import from:
    from lifecycle import ShutdownCoordinator, TaskRegistry
    from lifecycle.handlers import LEDShutdownHandler
"""

from .shutdown_coordinator import ShutdownCoordinator
from .task_registry import TaskRegistry, TaskCategory, TaskInfo
from .shutdown_protocol import IShutdownHandler
# handlers imported on-demand to avoid circular imports
# from . import handlers

__all__ = [
    "ShutdownCoordinator",
    "TaskRegistry",
    "TaskCategory",
    "TaskInfo",
    "IShutdownHandler",
]