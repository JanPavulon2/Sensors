from services.log_broadcaster import get_broadcaster
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SOCKETIO)


def register_logs(sio):
    """
    Registers Socket.IO integration for log streaming.
    Sets up the log broadcaster output and history request handler.
    """

    broadcaster = get_broadcaster()

    # Connect Socket.IO as log output
    broadcaster.set_socketio_server(sio)

    log.info("Socket.IO registered as log broadcaster output")

    @sio.event
    async def logs_request_history(sid: str, data: dict):
        """Client command: Request recent log history"""
        try:
            limit = data.get("limit", 100)
            logs = broadcaster.get_recent_logs(limit)
            payload = [entry.model_dump() for entry in logs]

            await sio.emit("logs:history", {'logs': payload}, room=sid)
            log.debug(f"Sent {len(payload)} logs to {sid}")

        except Exception as e:
            log.error("Failed to send log history", exc_info=True)
            await sio.emit("error", {"message": str(e)}, room=sid)