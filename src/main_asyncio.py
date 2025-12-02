"""
main_asyncio.py — Application entry point for Diuna
--------------------------------------------------

Responsible for:
- initializing managers, services, and controllers
- wiring dependencies (Dependency Injection)
- starting the async main loop
- graceful shutdown on Ctrl +C or fatal errors
"""

import contextlib
import sys
from typing import List, Optional

from lifecycle.handlers.all_tasks_cancellation_handler import AllTasksCancellationHandler
from lifecycle.handlers.animation_shutdown_handler import AnimationShutdownHandler
from lifecycle.handlers.api_server_shutdown_handler import APIServerShutdownHandler
from lifecycle.handlers.gpio_shutdown_handler import GPIOShutdownHandler
from lifecycle.handlers.led_shutdown_handler import LEDShutdownHandler
from lifecycle.handlers.task_cancellation_handler import TaskCancellationHandler
from managers.hardware_manager import HardwareManager
from models.domain.zone import ZoneCombined
from services.service_container import ServiceContainer
from models.enums import FramePriority

# ---------------------------------------------------------------------------
# UTF-8 ENCODING FIX (important for Raspberry Pi)
# ---------------------------------------------------------------------------

# Set UTF-8 encoding for output BEFORE any imports (fixes Unicode symbol rendering)
if hasattr(sys.stdout, 'reconfigure') and sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
if hasattr(sys.stderr, 'reconfigure') and sys.stderr.encoding != 'UTF-8':
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore

import signal
import asyncio
import atexit
import os
import uvicorn
from fastapi import FastAPI
from uvicorn import Server

from pathlib import Path
from utils.logger import get_logger, configure_logger
from services.log_broadcaster import get_broadcaster
from api.main import create_app
from api.dependencies import set_service_container

from models.enums import LogCategory, LogLevel, FramePriority
from components import ControlPanel, KeyboardInputAdapter, PreviewPanel
from hardware.gpio.gpio_manager import GPIOManager
from hardware.hardware_coordinator import HardwareCoordinator, HardwareBundle
from controllers.led_controller.lighting_controller import LightingController
from controllers import ControlPanelController, PreviewPanelController, ZoneStripController
from managers import ConfigManager
from services import EventBus, DataAssembler, ZoneService, AnimationService, ApplicationStateService, ServiceContainer
from services.middleware import log_middleware
from services.transition_service import TransitionService
from engine.frame_manager import FrameManager
from zone_layer.zone_strip import ZoneStrip
from hardware.led.ws281x_strip import WS281xStrip, WS281xConfig

# ---------------------------------------------------------------------------
# LOGGER SETUP
# ---------------------------------------------------------------------------

log = get_logger().for_category(LogCategory.SYSTEM)
configure_logger(LogLevel.DEBUG)

DEBUG_NOPULSE = False


# === Infrastructure imports ===
from hardware.gpio.gpio_manager import GPIOManager
from managers import ConfigManager
from services import (
    EventBus, DataAssembler, ZoneService, AnimationService,
    ApplicationStateService, ServiceContainer
)
from services.middleware import log_middleware

# === Hardware Layer ===
from hardware.hardware_coordinator import HardwareCoordinator

# === Lifecycle Management ===
from lifecycle import ShutdownCoordinator

from lifecycle.task_registry import (
    create_tracked_task,
    TaskCategory,
    TaskRegistry
)
# ---------------------------------------------------------------------------
# GLOBAL STATE (for shutdown coordination)
# ---------------------------------------------------------------------------

# Shared reference to api_server for explicit shutdown in signal handler
# _api_server_ref: dict = {'instance': None}

# Shared reference to gpio_manager for atexit cleanup
_gpio_manager_ref: dict = {'instance': None}

# ---------------------------------------------------------------------------
# SHUTDOWN & CLEANUP
# ---------------------------------------------------------------------------

def emergency_gpio_cleanup():
    """Emergency cleanup - called on any exit (crashes, seg faults)."""
    try:
        # Use the stored gpio_manager reference (not a new instance)
        gpio_manager = _gpio_manager_ref.get('instance')
        if gpio_manager:
            gpio_manager.cleanup()
            log.info("🚨 Emergency GPIO cleanup completed")
        else:
            log.debug("No GPIO manager to clean up")
    except Exception as e:
        log.error(f"Failed to cleanup GPIO: {e}")


async def cleanup_application(
    led_controller: LightingController,
    gpio_manager: GPIOManager,
    hardware: HardwareBundle,
    keyboard_task: asyncio.Task,
    polling_task: asyncio.Task,
    api_task: asyncio.Task
) -> None:
    """Perform graceful application cleanup on shutdown."""
    log.info("🧹 Starting cleanup...")

    # Cancel API server task
    if api_task and not api_task.done():
        api_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await api_task
        log.info("API server stopped")

    # Cancel polling and keyboard tasks
    if keyboard_task and not keyboard_task.done():
        keyboard_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await keyboard_task

    if polling_task and not polling_task.done():
        polling_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await polling_task

    # Stop animations
    log.info("Stopping animations...")
    try:
        led_controller.animation_mode_controller.animation_service.stop_all()
        log.debug("✓ Animation service stopped")
    except Exception as e:
        log.error(f"Error stopping animation service: {e}")

    try:
        if led_controller.animation_engine and led_controller.animation_engine.is_running():
            await led_controller.animation_engine.stop()
            log.debug("✓ Animation engine stopped")
    except Exception as e:
        log.error(f"Error stopping animation engine: {e}")

    # Stop pulsing
    log.info("Stopping pulsing...")
    await asyncio.sleep(0.05)

    # Clear LEDs (ALL strips, not just GPIO 18)
    log.info("Clearing LEDs on all GPIO strips...")
    try:
        led_controller.clear_all()
        log.debug("✓ All zones cleared")
    except Exception as e:
        log.error(f"Error clearing zones: {e}")

    try:
        for gpio_pin, strip in hardware.zone_strips.items():
            log.debug(f"Clearing GPIO {gpio_pin}...")
            strip.clear()
        log.debug("✓ All GPIO strips cleared")
    except Exception as e:
        log.error(f"Error clearing GPIO strips: {e}")

    # Cleanup GPIO
    log.info("Cleaning up GPIO...")
    try:
        gpio_manager.cleanup()
        log.debug("✓ GPIO cleaned up")
    except Exception as e:
        log.error(f"Error cleaning up GPIO: {e}")

    log.info("✓ Cleanup complete.")


# ---------------------------------------------------------------------------
# API SERVER RUNNER
# ---------------------------------------------------------------------------

async def run_api_server(app: FastAPI, host: str = "0.0.0.0", port: int = 8000) -> (Server, asyncio.Task):
    """
    Create uvicorn.Server and run serve() in a background task.
    Returns the Server instance and the Task running server.serve().
    """
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        loop="asyncio",
        log_level="info",
        access_log=False, 
        lifespan="on"
    )
    
    server = uvicorn.Server(config)
    
    log.info("API server starting...")
    
    server.install_signal_handlers = lambda: None 
    
    try:
        await server.serve()
    except asyncio.CancelledError:
        log.debug("Uvicorn lifespan cancelled during shutdown (expected).")
        
    return server
    log.debug("Uvicorn lifespan cancelled during shutdown (expected).")

# async def run_api_server2(app: FastAPI) -> Server:
#     """
#     Run FastAPI/uvicorn in the current event loop.
#     """
#     config = uvicorn.Config(
#         app,
#         host="0.0.0.0",
#         port=8000,
#         log_level="info",
#         access_log=False,
#         loop="asyncio"
#     )
    
#     server = uvicorn.Server(config)
#     await server.serve()
#     return server

# async def run_api_server() -> None:
#     """
#     Run the FastAPI server in the asyncio event loop.

#     Creates the FastAPI app with create_app() and runs it using
#     uvicorn's async server support. The API server handles REST
#     endpoints and WebSocket connections for logs and zone control.

#     The server runs until cancelled (via signal handlers).

#     IMPORTANT: We manage the server's lifespan manually (startup/shutdown)
#     instead of using serve() to prevent uvicorn from installing its own
#     signal handlers that would interfere with our shutdown pipeline.
#     """
#     log.info("Setting up FastAPI application...")

#     # Initialize LogBroadcaster for WebSocket log streaming
#     broadcaster = get_broadcaster()
#     broadcaster.start()

#     # Connect broadcaster to logger singleton
#     logger = get_logger()
#     logger.set_broadcaster(broadcaster)

#     log.info("LogBroadcaster initialized for WebSocket log streaming")

#     # Create FastAPI app
#     app = create_app(
#         title="Diuna LED System",
#         description="REST API for programmable LED control",
#         version="1.0.0",
#         docs_enabled=True
#     )

#     # Configure uvicorn server
#     API_PORT = 8000  # Change this if port is already in use
#     config = uvicorn.Config(
#         app=app,
#         host="0.0.0.0",
#         port=API_PORT,
#         log_level="info",
#         # Disable uvicorn's default access logging (we use our logger)
#         access_log=False,
#         loop="asyncio"
#     )

#     server = uvicorn.Server(config)

#     # Store server reference for explicit shutdown in signal handler
#     # _api_server_ref['instance'] = server

#     log.info(f"Starting FastAPI server on http://0.0.0.0:{API_PORT}")
#     log.info(f"API docs available at http://localhost:{API_PORT}/docs")

#     try:
#         # Run uvicorn's serve() which handles the full server lifecycle.
#         # When this returns or raises an exception, the server is being shut down
#         # (either by uvicorn handling a signal, or by our signal handler cancelling this task)
#         await server.serve()
#     except asyncio.CancelledError:
#         log.debug("API server task cancelled by signal handler...")
#         raise
#     except KeyboardInterrupt:
#         log.debug("API server received KeyboardInterrupt...")
#         raise
#     finally:
#         # Cleanup is handled by uvicorn's serve() context manager
#         # But ensure it's shut down if this exits unexpectedly
#         try:
#             if server.started:
#                 await server.shutdown()
#         except Exception as e:
#             log.debug(f"Server shutdown (expected): {e}")


# ---------------------------------------------------------------------------
# Application Entry
# ---------------------------------------------------------------------------

async def main():
    """Main async entry point (dependency injection and event loop startup)."""

    log.info("Starting Diuna application...")

    # ========================================================================
    # 1. INFRASTRUCTURE
    # ========================================================================

    log.info("Initializing GPIO manager (singleton)...")
    gpio_manager = GPIOManager()
    # _gpio_manager_ref['instance'] = gpio_manager

    log.info("Loading configuration...")
    config_manager = ConfigManager(gpio_manager)
    config_manager.load()

    log.info("Initializing event bus...")
    event_bus = EventBus()
    event_bus.add_middleware(log_middleware)
    
    atexit.register(emergency_gpio_cleanup)

    log.info("Loading application state...")
    state_file = Path(__file__).resolve().parent / "state" / "state.json"
    assembler = DataAssembler(config_manager, state_file)

    log.info("Initializing services...")
    animation_service = AnimationService(assembler)
    app_state_service = ApplicationStateService(assembler)
    zone_service = ZoneService(assembler, app_state_service)


    # ========================================================================
    # 2. HARDWARE COORDINATOR
    # ========================================================================

    hardware = HardwareCoordinator(
        hardware_manager=config_manager.hardware_manager,
        gpio_manager=gpio_manager
    ).initialize(
        all_zones = zone_service.get_all()
    )
    
    hardware.control_panel.event_bus = event_bus
    
    control_panel_controller = ControlPanelController(
        control_panel=hardware.control_panel, 
        event_bus=event_bus
    )

    # ========================================================================
    # 3. FRAME MANAGER
    # ========================================================================

    log.info("Initializing FrameManager...")
    frame_manager = FrameManager(fps=60)
    create_tracked_task(frame_manager.start(),
                        category=TaskCategory.RENDER,
                        description="Frame Manager renders loops")
    
    # frame_manager_task = asyncio.create_task(frame_manager.start())

    zone_strip_controllers = {}
    
    # Register all LED strips with FrameManager
    for gpio_pin, strip in hardware.zone_strips.items():
        frame_manager.add_zone_strip(strip)
        transition_service = TransitionService(strip, frame_manager)
        zone_strip_controllers[gpio_pin] = ZoneStripController(
            strip, transition_service, frame_manager
        )

        log.info(f"ZoneStripController ready on GPIO {gpio_pin}")

    
    # ========================================================================
    # 4. SERVICE CONTAINER
    # ========================================================================

    services = ServiceContainer(
        zone_service=zone_service,
        animation_service=animation_service,
        app_state_service=app_state_service,
        frame_manager=frame_manager,
        event_bus=event_bus,
        color_manager=config_manager.color_manager,
        config_manager=config_manager
    )

    # Register service container with API for dependency injection
    set_service_container(services)
    log.info("Service container registered with API")

    log.info("Initializing LED controller...")
    lighting_controller = LightingController(
        config_manager=config_manager,
        event_bus=event_bus,
        gpio_manager=gpio_manager, 
        service_container=services,
        zone_strip_controllers=zone_strip_controllers
    )


    # ========================================================================
    # 6. ADAPTERS (Keyboard)
    # ========================================================================

    log.info("Initializing keyboard input...")
    keyboard_task = create_tracked_task(
        KeyboardInputAdapter(event_bus).run(),
        category=TaskCategory.INPUT,
        description="KeyboardInputAdapter"
    )
    # asyncio.create_task(keyboard_adapter.run())


    # ========================================================================
    # 7. HARDWARE POLLING LOOP
    # ========================================================================

    async def hardware_polling_loop():
        """Poll hardware inputs at 50Hz"""
        try:
            while True:
                try:
                    await control_panel_controller.poll()
                except Exception as error:
                    log.error(f"Hardware polling error: {error}", exc_info=True)
                await asyncio.sleep(0.02)
        except asyncio.CancelledError:
            log.debug("Hardware polling loop cancelled.")
            raise
    
        
    polling_task =  create_tracked_task(
        hardware_polling_loop(),
        category=TaskCategory.HARDWARE,
        description="ControlPanel Polling Loop"
    )
    # asyncio.create_task(hardware_polling_loop(), name="HardwarePolling")
    
    
    # ========================================================================
    # 8. API SERVER
    # ========================================================================

    log.info("Starting API server task...")
    # Initialize LogBroadcaster for WebSocket log streaming
    broadcaster = get_broadcaster()
    broadcaster.start()

    # Connect broadcaster to logger singleton
    # get_logger().set_broadcaster(broadcaster)

    log.info("LogBroadcaster initialized for WebSocket log streaming")


    app = create_app()
    api_task = create_tracked_task(
        run_api_server(app),
        category=TaskCategory.API,
        description="FastAPI/Uvicorn Server"
    )


    # ============================================================
    # 8. SHUTDOWN COORDINATOR
    # ============================================================

    log.info("Initializing shutdown system...")

    coordinator = ShutdownCoordinator()

    # Register shutdown handlers
    coordinator.register(LEDShutdownHandler(hardware))
    coordinator.register(AnimationShutdownHandler(lighting_controller))
    coordinator.register(APIServerShutdownHandler(api_task))
    coordinator.register(TaskCancellationHandler([keyboard_task, polling_task, api_task]))
    # AllTasksCancellationHandler cancels all remaining tracked tasks (excluding explicitly managed ones)
    # This ensures any tasks registered in TaskRegistry get cleaned up, avoiding orphaned tasks
    coordinator.register(AllTasksCancellationHandler(exclude_tasks=[keyboard_task, polling_task, api_task]))
    coordinator.register(GPIOShutdownHandler(gpio_manager))
    
    shutdown_event = asyncio.Event()
    def _signal(sig):
        log.info(f"Signal received: {sig.name}")
        shutdown_event.set()
        
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: _signal(s))

    log.info("🏁 Application initialized. Waiting for exit signal...")
    
    await shutdown_event.wait()
    log.info("Shutdown requested")

    await coordinator.shutdown_all()
    log.info("👋 Diuna shut down cleanly.")

    
# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Keyboard interrupt received")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
    finally:
        emergency_gpio_cleanup()
        sys.exit(0)
        
    # ============================================================
    # 9. WAIT FOR SHUTDOWN
    # ============================================================

    # log.info("🏁 Application initialized. Waiting for exit signal...")
    # try:
    #     await coordinator.wait_for_shutdown()
    #     log.info("Shutdown signal received, running shutdown handlers...")
    #     await coordinator.shutdown_all()
    # except asyncio.CancelledError:
    #     log.warn("Main cancelled while waiting for shutdown")
    #     raise
    # except Exception as e:
    #     log.error("Unhandled error during shutdown sequencing: %s. Error: {e}")
    # finally:
    #     # ensure broadcaster and other singleton resources are stopped
    #     try:
    #         await broadcaster.stop()
    #     except Exception:
    #         pass

    #     # extra safety: if anything still runs, cancel remaining tasks
    #     remaining = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    #     if remaining:
    #         log.debug("Cancelling remaining %d tasks", remaining=len(remaining))
    #         for t in remaining:
    #             t.cancel()
    #         await asyncio.gather(*remaining, return_exceptions=True)

    #     # Emergency GPIO cleanup on final exit
    #     try:
    #         gpio_manager.cleanup()
    #         log.info("GPIO cleaned up (final)")
    #     except Exception:
    #         log.error("Final GPIO cleanup failed")

    #     log.info("👋 Diuna shut down cleanly.")
    #     # Exit process
    #     sys.exit(0)
    
    # ========================================================================
    # SIGNAL HANDLERS
    # ========================================================================

    # Create shutdown event to coordinate graceful exit
    # shutdown_event = asyncio.Event()

    # def signal_handler(sig):
    #     """Signal handler that triggers graceful shutdown."""
    #     log.info(f"Received signal: {sig.name} → initiating graceful shutdown...")
    #     # Set event to break gather() - this is the ONLY action in signal handler
    #     # (no async calls here)
    #     shutdown_event.set()

    # # Register signal handlers for graceful exit
    # loop = asyncio.get_running_loop()
    # for sig in (signal.SIGINT, signal.SIGTERM):
    #     loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))


    # ========================================================================
    # MAIN TASK GATHER
    # ========================================================================

    # async def wait_for_shutdown():
    #     """Wait for shutdown event to be triggered."""
    #     try:
    #         await shutdown_event.wait()
    #     except asyncio.CancelledError:
    #         raise

    # try:
    #     # Monitor tasks and trigger shutdown if:
    #     # 1. Shutdown event is set (user pressed Ctrl+C)
    #     # 2. API server exits unexpectedly (uvicorn handled a signal)
    #     while True:
    #         # Check if api_task has completed (uvicorn shut down)
    #         if api_task.done():
    #             log.info("API server exited, triggering shutdown...")
    #             shutdown_event.set()
    #             break

    #         # Check if shutdown event is set
    #         if shutdown_event.is_set():
    #             break

    #         # Also check if other critical tasks failed
    #         for task in [keyboard_task, polling_task]:
    #             if task.done() and task.exception() is not None:
    #                 log.error(f"Critical task failed: {task.get_name()}")
    #                 shutdown_event.set()
    #                 break

    #         # Small sleep to avoid busy-waiting
    #         try:
    #             await asyncio.wait_for(asyncio.sleep(0.1), timeout=0.5)
    #         except asyncio.TimeoutError:
    #             continue
    #         except asyncio.CancelledError:
    #             log.debug("Main loop cancelled.")
    #             raise

    #     # Cancel remaining tasks
    #     log.debug("Breaking out of main loop, cancelling remaining tasks...")
    #     for task in [keyboard_task, polling_task, api_task]:
    #         if not task.done():
    #             task.cancel()

    #     # Wait for them to finish cancelling
    #     await asyncio.gather(keyboard_task, polling_task, api_task, return_exceptions=True)

    # except asyncio.CancelledError:
    #     log.debug("Main loop cancelled.")
    # finally:
    #     log.info("Initiating shutdown sequence...")

    #     # Clear LEDs IMMEDIATELY before anything else
    #     try:
    #         log.info("Clearing LEDs on all GPIO strips...")
    #         # Clear all zone strips (there may be multiple GPIO pins)
    #         for gpio_pin, strip in hardware.zone_strips.items():
    #             try:
    #                 strip.clear()
    #                 log.debug(f"✓ Cleared GPIO {gpio_pin}")
    #             except Exception as e:
    #                 log.error(f"Error clearing GPIO {gpio_pin}: {e}")
    #         log.info("✓ All LEDs cleared")
    #     except Exception as e:
    #         log.error(f"Error clearing LEDs: {e}")

    #     try:
    #         # First, run explicit shutdown to release API server and cancel tasks
    #         await asyncio.wait_for(
    #             shutdown(asyncio.get_running_loop(), "MAIN_SHUTDOWN"),
    #             timeout=3.0
    #         )
    #     except asyncio.TimeoutError:
    #         log.error("⚠️ shutdown() timeout - force cancelling remaining tasks")
    #         # Force cancel all remaining tasks
    #         for task in asyncio.all_tasks(loop):
    #             if task is not asyncio.current_task(loop):
    #                 task.cancel()
    #     except Exception as e:
    #         log.error(f"Error during shutdown: {e}")

    #     try:
    #         # Then, do cleanup work (clear LEDs, cleanup GPIO)
    #         await asyncio.wait_for(
    #             cleanup_application(
    #                 lighting_controller,
    #                 gpio_manager,
    #                 hardware,
    #                 keyboard_task,
    #                 polling_task,
    #                 api_task
    #             ),
    #             timeout=3.0  # 3 second timeout for cleanup
    #         )
    #     except asyncio.TimeoutError:
    #         log.error("⚠️ Cleanup timeout - some operations took too long, forcing shutdown")
    #         try:
    #             # Try emergency GPIO cleanup as fallback
    #             gpio_manager.cleanup()
    #         except Exception as e:
    #             log.error(f"Emergency cleanup failed: {e}")
    #     except Exception as e:
    #         log.error(f"Error during cleanup: {e}")


# ---------------------------------------------------------------------------
# ENTRY
# ---------------------------------------------------------------------------


# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         log.info("KeyboardInterrupt received - exiting...")
#     except Exception as e:
#         log.error(f"Unexpected error: {e}", exc_info=True)
#     finally:
#         pass
        # Ensure GPIO cleanup happens no matter what
        # log.info("Final shutdown...")
        # try:
        #     emergency_gpio_cleanup()
        # except Exception as e:
        #     log.error(f"Error in final cleanup: {e}")
        # # Explicitly exit to ensure the process terminates
        # sys.exit(0)
