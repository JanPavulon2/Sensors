"""
Button Component - Hardware Abstraction Layer (Layer 1)

Simple button with debouncing.
"""

import RPi.GPIO as GPIO
import time

class Button:
    """
    Single button with debouncing

    Args:
        pin: BCM GPIO pin number
        debounce_time: Debounce time (seconds, default 0.3s)

    Example:
        btn = Button(pin=24)

        while True:
            if btn.is_pressed():
                print("Button pressed!")
    """

    def __init__(self, pin: int, debounce_time: float = 0.3):
        self.pin = pin
        self.debounce_time = debounce_time

        # State tracking
        initial = GPIO.input(self.pin)
        self._last_state = initial
        self._last_press_time = 0

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    def is_pressed(self) -> bool:
        """
        Check if button was pressed (with debouncing)

        Returns:
            True once per physical press (after debounce)
        """
        current_state = GPIO.input(self.pin)
        current_time = time.time()

        pressed = False

        # FALLING EDGE: HIGH → LOW
        if self._last_state == GPIO.HIGH and current_state == GPIO.LOW:
            if (current_time - self._last_press_time) >= self.debounce_time:
                pressed = True
                self._last_press_time = current_time

        # Update state AFTER detection
        self._last_state = current_state
        return pressed


    # ---------------------------------------------------------------
    # Utilities 
    # ---------------------------------------------------------------

    def reset(self) -> None:
        """Reset internal state (useful for tests or device reconnect)."""
        self._last_state = GPIO.input(self.pin)
        self._last_press_time = 0.0

    def is_held(self) -> bool:
        """
        Return True if the button is currently physically held down.
        Does NOT include debouncing, purely raw state.
        """
        return GPIO.input(self.pin) == GPIO.LOW

    def __repr__(self) -> str:
        return f"<Button pin={self.pin} debounce={self.debounce_time}s>"





