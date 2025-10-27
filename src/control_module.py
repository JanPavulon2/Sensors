"""
Control Module - Hardware abstraction layer

Provides event-driven interface for hardware input polling.
"""

import RPi.GPIO as GPIO
from components import RotaryEncoder, Button
from managers.hardware_manager import HardwareManager


class ControlModule:
    """
    Hardware control module for LED station

    Components:
        - Selector (Encoder): Selects items (zones in STATIC mode, animations in ANIMATION mode)
        - Modulator (Encoder): Modulates parameter values (color, brightness, speed, intensity)
        - 4x Buttons: Mode toggles and special functions

    Callbacks (assign functions to these):
        - on_selector_rotate(delta): Called when selector encoder rotates
        - on_selector_click(): Called when selector encoder button pressed
        - on_modulator_rotate(delta): Called when modulator encoder rotates
        - on_modulator_click(): Called when modulator encoder button pressed
        - on_button: List of 4 button callbacks
    """

    def __init__(self, hardware_manager: HardwareManager):
        """
        Initialize ControlModule with HardwareManager

        Args:
            hardware_manager: HardwareManager instance providing hardware configuration
        """
        self.hardware_manager = hardware_manager

        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Selector (Encoder) - selects items (zones/animations)
        # Config key is still "zone_selector" for backward compatibility
        selector_cfg = hardware_manager.get_encoder("zone_selector")
        self.selector = RotaryEncoder(
            clk=selector_cfg["clk"], # type: ignore
            dt=selector_cfg["dt"], # type: ignore
            sw=selector_cfg["sw"] # type: ignore
        )

        # Modulator (Encoder) - modulates parameter values
        modulator_cfg = hardware_manager.get_encoder("modulator")
        self.modulator = RotaryEncoder(
            clk=modulator_cfg["clk"], # type: ignore
            dt=modulator_cfg["dt"], # type: ignore
            sw=modulator_cfg["sw"] # type: ignore
        )

        # Buttons - from HardwareManager
        button_pins = hardware_manager.button_pins
        self.buttons = [Button(pin) for pin in button_pins]

        # Event callbacks (user assigns these)
        self.on_selector_rotate = None
        self.on_selector_click = None
        self.on_modulator_rotate = None
        self.on_modulator_click = None
        self.on_button = [None, None, None, None]

    def poll(self):
        """
        Poll all hardware inputs and call callbacks

        Call this in your main loop to handle all hardware events.
        """
        # Selector rotation
        delta = self.selector.read()
        if delta != 0 and self.on_selector_rotate:
            self.on_selector_rotate(delta)

        # Selector button
        if self.selector.is_pressed() and self.on_selector_click:
            self.on_selector_click()

        # Modulator rotation
        delta = self.modulator.read()
        if delta != 0 and self.on_modulator_rotate:
            self.on_modulator_rotate(delta)

        # Modulator button
        if self.modulator.is_pressed() and self.on_modulator_click:
            self.on_modulator_click()

        # Buttons
        for i, btn in enumerate(self.buttons):
            if btn.is_pressed() and self.on_button[i]:
                self.on_button[i]() # type: ignore

    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup()




