"""
LED Control Station - Main Entry Point

Asyncio-based event-driven architecture for Raspberry Pi LED control.
See CLAUDE.md for full architecture documentation.
"""

import sys
import os

# Set UTF-8 encoding for output BEFORE any imports (fixes Unicode symbol rendering)
if hasattr(sys.stdout, 'reconfigure') and sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
if hasattr(sys.stderr, 'reconfigure') and sys.stderr.encoding != 'UTF-8':
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore

import asyncio
from utils.logger import get_logger, configure_logger
from models.enums import LogLevel
from components import ControlModule
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

    # Initialize LED controller (loads state via DataAssembler)
    log.system("Initializing LED controller...")
    led = LEDController(config_manager, event_bus)

    # Register middleware
    log.system("Registering middleware...")
    event_bus.add_middleware(log_middleware)

    # Initialize hardware control module
    log.system("Initializing hardware...")
    if config_manager.hardware_manager is None:
        log.system("ERROR: Hardware manager not initialized!")
        return
    module = ControlModule(config_manager.hardware_manager, event_bus)

    async def hardware_loop():
        """Poll hardware inputs at 100Hz"""
        while True:
            module.poll()
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

        log.system("Stopping animations...")
        await led.animation_engine.stop()

        log.system("Stopping pulsing...")
        led._stop_pulse()
        await asyncio.sleep(0.1)  # Let colors restore

        log.system("Clearing LEDs...")
        led.clear_all()

        log.system("Cleaning up GPIO...")
        module.cleanup()

        log.system("Shutdown complete. Goodbye!")



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Handled in main()'s finally block
