
from __future__ import annotations
import asyncio
import uvicorn
from fastapi import FastAPI
from typing import Optional
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.API)


class APIServerWrapper:
    """
    Clean wrapper for running Uvicorn inside an asyncio task without Uvicorn's
    signal handlers interfering with your shutdown pipeline.
    
    Provides:
    - start()
    - stop()
    - is_running
    - access to the underlying uvicorn.Server
    """
    def __init__(
        self, 
        app: FastAPI, 
        host: str = "0.0.0.0", 
        port: int = 8000):
        
        self.app = app
        self.host = host
        self.port = port
        self._server: Optional[uvicorn.Server] = None
        self._task: Optional[asyncio.Task] = None
        
    # ----------------------------------------------------------------------
    # INTERNAL
    # ----------------------------------------------------------------------
    def _create_server(self) -> uvicorn.Server:
        """Create a uvicorn.Server instance with disabled signal handlers."""
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            loop="asyncio",
            log_level="info",
            access_log=False,
        )

        server = uvicorn.Server(config)

        # Explicitly disable uvicorn's own signal handlers
        # (property exists in all modern Uvicorn versions)
        server.install_signal_handlers = lambda: None  # type: ignore

        return server
        
    # ----------------------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------------------
    async def start(self) -> None:
        if self._task is not None:
            raise RuntimeError("API server already started")

        self._server = self._create_server()
        log.info(f"🌐 Starting API server on http://{self.host}:{self.port}")

        self._task = asyncio.create_task(
            self._server.serve(),
            name="UvicornServerTask"
        )

        # Optional: wait until the server signals it's ready
        await asyncio.sleep(0)  # yield control

        if self._server.started:
            log.info("🌐 API server started successfully")
        else:
            log.warn("🌐 API server start not confirmed (maybe still booting)")

    async def stop(self) -> None:
        """
        Stop the API server immediately and release the port.

        CRITICAL FIX for uvicorn/Starlette lifespan task leak:
        Setting force_exit=True bypasses lifespan shutdown handlers and closes
        all socket FDs immediately. This prevents the port from remaining in
        LISTEN state and prevents the application from hanging on Ctrl+C.

        Without force_exit, Starlette lifespan handlers can leak a task that:
        - Keeps the port in LISTEN state even after process dies
        - Prevents Ctrl+C from working (application appears frozen)
        - Requires Ctrl+Z (SIGSTOP) to kill, leaving orphaned process
        """
        if self._server is None:
            log.warn("API server stop() called before start()")
            return

        log.info("🌐 Stopping API server...")

        # ✅ CRITICAL: Prevent uvicorn lifespan task leak
        # force_exit=True immediately closes all FDs without waiting for lifespan
        self._server.force_exit = True

        try:
            # This will now exit immediately due to force_exit
            await asyncio.wait_for(self._server.shutdown(), timeout=1.0)
            log.info("🌐 API server shutdown completed")
        except asyncio.TimeoutError:
            log.warn("🌐 API server shutdown timeout, forcing exit...")
        except Exception as e:
            log.error(f"Error during API server shutdown(): {e}")

        # Cancel the server task
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=0.5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                log.debug("Uvicorn task cancelled cleanly")

        log.info("🌐 API server stopped and port released")
        
    # ----------------------------------------------------------------------
    # PROPERTIES
    # ----------------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return (
            self._task is not None
            and not self._task.done()
        )

    @property
    def task(self) -> Optional[asyncio.Task]:
        return self._task

    @property
    def server(self) -> Optional[uvicorn.Server]:
        return self._server