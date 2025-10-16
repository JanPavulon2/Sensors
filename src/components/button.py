"""
Button Component

Simple button with debouncing.
"""

import RPi.GPIO as GPIO
import time


class Button:
    """
    Single button with debouncing

    Args:
        pin: GPIO pin number
        debounce_time: Debounce time (seconds)

    Example:
        btn = Button(pin=24)

        while True:
            if btn.is_pressed():
                print("Button pressed!")
    """

    def __init__(self, pin, debounce_time=0.3):
        self.pin = pin
        self.debounce_time = debounce_time

        # Setup GPIO
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # State tracking
        self._last_state = GPIO.HIGH
        self._last_press_time = 0

    def is_pressed(self):
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
