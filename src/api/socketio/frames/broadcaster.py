"""Socket.IO event handlers for frame streaming."""

from utils.logger import get_logger
from models.enums import LogCategory

log = get_logger().for_category(LogCategory.FRAME_MANAGER)


def register_frame_broadcaster(sio, services):
    """
    Register frame streaming event handlers.

    Note: Frame emission happens automatically via FrameManager → FrameStreamer.
    These handlers are for client connection management and debugging.
    """

    @sio.event(namespace="/frames")
    async def connect(sid: str, environ: dict):
        """Client connected to /frames namespace."""
        log.info(f"Client {sid} connected to /frames namespace")

    @sio.event(namespace="/frames")
    async def disconnect(sid: str):
        """Client disconnected from /frames namespace."""
        log.info(f"Client {sid} disconnected from /frames namespace")
