"""
Button Component - Hardware Abstraction Layer (Layer 1)

Simple button with debouncing. Registers GPIO pins via GPIOManager.
"""

import RPi.GPIO as GPIO
import time
from hardware.gpio.gpio_manager import GPIOManager
from models.enums import GPIOPullMode


class Button:
    """
    Single button with debouncing

    Args:
        pin: BCM GPIO pin number
        gpio_manager: GPIOManager instance for pin registration
        debounce_time: Debounce time (seconds, default 0.3s)

    Example:
        gpio_manager = GPIOManager()
        btn = Button(pin=24, gpio_manager=gpio_manager)

        while True:
            if btn.is_pressed():
                print("Button pressed!")
    """

    def __init__(self, pin: int, debounce_time: float = 0.3):
        self.pin = pin
        self.debounce_time = debounce_time

        # NOTE: GPIO registration is handled by HardwareManager
        # This component receives already-registered pins, just uses them for input reading
        # Do NOT register pins here to avoid conflicts

        # State tracking
        self._last_state = GPIO.HIGH
        self._last_press_time = 0

    def is_pressed(self) -> bool:
        """
        Check if button was pressed (with debouncing)

        Returns:
            True if button was pressed (falling edge with debounce)
            False otherwise
        """
        current_state = GPIO.input(self.pin)
        current_time = time.time()

        # Detect falling edge (button press)
        if self._last_state == GPIO.HIGH and current_state == GPIO.LOW:
            if (current_time - self._last_press_time) > self.debounce_time:
                self._last_press_time = current_time
                self._last_state = current_state
                return True

        self._last_state = current_state
        return False




