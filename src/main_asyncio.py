"""
LED Control Station - Main Entry Point

Asyncio-based event-driven architecture for Raspberry Pi LED control.
See CLAUDE.md for full architecture documentation.
"""

import sys
import os

# Set UTF-8 encoding for output BEFORE any imports (fixes Unicode symbol rendering)
if sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'UTF-8':
    sys.stderr.reconfigure(encoding='utf-8')

import asyncio
from utils.logger import get_logger, configure_logger
from models.enums import LogLevel
from components import ControlModule
from controllers.led_controller import LEDController
from managers.config_manager import ConfigManager

# Configure UTF-8 encoding for terminal output (support unicode icons)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

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

    # Initialize hardware control module
    log.system("Initializing hardware...")
    module = ControlModule(config_manager.hardware_manager)

    # Initialize LED controller (loads state via DataAssembler)
    log.system("Initializing LED controller...")
    led = LEDController(config_manager)

    # Hardware event handlers (callback pattern)
    # TODO: Migrate to Event Bus architecture (Phase 3)

    def handle_zone_change(delta):
        """Selector encoder rotated - context-sensitive (zone select or animation select)"""
        led.handle_selector_rotation(delta)

    def handle_zone_selector_click():
        """Selector encoder clicked - context-sensitive action"""
        led.handle_selector_click()

    def handle_modulator(delta):
        """Modulator encoder rotated - adjust parameter value (context-sensitive)"""
        led.handle_modulator_rotation(delta)

    def handle_modulator_click():
        """Modulator encoder clicked - cycle parameters"""
        led.handle_modulator_click()

    def handle_button1():
        """Button 1: Toggle EDIT MODE"""
        led.toggle_edit_mode()

    def handle_button2():
        """Button 2: Quick action - Lamp warm white"""
        led.quick_lamp_white()

    def handle_button3():
        """Button 3: Power toggle"""
        led.power_toggle()

    def handle_button4():
        """Button 4: Toggle STATIC/ANIMATION mode"""
        led.toggle_main_mode()

    async def hardware_loop():
        """Poll hardware inputs at 100Hz"""
        while True:
            module.poll()
            await asyncio.sleep(0.01)

    # Wire callbacks to hardware events
    module.on_selector_rotate = handle_zone_change
    module.on_selector_click = handle_zone_selector_click
    module.on_modulator_rotate = handle_modulator
    module.on_modulator_click = handle_modulator_click
    module.on_button[0] = handle_button1
    module.on_button[1] = handle_button2
    module.on_button[2] = handle_button3
    module.on_button[3] = handle_button4

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
