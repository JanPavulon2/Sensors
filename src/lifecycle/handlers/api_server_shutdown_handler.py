from __future__ import annotations
import asyncio

from controllers.led_controller.lighting_controller import LightingController
from lifecycle.shutdown_protocol import IShutdownHandler
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SHUTDOWN)

class APIServerShutdownHandler(IShutdownHandler):
    """
    Shutdown handler for API server (FastAPI + Uvicorn).
    Stops the HTTP/WebSocket API server and releases port 8000.

    Priority: 90
    """

    def __init__(self, api_task: asyncio.Task):
        """
        Initialize API server shutdown handler.

        Args:
            api_server: uvicorn.Server instance
        """
        self.api_task = api_task

    @property
    def shutdown_priority(self) -> int:
        """API server shuts down after animations."""
        return 90

    async def shutdown(self) -> None:
        """Shutdown uvicorn server."""
        log.info("Stopping API server...")
        
        if self.api_task is None:
            log.debug("No API task to stop.")
            return

        if self.api_task.done():
            log.debug("API server task already finished.")
            return
        
        self.api_task.cancel()
            
        try:
            await self.api_task
        except asyncio.CancelledError:
            # This is *NORMAL* for Starlette/Uvicorn lifespan
            log.debug("API server task cancel acknowledged (normal during shutdown).")
        except Exception as e:
            log.error(f"Unexpected error when stopping API server: {e}")
        # try:
        #     if self.api_server and self.api_server.started:
        #         await self.api_server.shutdown()
        #         # Give it a moment to release the port
        #         await asyncio.sleep(0.1)
        #         log.debug("✓ API server stopped")
        # except Exception as e:
        #     log.error(f"Error stopping API server: {e}")

