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
from components import ControlPanel, KeyboardInputAdapter, PreviewPanel
from hardware.gpio.gpio_manager import GPIOManager
from controllers.led_controller.led_controller import LEDController
from controllers import ControlPanelController, PreviewPanelController, ZoneStripController
from managers import ConfigManager
from services import EventBus, DataAssembler, ZoneService, AnimationService, ApplicationStateService
from services.middleware import log_middleware
from services.transition_service import TransitionService

# ---------------------------------------------------------------------------
# LOGGER SETUP
# ---------------------------------------------------------------------------

log = get_logger().for_category(LogCategory.SYSTEM)

# DEBUG MODE: Set to True to disable animations/pulse/fades for testing
DEBUG_NOPULSE = False

configure_logger(LogLevel.DEBUG)

# ---------------------------------------------------------------------------
# SHUTDOWN & CLEANUP
# ---------------------------------------------------------------------------

def emergency_gpio_cleanup():
    """Emergency cleanup - called on any exit (crashes, seg faults)."""
    try:
        gpio_manager = GPIOManager()
        gpio_manager.cleanup()
        log.info("🚨 Emergency GPIO cleanup completed")
    except Exception as e:
        log.error(f"Failed to cleanup GPIO on exit: {e}")


async def shutdown(loop: asyncio.AbstractEventLoop, signal_name: str) -> None:
    """Gracefully shut down all tasks and hardware."""
    if signal_name:
        log.info(f"Received signal: {signal_name} → initiating graceful shutdown...")

    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
    log.debug(f"Cancelling {len(tasks)} running tasks...")
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.sleep(0.05)
    log.info("Shutdown complete. Goodbye!")


def _create_zone_strips(zone_service, config_manager):
    """Create and configure LED strip drivers for all GPIO pins."""
    from zone_layer.zone_strip import ZoneStrip
    from hardware.led.ws281x_strip import WS281xStrip, WS281xConfig

    all_zones = zone_service.get_all()
    zones_by_gpio = {}
    for zone in all_zones:
        gpio = zone.config.gpio
        if gpio not in zones_by_gpio:
            zones_by_gpio[gpio] = []
        zones_by_gpio[gpio].append(zone.config)

    hardware_mappings = config_manager.hardware_manager.get_gpio_to_zones_mapping()
    zone_strips = {}

    for gpio_pin in sorted(zones_by_gpio.keys()):
        zones_for_gpio = zones_by_gpio[gpio_pin]

        hardware_config = None
        for hw in hardware_mappings:
            if hw["gpio"] == gpio_pin:
                hardware_config = hw
                break

        if not hardware_config:
            log.warn(f"No config for GPIO {gpio_pin}, skipping")
            continue

        pixel_count = sum(z.pixel_count for z in zones_for_gpio)

        ws_config = WS281xConfig(
            gpio_pin=gpio_pin,
            led_count=pixel_count,
            color_order=hardware_config["color_order"],
            frequency_hz=800_000,
            dma_channel=10,
            brightness=255,
            invert=False,
            channel=0 if gpio_pin == 18 else (1 if gpio_pin == 19 else 0),
        )
        hardware = WS281xStrip(ws_config)
        strip = ZoneStrip(pixel_count=pixel_count, zones=zones_for_gpio, hardware=hardware)
        zone_strips[gpio_pin] = strip
        log.info(f"Created ZoneStrip GPIO {gpio_pin}: {pixel_count} pixels, {len(zones_for_gpio)} zones")

    return zone_strips


async def cleanup_application(
    led_controller,
    zone_strip_transition_service,
    gpio_manager,
    keyboard_task,
    polling_task,
    zone_strips
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
    # await led_controller.static_mode_controller._stop_pulse_async()
    await asyncio.sleep(0.05)

    # Fade out
    # log.info("Performing shutdown transition...")
    await zone_strip_transition_service.fade_out(zone_strip_transition_service.SHUTDOWN)

    # Clear LEDs (ALL strips, not just GPIO 18)
    log.info("Clearing LEDs on all GPIO strips...")
    led_controller.clear_all()
    for gpio_pin, strip in zone_strips.items():
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
    zone_strips = _create_zone_strips(zone_service, config_manager)
    zone_strip = zone_strips.get(18, list(zone_strips.values())[0])

    # PREVIEW PANEL: TEMPORARILY DISABLED
    # Treating last 8 pixels (PREVIEW zone) as normal zone for now

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
    # PREVIEW PANEL DISABLED - will enable after testing main LED strips
    # preview_panel_transition_service = TransitionService(control_panel.preview_panel, frame_manager)
    preview_panel_transition_service = None

    # ========================================================================
    # LAYER 2: CONTROLLERS
    # ========================================================================

    log.info("Initializing controllers...")
    zone_strip_controller = ZoneStripController(zone_strip, zone_strip_transition_service, frame_manager)
    # PREVIEW PANEL DISABLED
    # preview_panel_controller = PreviewPanelController(control_panel.preview_panel, preview_panel_transition_service)
    preview_panel_controller = None
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
        
    # PREVIEW PANEL DISABLED
    # Set parent controller reference for preview panel (needed for power toggle fade)
    # if preview_panel_controller:
    #     preview_panel_controller._parent_controller = led_controller

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
    zones = zone_service.get_all()
    await zone_strip_controller.startup_fade_in(zones, zone_strip_transition_service.STARTUP)

    # ========================================================================
    # RUN LOOPS
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
            polling_task,
            zone_strips
        )



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Handled in main()'s finally block
