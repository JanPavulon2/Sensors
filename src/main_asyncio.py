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
import asyncio

# Set UTF-8 encoding for output BEFORE any imports (fixes Unicode symbol rendering)
if hasattr(sys.stdout, 'reconfigure') and sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
if hasattr(sys.stderr, 'reconfigure') and sys.stderr.encoding != 'UTF-8':
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore

from pathlib import Path

# === Lifecycle Management ===
from lifecycle.handlers import (
    AllTasksCancellationHandler, AnimationShutdownHandler, APIServerShutdownHandler, FrameManagerShutdownHandler,
    GPIOShutdownHandler, IndicatorShutdownHandler, LEDShutdownHandler, TaskCancellationHandler
)
from lifecycle.api_server_wrapper import APIServerWrapper
from lifecycle import ShutdownCoordinator
from lifecycle.task_registry import (
    create_tracked_task,
    TaskCategory,
    TaskRegistry
)

# === Logger Setup ===
from utils.logger import get_logger, configure_logger
from models.enums import LogCategory, LogLevel

# === API ===
from api.main import create_app
from api.dependencies import set_service_container
from api.socketio.server import create_socketio_server, wrap_app_with_socketio
from api.socketio.registry import register_socketio

# === Infrastructure ===
from hardware.gpio.gpio_manager_factory import create_gpio_manager
from hardware.hardware_coordinator import HardwareCoordinator
from hardware.input.keyboard import start_keyboard

# === Services ===
from services.port_manager import PortManager
from services.service_container import ServiceContainer
from services.snapshot_publisher import SnapshotPublisher
from services.log_broadcaster import get_broadcaster
from services import (
    EventBus, DataAssembler, ZoneService, AnimationService,
    ApplicationStateService, ServiceContainer
)
from services.middleware import log_middleware
from services.transition_service import TransitionService

# === Managers ===
from managers import ConfigManager

# === Controllers ===
from controllers.led_controller.lighting_controller import LightingController
from controllers import ControlPanelController

# === Engine ===
from engine.frame_manager import FrameManager

# === Runtime ===
from runtime.runtime_info import RuntimeInfo

# ---------------------------------------------------------------------------
# LOGGER SETUP
# ---------------------------------------------------------------------------

log = get_logger().for_category(LogCategory.SYSTEM)
configure_logger(LogLevel.DEBUG)

# ---------------------------------------------------------------------------
# Application Entry
# ---------------------------------------------------------------------------

async def main():
    """Main async entry point (dependency injection and event loop startup)."""

    log.info("Initializing Diuna application...")

    # Create Socket.IO server
    log.info("Creating Socket.IO server...")
    
    cors_origins = []
    if cors_origins is None:
        cors_origins = [
            "http://192.168.137.139:3000",
            "http://192.168.137.139:8000",
            "http://192.168.137.139:5173",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:5173",
        ]
        
    socketio_server = create_socketio_server(cors_origins=["*"])
    
    # Initialize broadcaster early so all logs can be transmitted
    broadcaster = get_broadcaster()
    broadcaster.set_socketio_server(socketio_server)
    broadcaster.start()
    
    get_logger().set_broadcaster(broadcaster)
    
    log.info("Socket.IO + LogBroadcaster initialized (early)")
    
    # ========================================================================
    # 1. INFRASTRUCTURE
    # ========================================================================
    runtime = RuntimeInfo()

    log.info(
        "Runtime detected",
        linux=runtime.is_linux(),
        rpi=runtime.is_raspberry_pi(),
        windows=runtime.is_windows(),
        has_ws281x=runtime.has_ws281x(),
        has_evdev=runtime.has_evdev(),
        has_gpio=runtime.has_gpio(),
    )

    log.info("Initializing GPIO manager (singleton)...")
    gpio_manager = create_gpio_manager()

    log.info("Loading configuration...")
    config_manager = ConfigManager(gpio_manager)
    config_manager.load()

    log.info("Initializing event bus...")
    event_bus = EventBus().instance()
    event_bus.add_middleware(log_middleware)

    log.info("Loading application state...")
    state_file = Path(__file__).resolve().parent / "state" / "state.json"
    assembler = DataAssembler(config_manager, state_file)

    log.info("Initializing services...")
    animation_service = AnimationService(assembler)
    app_state_service = ApplicationStateService(assembler)
    zone_service = ZoneService(assembler, app_state_service, event_bus)

    # ========================================================================
    # 2. HARDWARE COORDINATOR
    # ========================================================================

    log.info("Initializing hardware stack...")
    hardware = HardwareCoordinator(
        hardware_manager=config_manager.hardware_manager,
        gpio_manager=gpio_manager
    ).initialize(
        all_zones = zone_service.get_all()
    )

    control_panel_controller = ControlPanelController(
        control_panel=hardware.control_panel,
        event_bus=event_bus
    )
        
        
    # ========================================================================
    # 3. FRAME MANAGER
    # ========================================================================

    log.info("Initializing FrameManager...")
    frame_manager = FrameManager(fps=60)
    frame_manager_task = create_tracked_task(
        frame_manager.start(),
        category=TaskCategory.RENDER,
        description="Frame Manager render loop"
    )

    # Register all LED strips with FrameManager
    for gpio_pin, strip in hardware.led_channels.items():
        frame_manager.add_led_channel(strip)
        # Create TransitionService for this strip (used by FrameManager internally)
        transition_service = TransitionService(strip, frame_manager)
        log.info(f"Zone strip registered on GPIO {gpio_pin}", category=LogCategory.FRAME_MANAGER)

    
    # ========================================================================
    # 4. SERVICE CONTAINER
    # ========================================================================

    services = ServiceContainer(
        event_bus=event_bus,
        zone_service=zone_service,
        animation_service=animation_service,
        app_state_service=app_state_service,
        frame_manager=frame_manager,
        color_manager=config_manager.color_manager,
        config_manager=config_manager,
        data_assembler=assembler
    )
    
    snapshot_publisher = SnapshotPublisher(
        zone_service=zone_service,
        event_bus=event_bus,
    )


    # Register service container with API for dependency injection
    set_service_container(services)
    log.info("Service container registered")

    log.info("Initializing LED controller...")
    lighting_controller = LightingController(
        service_container=services
    )
    log.info("Finished initializing LED controller...")


    # ========================================================================
    # 6. ADAPTERS (Keyboard)
    # ========================================================================

    log.info("Initializing keyboard input...")
    keyboard_task = create_tracked_task(
        start_keyboard(event_bus),
        category=TaskCategory.INPUT,
        description="KeyboardInput"
    )

    # ========================================================================
    # 7. HARDWARE POLLING LOOP
    # ========================================================================

    async def hardware_polling_loop():
        """Poll hardware inputs at 50Hz"""
        
        if control_panel_controller is None: 
            log.warn("Control Panel Controller is NONE")
            return
        
        try:
            while True:
                try:
                    await control_panel_controller.poll()
                except Exception as error:
                    log.error(f"Hardware polling error: {error}", exc_info=True)
                await asyncio.sleep(0.02)
        except asyncio.CancelledError:
            log.debug("Hardware polling loop cancelled", category=LogCategory.HARDWARE)
            raise
        
    if control_panel_controller:
        polling_task =  create_tracked_task(
            hardware_polling_loop(),
            category=TaskCategory.HARDWARE,
            description="ControlPanel Polling Loop"
        )
    else:
        polling_task = None

    
    log.info("Registering Socket.IO modules...")
    register_socketio(socketio_server, services)
        
    # ========================================================================
    # 8. API SERVER
    # ========================================================================

    # Ensure port is free before starting API server
    # (recovery from previous crashes that left port orphaned)
    log.info("Checking API port availability...")
    port_mgr = PortManager.instance()
    await port_mgr.ensure_available(port=8000)

    log.info("Creating FastAPI app...")
    fastapi_app = create_app(
        title="Diuna LED System",
        version="1.0.0",
        docs_enabled=True,
        cors_origins=["*"]
    )
    
    log.info("Wrapping FastAPI app with Socket.IO...")
    app = wrap_app_with_socketio(fastapi_app, socketio_server)
    
    api_wrapper = APIServerWrapper(app, host="0.0.0.0", port=8000)

    log.info("Starting FastAPI app...")
    api_task = create_tracked_task(
        api_wrapper.start(),
        category=TaskCategory.API,
        description="FastAPI/Uvicorn Server"
    )
    
    log.info("FastAPI app started")

    # ============================================================
    # 10. SHUTDOWN COORDINATOR
    # ============================================================

    log.info("Initializing shutdown system...")

    coordinator = ShutdownCoordinator()
    coordinator.register(APIServerShutdownHandler(api_wrapper))  # ← Pass wrapper, not task
    coordinator.register(AnimationShutdownHandler(lighting_controller))
    coordinator.register(IndicatorShutdownHandler(lighting_controller.selected_zone_indicator))
    coordinator.register(FrameManagerShutdownHandler(frame_manager))  # ← Frame manager cleanup (includes executor shutdown)
    coordinator.register(LEDShutdownHandler(hardware))
    
    if polling_task:
        coordinator.register(TaskCancellationHandler([frame_manager_task, keyboard_task, polling_task]))  # ← Add frame manager task
    
    coordinator.register(AllTasksCancellationHandler([api_task]))  # ← Catch any remaining tasks (safety net)
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
