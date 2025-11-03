
"""
Rotary Encoder Component - Hardware Abstraction Layer (Layer 1)

Handles reading rotary encoder (CLK/DT pins) and button (SW pin).
Provides simple interface: read() returns -1/0/1, is_pressed() returns bool.

Registers all GPIO pins via GPIOManager.
"""

import RPi.GPIO as GPIO
import time
from managers.GPIOManager import GPIOManager
from models.enums import GPIOPullMode


class RotaryEncoder:
    """
    Rotary encoder with built-in button

    Args:
        clk: CLK pin (BCM GPIO number)
        dt: DT pin (BCM GPIO number)
        sw: SW pin (BCM GPIO number) - button
        gpio_manager: GPIOManager instance for pin registration
        debounce_time: Debounce time for button (seconds, default 0.3s)

    Example:
        gpio_manager = GPIOManager()
        encoder = RotaryEncoder(clk=5, dt=6, sw=13, gpio_manager=gpio_manager)

        while True:
            delta = encoder.read()
            if delta != 0:
                print(f"Rotated: {delta}")

            if encoder.is_pressed():
                print("Button pressed!")
    """

    def __init__(
        self,
        clk: int,
        dt: int,
        sw: int,
        gpio_manager: GPIOManager,
        debounce_time: float = 0.3
    ):
        self.clk_pin = clk
        self.dt_pin = dt
        self.sw_pin = sw
        self.debounce_time = debounce_time

        # Register GPIO pins via manager (pull-up for all encoder pins)
        gpio_manager.register_input(
            pin=clk,
            component=f"RotaryEncoder({clk},{dt},{sw}).CLK",
            pull_mode=GPIOPullMode.PULL_UP
        )
        gpio_manager.register_input(
            pin=dt,
            component=f"RotaryEncoder({clk},{dt},{sw}).DT",
            pull_mode=GPIOPullMode.PULL_UP
        )
        gpio_manager.register_input(
            pin=sw,
            component=f"RotaryEncoder({clk},{dt},{sw}).SW",
            pull_mode=GPIOPullMode.PULL_UP
        )

        # State tracking
        self._last_clk = GPIO.input(clk)
        self._last_button_state = GPIO.HIGH
        self._last_button_time = 0

    def read(self) -> int:
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

    def is_pressed(self) -> bool:
        """
        Check if button is pressed (with debouncing)

        Returns:
            True if button was pressed (falling edge with debounce)
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

