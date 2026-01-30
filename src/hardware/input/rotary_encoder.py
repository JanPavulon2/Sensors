
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

        # State tracking for rotation
        self._last_clk = self.gpio_manager.read(clk)

        # State tracking for button press
        self._last_state = self.gpio_manager.read(sw)
        self._last_press_time = 0.0

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
        Check if button was pressed (with debouncing)

        Returns:
            True once per physical press (after debounce)
        """
        current_state = self.gpio_manager.read(self.sw_pin)
        now = time.time()

        pressed = False

        # FALLING EDGE: HIGH → LOW
        if self._last_state == self.gpio_manager.HIGH and current_state == self.gpio_manager.LOW:
            if (now - self._last_press_time) >= self.debounce_time:
                pressed = True
                self._last_press_time = now

        # Update state AFTER detection
        self._last_state = current_state
        return pressed
