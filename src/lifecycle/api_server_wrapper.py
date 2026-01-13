from __future__ import annotations

import asyncio
import uvicorn
from typing import Optional
from starlette.types import ASGIApp

from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.API)

class APIServerWrapper:
    """
    Robust wrapper for running Uvicorn inside an asyncio task.
    
    Solves common Uvicorn problems in async applications:
    - Signal handler conflicts (disables Uvicorn's SIGINT/SIGTERM handlers)
    - Graceful shutdown with configurable timeout
    - Quick port release (manual socket close)
    - Lifespan hangs (force_exit option to skip cleanup)
    
    This wrapper allows you to:
    1. Start Uvicorn as a background task (non-blocking)
    2. Stop Uvicorn gracefully from shutdown coordinator
    3. Restart quickly without "Address already in use" errors
    4. Test API server lifecycle in integration tests
    
    Example:
        >>> wrapper = APIServerWrapper(app, host="0.0.0.0", port=8000)
        >>> 
        >>> # Start server (blocks until stop() is called)
        >>> await wrapper.start()
        >>> 
        >>> # Or start as background task
        >>> task = asyncio.create_task(wrapper.start())
        >>> 
        >>> # ... application runs ...
        >>> 
        >>> # Graceful shutdown (2s timeout)
        >>> await wrapper.stop()
    
    Usage in Shutdown Coordinator:
        coordinator.register(APIServerShutdownHandler(wrapper))
    
    Attributes:
        app: ASGI application (FastAPI/Starlette)
        host: Bind host (default: "0.0.0.0")
        port: Bind port (default: 8000)
    """

    def __init__(
        self,
        app: ASGIApp,
        host: str = "0.0.0.0",
        port: int = 8000,
    ):
        self.app = app
        self.host = host
        self.port = port
        
        # Internal state
        self._server: Optional[uvicorn.Server] = None
        self._serve_task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self._started_by_wrapper = False
        
        
    # ----------------------------------------------------------------------
    # INTERNAL
    # ----------------------------------------------------------------------
    def _create_server(self) -> uvicorn.Server:
        """
        Create a uvicorn.Server instance with:
        - Disabled signal handlers (to avoid conflicts with ShutdownCoordinator)
        """
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            loop="asyncio",
            log_level="info",
            access_log=False,
            server_header=False,
        )

        server = uvicorn.Server(config)

        # CRITICAL: Disable Uvicorn's signal handlers
        # Without this, Uvicorn intercepts SIGINT/SIGTERM and breaks your shutdown flow
        server.install_signal_handlers = lambda: None  # type: ignore

        return server
        
    # ----------------------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------------------
    async def start(self, *, wait_started_timeout: float = 5.0) -> None:
        """
        Start Uvicorn server in background and block until stop() is called.
        
        This method:
        1. Creates Uvicorn server with disabled signal handlers
        2. Starts server.serve() as background task
        3. Waits until server reports "started" (or timeout)
        4. Blocks on stop_event until stop() is called
        5. Returns after shutdown completes
        
        Args:
            wait_started_timeout: Seconds to wait for server to bind (default: 5s)
        
        Raises:
            RuntimeError: If server already started
            asyncio.CancelledError: If start() is cancelled externally
        
        Note:
            This method blocks until stop() is called. To run server in background,
            use: asyncio.create_task(wrapper.start())
        """
        if self._serve_task is not None and not self._serve_task.done():
            raise RuntimeError("API server already started")

        self._server = self._create_server()
        self._stop_event.clear()
        self._started_by_wrapper = True

        log.info(f"🌐 Launching API server on http://{self.host}:{self.port}")

        # Start uvicorn serve() as background task and keep reference
        self._serve_task = asyncio.create_task(
            self._server.serve(), name="UvicornServeInternal"
        )

        # Wait until uvicorn reports it's started (or timeout)
        # use getattr to avoid static analysis complaining about .started
        deadline = asyncio.get_event_loop().time() + wait_started_timeout
        while asyncio.get_event_loop().time() < deadline:
            # Case 1: uvicorn sets the 'started' flag
            if getattr(self._server, "started", False):
                log.info("🌐 API server started (Uvicorn 'started' flag set)")
                break
            
            # Check if sockets bound (alternative indicator)
            servers = getattr(self._server, "servers", None)
            if servers:
                log.info("🌐 API server started (sockets bound)")
                break
            await asyncio.sleep(0.05)
        
        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            # If start() is cancelled, attempt graceful stop
            log.debug("start() cancelled externally, invoking stop()")
            await self.stop()
            raise

        log.debug("APIServerWrapper.start() exiting (stop_event set)")

    async def stop(self, *, shutdown_timeout: float = 2.0, force_exit: bool = True) -> None:
        """
        Stop the API server and release the port.
        
        Shutdown sequence:
        1. Set stop_event (unblocks start())
        2. Set server.force_exit=True (skips lifespan cleanup if needed)
        3. Call server.shutdown() with timeout
        4. Close low-level sockets manually
        5. Cancel serve task if still running
        
        Args:
            shutdown_timeout: Seconds to wait for graceful shutdown (default: 2s)
            force_exit: Skip lifespan cleanup to avoid hangs (default: True)
        
        Note:
            Safe to call multiple times (idempotent).
            Safe to call if server not started (no-op).
        """
        # If not started, nothing to do
        if self._server is None and (self._serve_task is None or self._serve_task.done()):
            log.warn("API server stop() called but server was not running")
            self._stop_event.set() # Unblock any waiters
            return

        log.info("🌐 Stopping API server...")

        # Signal to start() waiter
        self._stop_event.set()

        # Defensive: ensure server object exists
        if self._server is None:
            if self._serve_task:
                try:
                    await asyncio.wait_for(self._serve_task, timeout=0.5)
                except Exception:
                    pass
            if self._server is None:
                log.warn("API server object missing during stop(); aborting")
                return

        # Try graceful shutdown
        try:
            if force_exit:
                # force_exit speeds up shutdown by skipping lifespan cleanup
                # This prevents hangs if lifespan context manager is stuck
                self._server.force_exit = True

            # server.shutdown() is async coroutine that completes Uvicorn shutdown
            try:
                await asyncio.wait_for(self._server.shutdown(), timeout=shutdown_timeout)
                log.info("🌐 API server shutdown completed gracefully")
            except asyncio.TimeoutError:
                log.warn(f"🌐 API server shutdown timeout ({shutdown_timeout}s); forcing socket close")
        except Exception as e:
            log.error(f"Error during API server.shutdown(): {e}", exc_info=True)

        # Manually close low-level sockets (ensures port released immediately)
        try:
            servers = getattr(self._server, "servers", None)
            if servers:
                for s in servers:
                    try:
                        s.close()
                        log.debug("🌐 Closed socket FD")
                    except Exception:
                        log.debug("🌐 Exception while closing socket", exc_info=True)
        except Exception as e:
            log.debug(f"Error closing sockets: {e}", exc_info=True)

        # Cancel the serve task if it didn't finish
        if self._serve_task and not self._serve_task.done():
            self._serve_task.cancel()
            try:
                await asyncio.wait_for(self._serve_task, timeout=1.0)
            except asyncio.CancelledError:
                log.debug("Uvicorn serve task cancelled cleanly")
            except asyncio.TimeoutError:
                log.debug("Uvicorn serve task did not stop in time")

        # Final cleanup
        self._server = None
        self._serve_task = None
        self._started_by_wrapper = False

        log.info("🌐 API server stopped and port released")

    # ----------------------------------------------------------------------
    # PROPERTIES
    # ----------------------------------------------------------------------
    @property
    def is_started(self) -> bool:
        """
        Return whether start() was called (even if server not yet bound).
        
        Useful for checking initialization state.
        """
        return self._started_by_wrapper
    
    @property
    def is_running(self) -> bool:
        """
        Return whether server is actively serving requests.
        
        Checks both that:
        - serve task exists and is running
        - Uvicorn reports 'started' flag
        """
        return (
            self._serve_task is not None 
            and not self._serve_task.done()
            and getattr(self._server, "started", False)
        )
        
    @property
    def task(self) -> Optional[asyncio.Task]:
        """Return the asyncio Task running uvicorn.Server.serve() (or None)"""
        return self._serve_task

    @property
    def server(self) -> Optional[uvicorn.Server]:
        """Return the underlying uvicorn.Server instance (or None)"""
        return self._server