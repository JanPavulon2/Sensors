from socketio import AsyncServer, ASGIApp
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SOCKETIO)


def create_socketio_server(cors_origins: list[str]) -> AsyncServer:
    """Create and configure a Socket.IO AsyncServer."""
    return AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=cors_origins,
        ping_timeout=60,
        ping_interval=25,
        logger=False,
        engineio_logger=False,
    )


def wrap_app_with_socketio(app, socketio_server: AsyncServer):
    """Wrap FastAPI app with Socket.IO ASGI middleware."""
    return ASGIApp(socketio_server, app)