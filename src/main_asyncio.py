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

from models.enums import LogCategory, LogLevel
from components import ControlPanel, KeyboardInputAdapter, ZoneStrip
from infrastructure import GPIOManager
from controllers.led_controller.led_controller import LEDController
from controllers import ControlPanelController, PreviewPanelController, ZoneStripController
from managers import ConfigManager
from services import EventBus, DataAssembler, ZoneService, AnimationService, ApplicationStateService
from services.middleware import log_middleware
from services.transition_service import TransitionService

from models.enums import AnimationID

# ---------------------------------------------------------------------------
# LOGGER SETUP
# ---------------------------------------------------------------------------

log = get_logger().for_category(LogCategory.SYSTEM)


configure_logger(LogLevel.DEBUG)
# ---------------------------------------------------------------------------
# SHUTDOWN & CLEANUP
# ---------------------------------------------------------------------------

async def shutdown(loop: asyncio.AbstractEventLoop, signal_name: str) -> None:
    """Gracefully shut down all tasks and hardware."""
    if signal_name:
        log.info(f"Received signal: {signal_name} → initiating graceful shutdown...")

    # Cancel all running tasks except current
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
    log.debug(f"Cancelling {len(tasks)} running tasks...")
    for task in tasks:
        task.cancel()

    # Wait for cancellation
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Allow pending logs to flush
    await asyncio.sleep(0.05)
    log.info("Shutdown complete. Goodbye!")


async def cleanup_application(
    led_controller,
    zone_strip_transition_service,
    gpio_manager,
    keyboard_task,
    polling_task
) -> None:
    """Perform graceful application cleanup on shutdown."""
    log.info("🧹 Starting cleanup...")

    # Cancel polling and keyboard tasks
    if not keyboard_task.done():
        keyboard_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await keyboard_task

    if not polling_task.done():
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
    await led_controller.static_mode_controller._stop_pulse_async()
    await asyncio.sleep(0.05)

    # Fade out
    log.info("Performing shutdown transition...")
    await zone_strip_transition_service.fade_out(zone_strip_transition_service.SHUTDOWN)

    # Clear LEDs
    log.info("Clearing LEDs...")
    led_controller.clear_all()

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
    # INFRASTRUCTURE
    # ========================================================================

    log.info("Initializing GPIO manager (singleton)...")
    gpio_manager = GPIOManager()

    log.info("Loading configuration...")
    config_manager = ConfigManager(gpio_manager)
    config_manager.load()

    log.info("Initializing event bus...")
    event_bus = EventBus()
    event_bus.add_middleware(log_middleware)
    
    # Register GPIO cleanup on exit (handles crashes and segfaults)
    def emergency_gpio_cleanup():
        """Emergency GPIO cleanup - called on any exit (including crashes)"""
        try:
            gpio_manager.cleanup()
            log.info("🚨 Emergency GPIO cleanup completed")
        except Exception as e:
            log.error(f"Failed to cleanup GPIO on exit: {e}")

    atexit.register(emergency_gpio_cleanup)

    # ========================================================================
    # REPOSITORY & SERVICES
    # ========================================================================

    log.info("Loading application state...")
    state_file = Path(__file__).resolve().parent / "state" / "state.json"
    assembler = DataAssembler(config_manager, state_file)

    log.info("Initializing services...")
    animation_service = AnimationService(assembler)
    app_state_service = ApplicationStateService(assembler)
    zone_service = ZoneService(assembler, app_state_service)

    # ========================================================================
    # LAYER 1: HARDWARE
    # ========================================================================

    log.info("Initializing hardware control panel...")
    control_panel = ControlPanel(
        config_manager.hardware_manager,
        event_bus,
        gpio_manager
    )

    log.info("Initializing LED strips...")
    from engine.frame_manager import FrameManager

    # Create ZoneStrips for each GPIO
    # Each strip gets only the zones assigned to its GPIO, with pixel indices reset to 0
    zone_strips = {}  # gpio -> ZoneStrip
    all_zones = zone_service.get_all()

    # Group zones by GPIO
    zones_by_gpio = {}
    for zone in all_zones:
        gpio = zone.config.gpio
        if gpio not in zones_by_gpio:
            zones_by_gpio[gpio] = []
        zones_by_gpio[gpio].append(zone.config)

    # Map GPIO pins to DMA channels
    # GPIO 18 uses DMA 10 (default), other GPIOs use different channels to avoid conflicts
    gpio_to_dma = {
        18: 10,  # MAIN_12V on GPIO 18
        19: 11,  # AUX_5V on GPIO 19 (use DMA 11 to avoid conflict with GPIO 18)
    }
    gpio_to_pwm = {
        18: 0,  # MAIN_12V on GPIO 18
        19: 1,  # AUX_5V on GPIO 19 (use DMA 11 to avoid conflict with GPIO 18)
    }

    # Create a ZoneStrip for each GPIO
    # Zones already have correct pixel indices (per-GPIO) from ConfigManager.get_all_zones()
    for gpio_pin, zones_for_gpio in sorted(zones_by_gpio.items()):
        # Calculate total pixels for this GPIO
        pixel_count_for_gpio = sum(z.pixel_count for z in zones_for_gpio)

        # Get DMA channel for this GPIO (default to 10)
        dma_channel = gpio_to_dma.get(gpio_pin, 10)
        pwm_channel = gpio_to_pwm.get(gpio_pin, 0)
        # Create ZoneStrip for this GPIO
        strip = ZoneStrip(
            gpio=gpio_pin,
            pixel_count=pixel_count_for_gpio,
            zones=zones_for_gpio,
            gpio_manager=gpio_manager,
            dma_channel=dma_channel,
            pwm_channel=pwm_channel
        )
        zone_strips[gpio_pin] = strip
        log.info(f"Created ZoneStrip on GPIO {gpio_pin} (DMA {dma_channel}) with {pixel_count_for_gpio} pixels ({len(zones_for_gpio)} zones)")

    # Use main zone strip (GPIO 18) as the primary strip for controllers
    zone_strip = zone_strips.get(18, list(zone_strips.values())[0])

    # ========================================================================
    # FRAME MANAGER
    # ========================================================================

    log.info("Initializing FrameManager...")
    frame_manager = FrameManager(fps=60)

    # Register all LED strips with FrameManager
    for gpio_pin, strip in zone_strips.items():
        frame_manager.add_main_strip(strip)
        log.info(f"Registered ZoneStrip (GPIO {gpio_pin}) with FrameManager")

    # ========================================================================
    # SERVICES: TRANSITIONS
    # ========================================================================

    log.info("Creating transition services...")
    zone_strip_transition_service = TransitionService(zone_strip, frame_manager)
    preview_panel_transition_service = TransitionService(control_panel.preview_panel, frame_manager)

    # ========================================================================
    # LAYER 2: CONTROLLERS
    # ========================================================================

    log.info("Initializing controllers...")
    zone_strip_controller = ZoneStripController(zone_strip, zone_strip_transition_service, frame_manager)
    preview_panel_controller = PreviewPanelController(control_panel.preview_panel, preview_panel_transition_service)
    control_panel_controller = ControlPanelController(control_panel, event_bus)

    # ========================================================================
    # LAYER 3: APPLICATION
    # ========================================================================

    log.info("Initializing LED controller...")
    led_controller = LEDController(
        config_manager=config_manager,
        event_bus=event_bus,
        gpio_manager=gpio_manager,
        zone_service=zone_service,
        animation_service=animation_service,
        app_state_service=app_state_service,
        preview_panel_controller=preview_panel_controller,
        zone_strip_controller=zone_strip_controller,
        frame_manager=frame_manager
    )

    # ========================================================================
    # FRAME MANAGER STARTUP
    # ========================================================================

    log.info("Starting FrameManager render loop...")
    asyncio.create_task(frame_manager.start())
    log.info("FrameManager running.")
        
    # Set parent controller reference for preview panel (needed for power toggle fade)
    preview_panel_controller._parent_controller = led_controller

    # ========================================================================
    # ADAPTERS
    # ========================================================================

    log.info("Initializing keyboard input...")
    keyboard_adapter = KeyboardInputAdapter(event_bus)
    keyboard_task = asyncio.create_task(keyboard_adapter.run())

    # ========================================================================
    # STARTUP TRANSITION
    # ========================================================================
    
    log.info("Performing startup transition...")
    await zone_strip_controller.startup_fade_in(zone_service, zone_strip_transition_service.STARTUP)

    # ========================================================================
    # RUN LOOPS
    # ========================================================================

    async def hardware_polling_loop():
        """Poll hardware inputs at 50Hz"""
        try:
            while True:
                await control_panel_controller.poll()
                await asyncio.sleep(0.02)
        except asyncio.CancelledError:
            log.debug("Hardware polling loop cancelled.")
            raise
    
        
    polling_task = asyncio.create_task(hardware_polling_loop(), name="HardwarePolling")
    
    # Register signal handlers for graceful exit
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(loop, s.name)))

    try:
        await asyncio.gather(keyboard_task, polling_task)
    except asyncio.CancelledError:
        log.debug("Main loop cancelled.")
    finally:
        await cleanup_application(
            led_controller,
            zone_strip_transition_service,
            gpio_manager,
            keyboard_task,
            polling_task
        )



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Handled in main()'s finally block
