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

import asyncio
from control_module import ControlModule
from led_controller import LEDController
from managers.config_manager import ConfigManager
from managers.state_manager import StateManager

async def main():
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
    print("  ENCODER 1 (Zone Selector):")
    print("    Rotate: Change zone (lamp -> top -> right -> bottom -> left)")
    print("    Click:  Switch MODE (COLOR -> BRIGHTNESS -> ANIMATION -> PARAM)")
    print()
    print("  ENCODER 2 (Modulator):")
    print("    Rotate: Adjust parameter (active only in EDIT MODE)")
    print("    Click:  Switch SUB-MODE (HUE<->PRESET, or animation params)")
    print()
    print("  BUTTONS:")
    print("    BTN1: Toggle EDIT MODE (enable/disable editing)")
    print("    BTN2: Quick action - Lamp -> Warm White @ Full")
    print("    BTN3: Power toggle (all zones ON/OFF)")
    print("    BTN4: Toggle LAMP SOLO (lamp independent from animations)")
    print()
    print("Modes:")
    print("  - COLOR_SELECT: Choose color (HUE smooth / PRESET jump)")
    print("  - BRIGHTNESS_ADJUST: Adjust brightness (0-255)")
    print("  - ANIMATION_SELECT: Choose animation (TODO)")
    print("  - ANIMATION_PARAM: Adjust animation params (TODO)")
    print()
    print("Starting...")
    print("=" * 60)

    # load configuration and state
    config_manager = ConfigManager()
    config = config_manager.load()

    # Override zones in config dict with processed zones from zone_manager
    # This ensures LEDController gets {"lamp": [0,18], ...} format
    config["zones"] = config_manager.zones

    state_manager = StateManager()
    state = await state_manager.load()

    # Initialize hardware and controller
    module = ControlModule(config)
    led = LEDController(config, state)

    # Helper function to save state
    def save_state():
        """Update and save state after LED changes"""
        state_manager.update_from_led(led)
        asyncio.create_task(state_manager.save())

    # Connect hardware events to LED controller

    def handle_zone_change(delta):
        """Zone selector rotated - change zone"""
        led.change_zone(delta)
        save_state()

    def handle_zone_selector_click():
        """Zone selector button clicked - switch main mode (when edit_mode=ON)"""
        led.switch_mode()
        save_state()

    def handle_modulator(delta):
        """Modulator rotated - adjust parameter based on mode"""
        if not led.edit_mode:
            return  # Encoder 2 inactive when not in edit mode

        if led.mode.name == "COLOR_SELECT":
            if led.color_mode.name == "HUE":
                led.adjust_color(delta * 10)  # 10 degrees per click for HUE
            else:  # PRESET
                led.adjust_color(delta)  # 1 step per click for PRESET
            save_state()
        elif led.mode.name == "BRIGHTNESS_ADJUST":
            led.adjust_brightness(delta)  # 1 level per click (8 levels total)
            save_state()
        elif led.mode.name == "ANIMATION_SELECT":
            led.select_animation(delta)  # Select animation
            save_state()
        elif led.mode.name == "ANIMATION_PARAM":
            if led.anim_param_mode.name == "SPEED":
                led.adjust_animation_speed(delta * 2)  # faster change
                save_state()
            else:
                print(f"[TODO] Animation param adjust: {led.anim_param_mode}")
    
    def handle_modulator_click():
        """Modulator button clicked - switch sub-mode or start/stop animation"""
        if led.mode.name == "COLOR_SELECT":
            led.switch_color_submode()  # HUE <-> PRESET
        elif led.mode.name == "ANIMATION_SELECT":
            # Toggle animation on/off
            if led.animation_enabled:
                asyncio.create_task(led.stop_animation())
            else:
                asyncio.create_task(led.start_animation())
        elif led.mode.name == "ANIMATION_PARAM":
            led.switch_anim_param_submode()  # SPEED <-> COLOR1 <-> COLOR2 <-> INTENSITY

        save_state()

    def handle_button1():
        """Button 1: Toggle EDIT MODE"""
        led.toggle_edit_mode()
        save_state()

    def handle_button2():
        """Button 2: Quick action - Lamp warm white"""
        led.quick_lamp_white()

    def handle_button3():
        """Button 3: Power toggle"""
        led.power_toggle()

    def handle_button4():
        """Button 4: Toggle lamp solo mode"""
        led.toggle_lamp_solo()
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
    print(f"  Edit Mode: {status['edit_mode']}")
    print(f"  Mode: {status['mode']}")
    print(f"  Color Mode: {status['color_mode']}")
    print(f"  Zone: {status['zones']}")
    # print(f"  Brightness: {status['brightness']}/255")
    print(f"  Lamp Solo: {status['lamp_solo']}")
    print()
    print("TIP: Press BTN1 to enter EDIT MODE and start editing!")
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
        print("Stopping animations...")
        await led.stop_animation()  # Stop any running animation
        print("Stopping pulsing...")
        led._stop_pulse()  # Stop pulsing task
        await asyncio.sleep(0.1)  # Give time for colors to be restored
        print("Clearing all LEDs...")
        led.clear_all()
        print("Cleaning up GPIO...")
        module.cleanup()
        print("Saving final state...")
        state_manager.update_from_led(led)
        await state_manager.save()
        print("Final state saved. Goodbye!")



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
