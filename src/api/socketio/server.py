from socketio import AsyncServer
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SOCKETIO)


def create_socketio_server(cors_origins: list[str]) -> AsyncServer:
    return AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=cors_origins,
        ping_timeout=60,
        ping_interval=25,
        logger=False,
        engineio_logger=False,
    )