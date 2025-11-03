"""
LED Control Station - Main Entry Point

Asyncio-based event-driven architecture for Raspberry Pi LED control.
See CLAUDE.md for full architecture documentation.
"""

import sys
import os

from managers.GPIOManager import GPIOManager

# Set UTF-8 encoding for output BEFORE any imports (fixes Unicode symbol rendering)
if hasattr(sys.stdout, 'reconfigure') and sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
if hasattr(sys.stderr, 'reconfigure') and sys.stderr.encoding != 'UTF-8':
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore

import asyncio
from utils.logger import get_logger, configure_logger
from models.enums import LogLevel
from components import ControlPanel, KeyboardInputAdapter
from controllers.led_controller import LEDController
from managers.config_manager import ConfigManager
from services.event_bus import EventBus
from services.middleware import log_middleware

configure_logger(LogLevel.INFO)
log = get_logger()


async def main():
    """Main application entry point"""
    log.system("=" * 60)
    log.system("LED Control Station - Starting...")
    log.system("=" * 60)

    # Load configuration
    log.system("Loading configuration...")
    config_manager = ConfigManager()
    config_manager.load()

    # Create event bus
    log.system("Initializing event bus...")
    event_bus = EventBus()

    # Register middleware
    log.system("Registering event bus middleware...")
    event_bus.add_middleware(log_middleware)

    # Initialize GPIO manager (MUST be first - all hardware components register pins here)
    log.system("Initializing GPIO manager...")
    gpio_manager = GPIOManager()

    # Initialize LED controller (loads state via DataAssembler, registers WS281x pins)
    log.system("Initializing LED controller...")
    led = LEDController(config_manager, event_bus, gpio_manager)

    # await asyncio.sleep(2)

    # Initialize keyboard input adapter (runs in background)
    log.system("Initializing keyboard input adapter...")
    keyboard_adapter = KeyboardInputAdapter(event_bus)
    keyboard_task = asyncio.create_task(keyboard_adapter.run())

    # Initialize hardware control panel (registers encoders, buttons, preview panel pins)
    log.system("Initializing hardware...")
    if config_manager.hardware_manager is None:
        log.system("ERROR: Hardware manager not initialized!")
        return
    control_panel = ControlPanel(config_manager.hardware_manager, event_bus, gpio_manager)

    # Log GPIO pin allocations (useful for debugging conflicts)
    gpio_manager.log_registry()

    async def hardware_loop():
        """Poll hardware inputs at 100Hz"""
        while True:
            control_panel.poll()
            await asyncio.sleep(0.01)

    # Log initial state
    status = led.get_status()
    log.system("Initial state loaded:")
    log.system(f"  Mode: {led.main_mode.name}")
    log.system(f"  Edit Mode: {'ON' if status['edit_mode'] else 'OFF'}")
    if led.main_mode.name == "STATIC":
        log.system(f"  Zone: {led._get_current_zone_id().name}")
        log.system(f"  Parameter: {led.current_param.name}")
    else:
        anim_id = led.current_animation_id
        log.system(f"  Animation: {anim_id.name if anim_id else 'None'}")
        log.system(f"  Parameter: {led.current_param.name}")

    log.system("=" * 60)
    log.system("System ready. Press Ctrl+C to exit.")
    log.system("=" * 60)
    
    try:
        await hardware_loop()
    except (asyncio.CancelledError, KeyboardInterrupt):
        log.system("Shutdown signal received")
    finally:
        # Graceful shutdown sequence
        log.system("Shutting down...")

        # Cancel keyboard input task first (prevents threading errors)
        log.system("Stopping keyboard input...")
        keyboard_task.cancel()
        try:
            await keyboard_task
        except asyncio.CancelledError:
            pass  # Expected - task was cancelled

        log.system("Stopping animations...")
        await led.animation_engine.stop()

        log.system("Stopping pulsing...")
        led._stop_pulse()
        await asyncio.sleep(0.1)  # Let colors restore

        log.system("Clearing LEDs...")
        led.clear_all()

        log.system("Cleaning up GPIO...")
        gpio_manager.cleanup()
        # module.cleanup()

        log.system("Shutdown complete. Goodbye!")



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Handled in main()'s finally block
