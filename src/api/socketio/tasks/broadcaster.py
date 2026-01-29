from lifecycle.task_registry import TaskRegistry
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SOCKETIO)


def register_tasks(sio):
    """
    Registers Socket.IO handlers for task inspection.
    Provides endpoints for querying task state, statistics, and hierarchy.
    """

    registry = TaskRegistry.instance()

    @sio.event
    async def task_get_all(sid: str):
        """Client command: Get all tasks"""
        try:
            tasks = registry.get_all_as_dicts()
            await sio.emit("tasks:all", {'tasks': tasks}, room=sid)
            log.debug(f"Sent {len(tasks)} tasks to {sid}")
        except Exception as e:
            log.error("Failed to send all tasks", exc_info=True)
            await sio.emit('error', {'message': str(e)}, room=sid)

    @sio.event
    async def task_get_active(sid: str):
        """Client command: Get active tasks only"""
        try:
            tasks = registry.get_active_as_dicts()
            await sio.emit("tasks:active", {'tasks': tasks}, room=sid)
            log.debug(f"Sent {len(tasks)} active tasks to {sid}")
        except Exception as e:
            log.error("Failed to send active tasks", exc_info=True)
            await sio.emit('error', {'message': str(e)}, room=sid)

    @sio.event
    async def task_get_stats(sid: str):
        """Client command: Get task statistics"""
        try:
            stats = registry.get_stats()
            await sio.emit("tasks:stats", {'stats': stats}, room=sid)
            log.debug(f"Sent task stats to {sid}")
        except Exception as e:
            log.error("Failed to send task stats", exc_info=True)
            await sio.emit('error', {'message': str(e)}, room=sid)

    @sio.event
    async def task_get_tree(sid: str):
        """Client command: Get task hierarchy tree"""
        try:
            tree = registry.get_task_tree()
            await sio.emit("tasks:tree", {'tree': tree}, room=sid)
            log.debug(f"Sent task tree to {sid}")
        except Exception as e:
            log.error("Failed to send task tree", exc_info=True)
            await sio.emit('error', {'message': str(e)}, room=sid)