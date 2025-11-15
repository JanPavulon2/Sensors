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
from pathlib import Path

from utils.logger2 import get_logger, configure_logger

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
# SHUTDOWN HANDLER
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
    

# ---------------------------------------------------------------------------
# Application Entry
# ---------------------------------------------------------------------------

async def main():
    """Main async entry point (dependency injection and event loop startup)."""

    log.info("Starting Diuna application...")

    # ========================================================================
    # INFRASTRUCTURE
    # ========================================================================

    log.info("Loading configuration...")
    config_manager = ConfigManager()
    config_manager.load()

    log.info("Initializing event bus...")
    event_bus = EventBus()
    event_bus.add_middleware(log_middleware)

    log.info("Initializing GPIO manager...")
    gpio_manager = GPIOManager()

    # ========================================================================
    # REPOSITORY & SERVICES
    # ========================================================================

    log.info("Loading application state...")
    state_file = Path(__file__).resolve().parent / "state" / "state.json"
    assembler = DataAssembler(config_manager, state_file)

    log.info("Initializing services...")
    zone_service = ZoneService(assembler)
    animation_service = AnimationService(assembler)
    app_state_service = ApplicationStateService(assembler)

    # ========================================================================
    # LAYER 1: HARDWARE
    # ========================================================================

    log.info("Initializing hardware control panel...")
    control_panel = ControlPanel(
        config_manager.hardware_manager,
        event_bus,
        gpio_manager
    )

    log.info("Initializing LED strip...")
    zone_strip = ZoneStrip(
        gpio=config_manager.hardware_manager.get_led_strip("zone_strip")["gpio"],  # type: ignore
        pixel_count=zone_service.get_total_pixel_count(),
        zones=[z.config for z in zone_service.get_all()],
        gpio_manager=gpio_manager
    )

    # ========================================================================
    # FRAME MANAGER
    # ========================================================================

    log.info("Initializing FrameManager...")
    from engine.frame_manager import FrameManager
    frame_manager = FrameManager(fps=60)

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

    # Ensure frame manager exists and start it
    if hasattr(led_controller, "frame_manager"):
        frame_manager = led_controller.frame_manager
    elif hasattr(led_controller, "frame_manager"):
        frame_manager = led_controller.frame_manager
    else:
        frame_manager = None

    if frame_manager:
        log.info("Starting FrameManager render loop...")
        asyncio.create_task(frame_manager.start())
        log.info("FrameManager running.")
    else:
        log.warn("⚠ No FrameManager found — animations may not render.")
        
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
    # SYSTEM STATUS
    # ========================================================================

    log.info("=" * 60)
    log.info("Initial state loaded:")
    log.info(f"  Mode: {led_controller.main_mode.name}")
    log.info(f"  Edit Mode: {'ON' if led_controller.edit_mode else 'OFF'}")
    log.info("=" * 60)
    log.info("System ready. Press Ctrl+C to exit.")
    log.info("=" * 60)

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
        # Graceful cleanup
        log.info("🧹 Starting cleanup...")

        if not keyboard_task.done():
            keyboard_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keyboard_task
                
        
        if not polling_task.done():
            polling_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await polling_task

        log.info("Stopping animations...")
        led_controller.animation_mode_controller.animation_service.stop_all()
        
        
        log.info("Stopping pulsing...")
        led_controller.static_mode_controller._stop_pulse()
        await asyncio.sleep(0.05)

        log.info("Performing shutdown transition...")
        await zone_strip_transition_service.fade_out(zone_strip_transition_service.SHUTDOWN)

        keyboard_task.cancel()
        try:
            await keyboard_task
        except asyncio.CancelledError:
            pass

        # Stop animations safely
        log.info("Stopping animations...")
        if led_controller.animation_engine and led_controller.animation_engine.is_running():
            await led_controller.animation_engine.stop()

        if hasattr(led_controller, "animation_service"):
            led_controller.animation_service.stop_all()
            
        log.info("Clearing LEDs...")
        led_controller.clear_all()

        log.info("Cleaning up GPIO...")
        gpio_manager.cleanup()

        log.info("Shutdown complete. Goodbye!")



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Handled in main()'s finally block
