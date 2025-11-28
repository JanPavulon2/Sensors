
"""
Shutdown coordinator that orchestrates graceful shutdown of all components.

Manages signal handlers, shutdown sequencing, and error handling across
multiple shutdown handlers in priority order.
"""

import asyncio
import signal
from typing import List, Optional
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SYSTEM)


class ShutdownCoordinator:
    """
    Coordinates graceful shutdown of multiple components.

    Maintains a list of shutdown handlers and executes them in priority order
    when shutdown is triggered. Handles signal registration, timeout management,
    and error logging.

    Example:
        coordinator = ShutdownCoordinator()
        coordinator.register(LEDShutdownHandler(...))
        coordinator.register(APIServerShutdownHandler(...))
        coordinator.register(GPIOShutdownHandler(...))

        coordinator.setup_signal_handlers()
        await coordinator.wait_for_shutdown()
        await coordinator.shutdown_all()
    """

    def __init__(self, timeout_per_handler: float = 5.0, total_timeout: float = 15.0):
        """
        Initialize shutdown coordinator.

        Args:
            timeout_per_handler: Timeout for each individual handler (seconds)
            total_timeout: Total timeout for entire shutdown sequence (seconds)
        """
        self._handlers: List = []
        self._shutdown_event: Optional[asyncio.Event] = None
        self._timeout_per_handler = timeout_per_handler
        self._total_timeout = total_timeout
        self._shutdown_trigger = {"reason": None}

    def register(self, handler) -> None:
        """
        Register a shutdown handler.

        Handler must have:
        - shutdown_priority property (int)
        - async shutdown() method

        Args:
            handler: Object implementing ShutdownHandler protocol
        """
        if not hasattr(handler, "shutdown_priority"):
            raise ValueError(f"Handler {handler} missing shutdown_priority property")
        if not hasattr(handler, "shutdown"):
            raise ValueError(f"Handler {handler} missing shutdown() method")

        self._handlers.append(handler)
        log.debug(f"Registered shutdown handler: {handler.__class__.__name__}")

    def setup_signal_handlers(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        Install OS signal handlers for graceful shutdown.

        Registers SIGINT (Ctrl+C) and SIGTERM for graceful shutdown.

        Args:
            loop: Running asyncio event loop
        """
        self._shutdown_event = asyncio.Event()

        def signal_handler(sig: signal.Signals) -> None:
            """Handle OS signal by triggering shutdown event."""
            self._shutdown_trigger["reason"] = sig.name
            log.info(f"Signal {sig.name} received → triggering shutdown")
            self._shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

        log.info("Signal handlers installed (SIGINT, SIGTERM)")

    async def wait_for_shutdown(self) -> None:
        """
        Wait for shutdown event to be triggered.

        Blocks until a shutdown signal is received or the event is set
        by another part of the application.

        Raises:
            RuntimeError: If signal handlers weren't setup
        """
        if self._shutdown_event is None:
            raise RuntimeError("Call setup_signal_handlers() first")

        await self._shutdown_event.wait()

    async def shutdown_all(self) -> None:
        """
        Execute graceful shutdown of all handlers in priority order.

        Handlers are called in descending priority order (highest first).
        Includes timeout management and error handling.

        Each handler has its own timeout (timeout_per_handler) and the entire
        shutdown sequence has a global timeout (total_timeout).
        """
        log.info("🛑 Initiating graceful shutdown sequence...")
        reason = self._shutdown_trigger.get("reason", "UNKNOWN")
        log.info(f"   Reason: {reason}")

        # Sort by priority (highest first)
        sorted_handlers = sorted(
            self._handlers, key=lambda h: h.shutdown_priority, reverse=True
        )

        start_time = asyncio.get_event_loop().time()

        try:
            for handler in sorted_handlers:
                handler_name = handler.__class__.__name__
                priority = handler.shutdown_priority

                # Check if total timeout exceeded
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self._total_timeout:
                    log.error(
                        f"⚠️  Total shutdown timeout exceeded ({elapsed:.1f}s > {self._total_timeout}s)"
                    )
                    break

                try:
                    log.debug(
                        f"Shutting down {handler_name} (priority={priority})..."
                    )

                    # Call shutdown with timeout
                    await asyncio.wait_for(
                        handler.shutdown(), timeout=self._timeout_per_handler
                    )

                    log.debug(f"✓ {handler_name} shutdown complete")

                except asyncio.TimeoutError:
                    log.error(
                        f"⚠️  {handler_name} shutdown timeout "
                        f"({self._timeout_per_handler}s)"
                    )

                except asyncio.CancelledError:
                    log.debug(f"{handler_name} shutdown was cancelled")
                    raise

                except Exception as e:
                    log.error(
                        f"❌ Error shutting down {handler_name}: {e}", exc_info=True
                    )
                    # Continue with other handlers even if one fails

            log.info("✓ Shutdown sequence complete")

        except asyncio.CancelledError:
            log.warn("Shutdown sequence was cancelled")
            raise
        except Exception as e:
            log.error(f"Unexpected error during shutdown: {e}", exc_info=True)

    def get_handler(self, handler_type: type):
        """
        Get a registered handler by type.

        Useful for testing or debugging.

        Args:
            handler_type: The handler class to find

        Returns:
            Handler instance or None if not found
        """
        for handler in self._handlers:
            if isinstance(handler, handler_type):
                return handler
        return None