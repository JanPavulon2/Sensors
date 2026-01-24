
"""
Rotary Encoder Component - Hardware Abstraction Layer (Layer 1)

Handles reading rotary encoder (CLK/DT pins) and button (SW pin).
Provides simple interface: read() returns -1/0/1, is_pressed() returns bool.

Registers all GPIO pins via GPIOManager.
"""

import time
from hardware.gpio import IGPIOManager

class RotaryEncoder:
    
    def __init__(
        self,
        clk: int,
        dt: int,
        sw: int,
        gpio_manager: IGPIOManager,
        debounce_time: float = 0.3
    ):
        self.gpio_manager = gpio_manager
        
        self.clk_pin = clk
        self.dt_pin = dt
        self.sw_pin = sw
        self.debounce_time = debounce_time

        # NOTE: GPIO registration is handled by HardwareManager
        # This component receives already-registered pins, just uses them for input reading
        # Do NOT register pins here to avoid conflicts

        # State tracking
        self._last_clk = self.gpio_manager.read(clk)
        self._last_button_state = self.gpio_manager.HIGH
        self._last_button_time = 0

    def read(self) -> int:
        """
        Read encoder rotation

        Returns:
            1: Clockwise rotation
            -1: Counter-clockwise rotation
            0: No rotation
        """
        clk_state = self.gpio_manager.read(self.clk_pin)
        dt_state = self.gpio_manager.read(self.dt_pin)

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
        current_state = self.gpio_manager.read(self.sw_pin)
        current_time = time.time()

        # Detect falling edge (button press)
        if self._last_button_state == self.gpio_manager.HIGH and current_state == self.gpio_manager.LOW:
            if (current_time - self._last_button_time) > self.debounce_time:
                self._last_button_time = current_time
                self._last_button_state = current_state
                return True

        self._last_button_state = current_state
        return False

