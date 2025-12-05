"""
main_asyncio.py — Application entry point for Diuna
--------------------------------------------------

Responsible for:
- initializing managers, services, and controllers
- wiring dependencies (Dependency Injection)
- starting the async main loop
- graceful shutdown on Ctrl +C or fatal errors
"""

import sys
from typing import List, Optional

# from lifecycle.handlers.all_tasks_cancellation_handler import AllTasksCancellationHandler
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

import asyncio
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
# SHUTDOWN & CLEANUP
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# API SERVER RUNNER
# ---------------------------------------------------------------------------

async def run_api_server(app: FastAPI, host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Run FastAPI/Uvicorn server in asyncio event loop.

    Disables uvicorn's own signal handlers to use our shutdown coordinator instead.
    The server runs until cancelled (via CancelledError from shutdown system).
    """
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        loop="asyncio",
        log_level="info",
        access_log=False,
        # lifespan="on"
    )

    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # Prevent uvicorn from handling signals

    try:
        log.debug(f"🌐 Starting API server on {host}:{port}")
        await server.serve()
    except asyncio.CancelledError:
        # Expected during shutdown - uvicorn raises CancelledError on lifespan shutdown
        log.debug("🌐 API server cancelled (expected during shutdown)")
        raise  # Let the cancellation propagate to task handler

# ---------------------------------------------------------------------------
# Application Entry
# ---------------------------------------------------------------------------

async def main():
    """Main async entry point (dependency injection and event loop startup)."""

    # Initialize broadcaster first so all logs can be transmitted
    _broadcaster = get_broadcaster()
    _broadcaster.start()
    get_logger().set_broadcaster(_broadcaster)

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

    app = create_app()
    api_task = create_tracked_task(
        run_api_server(app),
        category=TaskCategory.API,
        description="FastAPI/Uvicorn Server"
    )


    # ============================================================
    # 10. SHUTDOWN COORDINATOR
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
    # coordinator.register(AllTasksCancellationHandler(exclude_tasks=[keyboard_task, polling_task, api_task]))
    coordinator.register(GPIOShutdownHandler(gpio_manager))

    # Setup signal handlers via coordinator
    loop = asyncio.get_running_loop()
    coordinator.setup_signal_handlers(loop)

    log.info("🏁 Application initialized. Waiting for exit signal...")

    # Wait for shutdown signal (Ctrl+C, SIGTERM, etc.)
    await coordinator.wait_for_shutdown()

    # Execute shutdown sequence in priority order
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
        sys.exit(0)
