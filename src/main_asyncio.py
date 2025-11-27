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
from typing import List

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
from pathlib import Path
from utils.logger import get_logger, configure_logger

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

# ---------------------------------------------------------------------------
# SHUTDOWN & CLEANUP
# ---------------------------------------------------------------------------

def emergency_gpio_cleanup():
    """Emergency cleanup - called on any exit (crashes, seg faults)."""
    try:
        GPIOManager().cleanup()
        log.info("🚨 Emergency GPIO cleanup completed")
    except Exception as e:
        log.error(f"Failed to cleanup GPIO: {e}")

async def shutdown(loop: asyncio.AbstractEventLoop, signal_name: str) -> None:
    """Gracefully shut down all tasks and hardware."""
    if signal_name:
        log.info(f"Received signal: {signal_name} → initiating graceful shutdown...")

    tasks = [
        t for t in asyncio.all_tasks(loop) 
        if t is not asyncio.current_task(loop)
    ]
    
    log.debug(f"Cancelling {len(tasks)} running tasks...")
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.sleep(0.05)
    log.info("Shutdown complete. Goodbye!")


async def cleanup_application(
    led_controller: LightingController,
    gpio_manager: GPIOManager,
    hardware: HardwareBundle,
    keyboard_task: asyncio.Task,
    polling_task: asyncio.Task
) -> None:
    """Perform graceful application cleanup on shutdown."""
    log.info("🧹 Starting cleanup...")

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
    led_controller.animation_mode_controller.animation_service.stop_all()
    if led_controller.animation_engine and led_controller.animation_engine.is_running():
        await led_controller.animation_engine.stop()

    # Stop pulsing
    log.info("Stopping pulsing...")
    # await led_controller.static_mode_controller._stop_pulse_async()
    await asyncio.sleep(0.05)

    # Fade out
    # log.info("Performing shutdown transition...")
    # await zone_strip_transition_service.fade_out(zone_strip_transition_service.SHUTDOWN)

    # Clear LEDs (ALL strips, not just GPIO 18)
    log.info("Clearing LEDs on all GPIO strips...")
    led_controller.clear_all()
    for gpio_pin, strip in hardware.zone_strips.items():
        log.info(f"Clearing GPIO {gpio_pin}...")
        strip.clear()

    # Cleanup GPIO
    log.info("Cleaning up GPIO...")
    gpio_manager.cleanup()

    log.info("Cleanup complete.")


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

    hardware_coordinator = HardwareCoordinator(
        hardware_manager=config_manager.hardware_manager,
        gpio_manager=gpio_manager
    )
    
    hardware = hardware_coordinator.initialize(
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
    asyncio.create_task(frame_manager.start())

    zone_strip_controllers = {}
    
    # Register all LED strips with FrameManager
    for gpio_pin, strip in hardware.zone_strips.items():
        frame_manager.add_zone_strip(strip)
        transition_service = TransitionService(strip, frame_manager)
        controller = ZoneStripController(strip, transition_service, frame_manager)
        
        zone_strip_controllers[gpio_pin] = controller

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
    
    log.info("Initializing LED controller...")
    lightning_controller = LightingController(
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
    keyboard_adapter = KeyboardInputAdapter(event_bus)
    keyboard_task = asyncio.create_task(keyboard_adapter.run())


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
    
        
    polling_task = asyncio.create_task(hardware_polling_loop(), name="HardwarePolling")
    
    
    # ========================================================================
    # SIGNAL HANDLERS
    # ========================================================================

    # Register signal handlers for graceful exit
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(loop, s.name)))


    # ========================================================================
    # MAIN TASK GATHER
    # ========================================================================

    try:
        await asyncio.gather(keyboard_task, polling_task)
    except asyncio.CancelledError:
        log.debug("Main loop cancelled.")
    finally:
        await cleanup_application(
            lightning_controller,
            gpio_manager,
            hardware,
            keyboard_task,
            polling_task
        )


# ---------------------------------------------------------------------------
# ENTRY
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Handled in main()'s finally block
