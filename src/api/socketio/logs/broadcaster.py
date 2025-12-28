
from services.log_broadcaster import get_broadcaster
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SOCKETIO)


def register_logs(sio):
    """
    Registers Socket.IO integration for log streaming.
    """

    broadcaster = get_broadcaster()

    # Podpinamy Socket.IO jako wyjście logów
    broadcaster.set_socketio_server(sio)

    log.info("Socket.IO registered as log broadcaster output")

    @sio.event
    async def logs_request_history(sid: str, data: dict):
        """
        Client asks for recent logs snapshot.
        """
        try:
            limit = data.get("limit", 100)
            logs = broadcaster.get_recent_logs(limit)
            payload = [log.model_dump() for log in logs]

            await sio.emit("logs.snapshot", payload, room=sid)

        except Exception as e:
            log.error("Failed to send log history", exc_info=True)
            await sio.emit("error", {"message": str(e)}, room=sid)