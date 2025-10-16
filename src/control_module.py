"""
Control Module - Hardware abstraction layer

Provides event-driven interface for hardware:
- 2x Rotary Encoders (zone_selector, modulator)
- 4x Buttons

Usage:
    module = ControlModule()

    # Assign callbacks
    module.on_zone_selector_rotate = lambda delta: print(f"Zone: {delta}")
    module.on_modulator_rotate = lambda delta: print(f"Color: {delta}")
    module.on_button[0] = lambda: print("Button 1!")

    # Poll in main loop
    while True:
        module.poll()
        time.sleep(0.01)
"""

import RPi.GPIO as GPIO
import asyncio
from components import RotaryEncoder, Button


class ControlModule:
    """
    Hardware control module for LED station

    Components:
        - Zone Selector (Encoder 1): Selects which zone to edit
        - Modulator (Encoder 2): Modulates parameters (color, brightness, speed)
        - 4x Buttons: Currently unassigned (will be moved when available)

    Callbacks (assign functions to these):
        - on_zone_selector_rotate(delta): Called when zone selector rotates
        - on_zone_selector_click(): Called when zone selector button pressed
        - on_modulator_rotate(delta): Called when modulator rotates
        - on_modulator_click(): Called when modulator button pressed
        - on_button: List of 4 button callbacks (currently disabled - buttons unplugged)
    """

    def __init__(self, config):
        self.config = config
        print(config)

        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Zone Selector (Encoder 1) - from config
        zone_cfg = config["hardware"]["encoders"]["zone_selector"]
        self.zone_selector = RotaryEncoder(
            clk=zone_cfg["clk"],
            dt=zone_cfg["dt"],
            sw=zone_cfg["sw"]
        )

        # Modulator (Encoder 2) - from config
        mod_cfg = config["hardware"]["encoders"]["modulator"]
        self.modulator = RotaryEncoder(
            clk=mod_cfg["clk"],
            dt=mod_cfg["dt"],
            sw=mod_cfg["sw"]
        )

        # Buttons - from config
        button_pins = config["hardware"]["buttons"]
        self.buttons = [Button(pin) for pin in button_pins]

        # Event callbacks (user assigns these)
        self.on_zone_selector_rotate = None
        self.on_zone_selector_click = None
        self.on_modulator_rotate = None
        self.on_modulator_click = None
        self.on_button = [None, None, None, None]

    def poll(self):
        """
        Poll all hardware inputs and call callbacks

        Call this in your main loop to handle all hardware events.
        """
        # Zone Selector rotation
        delta = self.zone_selector.read()
        if delta != 0 and self.on_zone_selector_rotate:
            self.on_zone_selector_rotate(delta)

        # Zone Selector button
        if self.zone_selector.is_pressed() and self.on_zone_selector_click:
            self.on_zone_selector_click()

        # Modulator rotation
        delta = self.modulator.read()
        if delta != 0 and self.on_modulator_rotate:
            self.on_modulator_rotate(delta)

        # Modulator button
        if self.modulator.is_pressed() and self.on_modulator_click:
            self.on_modulator_click()

        # Buttons (disabled for now)
        for i, btn in enumerate(self.buttons):
            if btn.is_pressed() and self.on_button[i]:
                self.on_button[i]()

    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup()




