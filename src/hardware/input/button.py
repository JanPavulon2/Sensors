"""
Button Component - Hardware Abstraction Layer (Layer 1)

Simple button with debouncing.
"""

import time
from hardware.gpio import IGPIOManager

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

    def __init__(
            self, 
            pin: int, 
            gpio_manager: IGPIOManager,
            debounce_time: float = 0.3
    ):
        self.pin = pin
        self.gpio_manager = gpio_manager
        self.debounce_time = debounce_time

        # State tracking
        self._last_state = gpio_manager.read(pin)
        self._last_press_time = 0.0
        
        self.HIGH = 1
        self.LOW = 0

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    def is_pressed(self) -> bool:
        """
        Check if button was pressed (with debouncing)

        Returns:
            True once per physical press (after debounce)
        """
        current_state = self.gpio_manager.read(self.pin)
        now = time.time()

        pressed = False
        
        # FALLING EDGE: HIGH → LOW
        if self._last_state == self.HIGH and current_state == self.LOW:
            if (now - self._last_press_time) >= self.debounce_time:
                pressed = True
                self._last_press_time = now

        # Update state AFTER detection
        self._last_state = current_state
        return pressed


    # ---------------------------------------------------------------
    # Utilities 
    # ---------------------------------------------------------------

    def reset(self) -> None:
        """Reset internal state (useful for tests or device reconnect)."""
        self._last_state = self.gpio_manager.read(self.pin)
        self._last_press_time = 0.0

    def is_held(self) -> bool:
        """
        Return True if the button is currently physically held down.
        Does NOT include debouncing, purely raw state.
        """
        return self.gpio_manager.read(self.pin) == self.LOW

    def __repr__(self) -> str:
        return f"<Button pin={self.pin}>"





