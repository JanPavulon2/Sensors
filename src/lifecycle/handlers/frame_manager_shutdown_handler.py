"""
FrameManager shutdown handler.

Responsible for graceful shutdown of FrameManager and its hardware executor.
"""

from __future__ import annotations

from engine.frame_manager import FrameManager
from lifecycle.shutdown_protocol import IShutdownHandler
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SHUTDOWN)


class FrameManagerShutdownHandler(IShutdownHandler):
    """
    Shutdown handler for FrameManager.

    Stops the render loop and cleans up the hardware executor,
    ensuring DMA operations don't continue during shutdown.
    """

    def __init__(self, frame_manager: FrameManager):
        self.frame_manager = frame_manager

    @property
    def shutdown_priority(self) -> int:
        return 120  # High priority - stop rendering early

    async def shutdown(self) -> None:
        """Shutdown frame manager and its executor."""
        log.info("Shutting down FrameManager...")

        try:
            await self.frame_manager.shutdown()
            log.debug("FrameManager shutdown complete")
        except Exception as e:
            log.error(f"Error shutting down FrameManager: {e}", exc_info=True)
