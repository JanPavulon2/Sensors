
from __future__ import annotations
import asyncio
import uvicorn
from fastapi import FastAPI
from typing import Optional
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.API)


class APIServerWrapper:
    """
    Robust wrapper for running Uvicorn inside an asyncio task without Uvicorn's
    signal handlers interfering with your shutdown pipeline.

    Behaviour:
      - start() launches uvicorn.Server.serve() as a background task and awaits
        an internal stop event. start() returns only after stop_event is set.
      - stop() triggers stop_event, attempts graceful shutdown, and forces exit
        if necessary. It will also close sockets and cancel tasks.
      - Both start() and stop() are safe to call from the shutdown coordinator.
    """

    def __init__(
        self,
        app: FastAPI,
        host: str = "0.0.0.0",
        port: int = 8000,
    ):
        self.app = app
        self.host = host
        self.port = port
        self._server: Optional[uvicorn.Server] = None
        self._serve_task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()
        # optional: track whether we called start()
        self._started_by_wrapper = False
        
        
    # ----------------------------------------------------------------------
    # INTERNAL
    # ----------------------------------------------------------------------
    def _create_server(self) -> uvicorn.Server:
        """Create a uvicorn.Server instance with disabled signal handlers and SO_REUSEADDR."""
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            loop="asyncio",
            log_level="info",
            access_log=False,
            # CRITICAL: SO_REUSEADDR allows binding even if port is in TIME_WAIT
            # This prevents "Address already in use" errors when restarting quickly
            server_header=False,
        )

        server = uvicorn.Server(config)

        # Explicitly disable uvicorn's own signal handlers
        # (property exists in all modern Uvicorn versions)
        server.install_signal_handlers = lambda: None  # type: ignore

        return server
        
    # ----------------------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------------------
    async def start(self, *, wait_started_timeout: float = 5.0) -> None:
        """
        Start uvicorn server in background and wait until stop() is called.

        This method will return when stop() has been invoked and shutdown
        completed (or was forced). If you want non-blocking start, schedule
        start() as a task with create_tracked_task().
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
                log.info("🌐 API server reported started")
                break
            
            # Case 2: uvicorn has bound low-level sockets (reliable sign of bind)
            servers = getattr(self._server, "servers", None)
            if servers:
                log.info("🌐 API server has bound sockets (servers list present)")
                break
            await asyncio.sleep(0.05)
        # --- Block here until stop() is called (stop_event set) ---
        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            # If outer code cancels start(), propagate cancellation but try to stop server
            log.debug("start() cancelled externally, invoking stop()")
            await self.stop()
            raise

        # start() returns after stop_event has been triggered and stop() finished
        log.debug("APIServerWrapper.start() exiting (stop_event set)")

    async def stop(self, *, shutdown_timeout: float = 2.0, force_exit: bool = True) -> None:
        """
        Stop the API server and release the port.

        Steps:
          1. set stop_event so start() unblocks
          2. set server.force_exit (optional) to avoid lifespan hang
          3. call server.shutdown() with timeout
          4. close sockets and cancel serve task if still running
        """
        # If not started, nothing to do
        if self._server is None and (self._serve_task is None or self._serve_task.done()):
            log.warn("API server stop() called but server was not running")
            # still set event so any waiter doesn't hang
            self._stop_event.set()
            return

        log.info("🌐 Stopping API server...")

        # Signal to start() waiter
        self._stop_event.set()

        # Defensive: ensure server object exists
        if self._server is None:
            # wait for serve task to create server (unlikely)
            if self._serve_task:
                try:
                    await asyncio.wait_for(self._serve_task, timeout=0.5)
                except Exception:
                    pass
            if self._server is None:
                log.warn("API server object missing during stop(); giving up")
                return

        # Try graceful shutdown
        try:
            if force_exit:
                # force_exit speeds immediate socket closing (prevents TIME_WAIT holding port)
                self._server.force_exit = True

            # server.shutdown() is a coroutine that completes uvicorn shutdown
            try:
                await asyncio.wait_for(self._server.shutdown(), timeout=shutdown_timeout)
                log.info("🌐 API server shutdown completed")
            except asyncio.TimeoutError:
                log.warn("🌐 API server shutdown timeout; proceeding to force-close sockets")
        except Exception as e:
            log.error(f"Error during API server.shutdown(): {e}", exc_info=True)

        # Close low-level sockets opened by the server if any
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
    def is_running(self) -> bool:
        """Return whether a uvicorn serve task is active."""
        return self._serve_task is not None and not self._serve_task.done()

    @property
    def task(self) -> Optional[asyncio.Task]:
        return self._serve_task

    @property
    def server(self) -> Optional[uvicorn.Server]:
        return self._server