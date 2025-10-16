
"""
Rotary Encoder Component

Handles reading rotary encoder (CLK/DT pins) and button (SW pin).
Provides simple interface: read() returns -1/0/1, is_pressed() returns bool.
"""

import RPi.GPIO as GPIO
import time


class RotaryEncoder:
    """
    Rotary encoder with built-in button

    Args:
        clk: CLK pin (GPIO number)
        dt: DT pin (GPIO number)
        sw: SW pin (GPIO number) - button
        debounce_time: Debounce time for button (seconds)

    Example:
        encoder = RotaryEncoder(clk=5, dt=6, sw=13)

        while True:
            delta = encoder.read()
            if delta != 0:
                print(f"Rotated: {delta}")

            if encoder.is_pressed():
                print("Button pressed!")
    """

    def __init__(self, clk, dt, sw, debounce_time=0.3):
        self.clk_pin = clk
        self.dt_pin = dt
        self.sw_pin = sw
        self.debounce_time = debounce_time

        # Setup GPIO
        GPIO.setup(clk, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(dt, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(sw, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # State tracking
        self._last_clk = GPIO.input(clk)
        self._last_button_state = GPIO.HIGH
        self._last_button_time = 0

    def read(self):
        """
        Read encoder rotation

        Returns:
            1: Clockwise rotation
            -1: Counter-clockwise rotation
            0: No rotation
        """
        clk_state = GPIO.input(self.clk_pin)
        dt_state = GPIO.input(self.dt_pin)

        if clk_state != self._last_clk:
            self._last_clk = clk_state
            if dt_state != clk_state:
                return 1  # Clockwise
            else:
                return -1  # Counter-clockwise

        return 0

    def is_pressed(self):
        """
        Check if button is pressed (with debouncing)

        Returns:
            True if button was pressed (rising edge with debounce)
            False otherwise
        """
        current_state = GPIO.input(self.sw_pin)
        current_time = time.time()

        # Detect falling edge (button press)
        if self._last_button_state == GPIO.HIGH and current_state == GPIO.LOW:
            if (current_time - self._last_button_time) > self.debounce_time:
                self._last_button_time = current_time
                self._last_button_state = current_state
                return True

        self._last_button_state = current_state
        return False

