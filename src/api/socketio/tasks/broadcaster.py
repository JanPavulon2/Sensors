from lifecycle.task_registry import TaskRegistry
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SOCKETIO)


def register_tasks(sio):
    """
    Registers Socket.IO handlers for task inspection.
    """

    registry = TaskRegistry.instance()

    @sio.event
    async def tasks_get_all(sid: str):
        try:
            tasks = registry.get_all_as_dicts()
            await sio.emit("tasks.snapshot", tasks, room=sid)
        except Exception:
            log.error("Failed to send all tasks", exc_info=True)

    @sio.event
    async def tasks_get_active(sid: str):
        try:
            tasks = registry.get_active_as_dicts()
            await sio.emit("tasks.active", tasks, room=sid)
        except Exception:
            log.error("Failed to send active tasks", exc_info=True)

    @sio.event
    async def tasks_get_stats(sid: str):
        try:
            stats = registry.get_stats()
            await sio.emit("tasks.stats", stats, room=sid)
        except Exception:
            log.error("Failed to send task stats", exc_info=True)