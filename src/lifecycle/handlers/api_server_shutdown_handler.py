from __future__ import annotations
from typing import TYPE_CHECKING

from lifecycle.shutdown_protocol import IShutdownHandler
from utils.logger import get_logger, LogCategory

if TYPE_CHECKING:
    from lifecycle.api_server_wrapper import APIServerWrapper

log = get_logger().for_category(LogCategory.SHUTDOWN)

class APIServerShutdownHandler(IShutdownHandler):
    """
    Shutdown handler for API server (FastAPI + Uvicorn).

    Stops the HTTP/WebSocket API server and releases port 8000.

    Uses APIServerWrapper for clean shutdown with force_exit flag to prevent
    uvicorn/Starlette lifespan task leak that leaves port orphaned.

    Priority: 90 (shutdown after animations, before other tasks)
    """

    def __init__(self, api_wrapper: "APIServerWrapper"):
        """
        Initialize API server shutdown handler.

        Args:
            api_wrapper: APIServerWrapper instance managing the API server
        """
        self.api_wrapper = api_wrapper

    @property
    def shutdown_priority(self) -> int:
        """API server shuts down after animations."""
        return 90

    async def shutdown(self) -> None:
        """
        Shutdown the API server and release port.

        Calls api_wrapper.stop() which:
        1. Sets server.force_exit = True (prevents lifespan leak)
        2. Calls server.shutdown() for graceful cleanup
        3. Cancels the uvicorn task
        4. Ensures port is released (no orphaned FD)
        """
        log.info("Stopping API server...")

        if not self.api_wrapper.is_running:
            log.debug("API server not running")
            return

        try:
            await self.api_wrapper.stop()
        except Exception as e:
            log.error(f"Error stopping API server: {e}", exc_info=True)

