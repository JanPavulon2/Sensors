#!/usr/bin/env python3
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
from config_manager import ConfigManager
from control_module import ControlModule
from led_controller import LEDController

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

    # Load config (with auto-save every 10 seconds)
    config = ConfigManager(auto_save_interval=10)

    # Initialize hardware and controller with config
    module = ControlModule(config)
    led = LEDController(config)

    # Connect hardware events to LED controller

    def handle_zone_change(delta):
        """Zone selector rotated - change zone"""
        led.change_zone(delta)

    def handle_zone_selector_click():
        """Zone selector button clicked - switch main mode (when edit_mode=ON)"""
        led.switch_mode()

    def handle_modulator(delta):
        """Modulator rotated - adjust parameter based on mode"""
        if not led.edit_mode:
            return  # Encoder 2 inactive when not in edit mode

        if led.mode.name == "COLOR_SELECT":
            if led.color_mode.name == "HUE":
                led.adjust_color(delta * 10)  # 10 degrees per click for HUE
            else:  # PRESET
                led.adjust_color(delta)  # 1 step per click for PRESET
        elif led.mode.name == "BRIGHTNESS_ADJUST":
            led.adjust_brightness(delta)  # 1 level per click (8 levels total)
        elif led.mode.name == "ANIMATION_SELECT":
            # TODO: Implement animation selection
            print(f"[TODO] Animation select: delta={delta}")
        elif led.mode.name == "ANIMATION_PARAM":
            # TODO: Implement animation parameter adjustment
            print(f"[TODO] Animation param adjust: delta={delta}")

    def handle_modulator_click():
        """Modulator button clicked - switch sub-mode"""
        if led.mode.name == "COLOR_SELECT":
            led.switch_color_submode()  # HUE <-> PRESET
        elif led.mode.name == "ANIMATION_PARAM":
            led.switch_anim_param_submode()  # SPEED <-> COLOR1 <-> COLOR2 <-> INTENSITY

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
        """Button 4: Toggle lamp solo mode"""
        led.toggle_lamp_solo()

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
    print(f"  Zone: {status['zone']}")
    print(f"  Brightness: {status['brightness']}/255")
    print(f"  Lamp Solo: {status['lamp_solo']}")
    print()
    print("TIP: Press BTN1 to enter EDIT MODE and start editing!")
    print("Press Ctrl+C to exit")
    print("=" * 60)
    print()

    # Start async tasks
    config.start_auto_save_task()  # Start config auto-save

    # Start pulsing if edit mode is ON
    if led.edit_mode:
        led.start_pulse_task()

    # Main polling loop
    try:
        while True:
            module.poll()  # Check hardware and call callbacks

            # Handle pulse task start/stop based on edit_mode changes
            if led.edit_mode and led.pulse_task is None:
                led.start_pulse_task()
            elif not led.edit_mode and led.pulse_task is not None:
                await led.stop_pulse_task()

            await asyncio.sleep(0.01)  # 10ms polling interval

    except (KeyboardInterrupt, asyncio.CancelledError):
        pass  # Normal shutdown
    finally:
        print("\n\nShutting down...")
        await led.clear_all()
        module.cleanup()
        await config.cleanup()  # Save state and stop auto-save
        print("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
