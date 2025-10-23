"""
LED Control Station - Main Entry Point

Event-driven architecture with state machine for LED control.

Hardware:
    - Preview Panel: GPIO 19 (8 LEDs, GRB) - CJMCU-2812-8
    - LED Strip: GPIO 18 (33 pixels = 99 LEDs, BRG) - WS2811
      Zones: lamp(19px), top(4px), right(3px), bottom(4px), left(3px)
    - Zone Selector: Encoder 1 (CLK=5, DT=6, SW=13)
    - Modulator: Encoder 2 (CLK=16, DT=20, SW=21)

Controls:
    - Zone Selector: Rotate = change zone, Click = (future)
    - Modulator: Rotate = adjust parameter (color/brightness), Click = switch mode

Modes:
    - COLOR_EDIT: Modulator adjusts hue
    - BRIGHTNESS_EDIT: Modulator adjusts brightness
"""

import sys
import asyncio
from utils.logger import get_logger, configure_logger
from models.enums import LogLevel 
from control_module import ControlModule
from led_controller import LEDController
from managers.config_manager import ConfigManager
from managers.state_manager import StateManager

# Configure UTF-8 encoding for terminal output (support unicode icons)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

configure_logger(LogLevel.DEBUG)
log = get_logger()
    
    
async def main():
    log.system("Logger test")
    
    print("=" * 60)
    print("LED Control Station")
    print("=" * 60)
    print()
    print("Hardware:")
    print("  - Preview Panel: GPIO 19 (8 LEDs, GRB) - CJMCU-2812-8")
    print("  - LED Strip: GPIO 18 (33 pixels = 99 physical LEDs, BRG) - WS2811")
    print("    Zones: lamp(19), top(4), right(3), bottom(4), left(3)")
    print("  - Zone Selector: Encoder 1")
    print("  - Modulator: Encoder 2")
    print()
    print("Controls:")
    print("  TWO MODES: STATIC (zone editing) <-> ANIMATION (animation control)")
    print("  Toggle with BTN4")
    print()
    print("  === STATIC MODE (default) ===")
    print("  ENCODER 1 (Upper):")
    print("    Rotate: Change zone (lamp -> top -> right -> bottom -> left)")
    print("    Click:  (unused)")
    print("  ENCODER 2 (Lower):")
    print("    Rotate: Adjust parameter value")
    print("    Click:  Cycle parameter (COLOR_HUE -> COLOR_PRESET -> BRIGHTNESS)")
    print()
    print("  === ANIMATION MODE ===")
    print("  ENCODER 1 (Upper):")
    print("    Rotate: Select animation (breathe -> color_fade -> snake -> color_snake)")
    print("    Click:  Start/Stop animation")
    print("  ENCODER 2 (Lower):")
    print("    Rotate: Adjust parameter value")
    print("    Click:  Cycle parameter (SPEED -> INTENSITY)")
    print()
    print("  === BUTTONS (all modes) ===")
    print("    BTN1: Toggle EDIT MODE (enable/disable editing)")
    print("    BTN2: Quick Lamp White (warm white @ full brightness)")
    print("    BTN3: Power toggle (all zones ON/OFF)")
    print("    BTN4: Toggle STATIC/ANIMATION mode")
    print()
    print("Starting...")
    print("=" * 60)

    # Load configuration (SINGLE ENTRY POINT)
    # ConfigManager loads all YAMLs and creates sub-managers
    config_manager = ConfigManager()
    config_manager.load()

    # Load state
    state_manager = StateManager()
    state = await state_manager.load()

    # Initialize hardware and controller (dependency injection)
    # ControlModule expects nested structure - provide hardware sub-dict
    # TODO: Refactor ControlModule to use HardwareManager directly
    hardware_config = {
        "hardware": {
            "encoders": config_manager.data.get("encoders", {}),
            "buttons": config_manager.data.get("buttons", []),
            "leds": config_manager.data.get("leds", {})
        }
    }
    module = ControlModule(hardware_config)

    # LEDController receives ConfigManager (not raw dict)
    led = LEDController(config_manager, state)

    # Helper function to save state
    def save_state():
        """Update and save state after LED changes"""
        state_manager.update_from_led(led)
        asyncio.create_task(state_manager.save())

    # Connect hardware events to LED controller

    def handle_zone_change(delta):
        """Upper encoder rotated - context-sensitive (zone select or animation select)"""
        led.handle_upper_rotation(delta)  # NEW: Two-mode system
        save_state()

    def handle_zone_selector_click():
        """Upper encoder clicked - cycle parameters (context-sensitive)"""
        led.handle_upper_click()  # NEW: Two-mode system
        save_state()

    def handle_modulator(delta):
        """Lower encoder rotated - adjust parameter value (context-sensitive)"""
        led.handle_lower_rotation(delta)  # NEW: Two-mode system
        save_state()

    def handle_modulator_click():
        """Lower encoder clicked - context-sensitive action"""
        led.handle_lower_click()  # NEW: Two-mode system
        save_state()

    def handle_button1():
        """Button 1: Toggle EDIT MODE"""
        led.toggle_edit_mode()
        save_state()

    def handle_button2():
        """Button 2: Quick action - Lamp warm white"""
        led.quick_lamp_white()
        save_state()

    def handle_button3():
        """Button 3: Power toggle"""
        led.power_toggle()
        save_state()

    def handle_button4():
        """Button 4: Toggle STATIC/ANIMATION mode"""
        led.toggle_main_mode()
        save_state()

    async def hardware_loop():
        """Poll hardware asynchronously"""
        while True:
            module.poll()
            await asyncio.sleep(0.01)  # non-blocking sleep

    # Autosave loop - disabled since we save after each change
    # async def autosave_loop():
    #     while True:
    #         state_manager.update_from_led(led)
    #         await state_manager.save()
    #         await asyncio.sleep(10)
             
    # Assign callbacks
    module.on_zone_selector_rotate = handle_zone_change
    module.on_zone_selector_click = handle_zone_selector_click
    module.on_modulator_rotate = handle_modulator
    module.on_modulator_click = handle_modulator_click
    module.on_button[0] = handle_button1
    module.on_button[1] = handle_button2
    module.on_button[2] = handle_button3
    module.on_button[3] = handle_button4

    # Print initial status
    status = led.get_status()
    print(f"\nInitial state:")
    print(f"  Mode: {led.main_mode.name}")
    print(f"  Edit Mode: {status['edit_mode']}")
    if led.main_mode.name == "STATIC":
        print(f"  Current Zone: {led._get_current_zone()}")
        print(f"  Parameter: {led.current_param.name}")
    else:
        print(f"  Current Animation: {led.animation_name}")
        print(f"  Parameter: {led.current_param.name}")
    print()
    print("TIP: Press BTN1 to toggle EDIT MODE")
    print("TIP: Press BTN4 to toggle STATIC/ANIMATION mode")
    print("TIP: Click upper encoder to cycle parameters in current mode")
    print("Press Ctrl+C to exit")
    print("=" * 60)
    print()

    
            
    print("Async LED Control Station running...")
    
    try:
        await hardware_loop()
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\nShutting down...")
    finally:
        # Always cleanup on exit
        print("Saving final state...")
        state_manager.update_from_led(led)
        await state_manager.save()
        print("Final state saved. Goodbye!")
        
        print("Stopping animations...")
        await led.stop_animation()  # Stop any running animation
        
        print("Stopping pulsing...")
        led._stop_pulse()  # Stop pulsing task
        await asyncio.sleep(0.1)  # Give time for colors to be restored
        
        print("Clearing all LEDs...")
        led.clear_all()
        
        print("Cleaning up GPIO...")
        module.cleanup()



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
