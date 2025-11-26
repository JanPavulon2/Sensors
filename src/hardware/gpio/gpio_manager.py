"""
GPIO Manager - Infrastructure Layer Component

Centralized GPIO pin allocation and lifecycle management.
Provides conflict detection and resource tracking for all GPIO operations.

Architecture: Infrastructure Layer (Layer 1.5)
- Sits between HAL components and RPi.GPIO hardware driver
- Manages pin registry and prevents conflicts
- Centralizes GPIO.setup() and cleanup() operations
"""

import RPi.GPIO as GPIO
from typing import Dict
from models.enums import GPIOPullMode, GPIOInitialState
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.HARDWARE)

class GPIOManager:
    """
    Infrastructure component managing GPIO pin allocation and lifecycle.

    Responsibilities:
    - Initialize RPi.GPIO library (BCM mode, disable warnings)
    - Track registered pins (prevent conflicts)
    - Provide pin registration API for HAL components
    - Clean up all registered pins on shutdown

    Layer: Infrastructure (Layer 1.5)
    """

    def __init__(self):
        """Initialize GPIO library and empty pin registry"""
        self._registry: Dict[int, str] = {}  # pin -> component_name

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        log.info("GPIO manager initialized (BCM mode)")

    def register_input(
        self,
        pin: int,
        component: str,
        pull_mode: GPIOPullMode = GPIOPullMode.PULL_UP
    ) -> None:
        """
        Register and setup input pin (buttons, encoder switches)

        Args:
            pin: BCM GPIO pin number
            component: Component name for tracking (e.g., "Button(22)")
            pull_mode: Pull resistor configuration (default: PULL_UP)

        Raises:
            ValueError: If pin already registered by another component
        """
        self._check_available(pin, component)

        # Map our enum to RPi.GPIO constants
        gpio_pull = {
            GPIOPullMode.PULL_UP: GPIO.PUD_UP,
            GPIOPullMode.PULL_DOWN: GPIO.PUD_DOWN,
            GPIOPullMode.NO_PULL: GPIO.PUD_OFF
        }[pull_mode]

        GPIO.setup(pin, GPIO.IN, pull_up_down=gpio_pull)
        self._registry[pin] = component

        log.info(
            f"GPIO pin registered (INPUT)",
            pin=pin,
            component=component,
            pull=pull_mode.name
        )

    def register_output(
        self,
        pin: int,
        component: str,
        initial: GPIOInitialState = GPIOInitialState.LOW
    ) -> None:
        """
        Register and setup output pin (generic digital outputs)

        Args:
            pin: BCM GPIO pin number
            component: Component name for tracking
            initial: Initial state (default: LOW)

        Raises:
            ValueError: If pin already registered by another component
        """
        self._check_available(pin, component)

        # Map our enum to RPi.GPIO constants
        gpio_initial = {
            GPIOInitialState.LOW: GPIO.LOW,
            GPIOInitialState.HIGH: GPIO.HIGH
        }[initial]

        GPIO.setup(pin, GPIO.OUT, initial=gpio_initial)
        self._registry[pin] = component

        log.info(
            f"GPIO pin registered (OUTPUT)",
            pin=pin,
            component=component,
            initial=initial.name
        )

    def register_ws281x(self, pin: int, component: str) -> None:
        """
        Register WS281x pin (DMA-based, no GPIO.setup needed)

        WS281x LEDs use DMA and are initialized by rpi_ws281x library.
        We only track the pin allocation here for conflict detection.

        Args:
            pin: BCM GPIO pin number (must be PWM-capable: 10, 12, 18, 21)
            component: Component name for tracking (e.g., "ZoneStrip(18)")

        Raises:
            ValueError: If pin already registered by another component
        """
        self._check_available(pin, component)

        self._registry[pin] = component

        log.info(
            f"GPIO pin registered (OUTPUT)", 
            pin=pin, 
            component=component
        )

    def _check_available(self, pin: int, component: str) -> None:
        """
        Check if pin is available for registration

        Args:
            pin: GPIO pin to check
            component: Component requesting the pin

        Raises:
            ValueError: If pin already registered
        """
        if pin in self._registry:
            existing_owner = self._registry[pin]
            error_msg = (
                f"GPIO pin conflict detected: Pin {pin} requested by '{component}' "
                f"is already registered to '{existing_owner}'"
            )
            log.error(error_msg)
            raise ValueError(error_msg)

    def cleanup(self) -> None:
        """
        Cleanup all registered GPIO pins

        Called on application shutdown to release GPIO resources.
        """
        pin_count = len(self._registry)
        log.info(f"Cleaning up {pin_count} GPIO pins")

        GPIO.cleanup()
        self._registry.clear()

        log.info("GPIO cleanup complete")

    def get_registry(self) -> Dict[int, str]:
        """
        Get current pin allocations (for debugging)

        Returns:
            Dict mapping pin number to component name
        """
        return self._registry.copy()

    def log_registry(self) -> None:
        """Log all registered pins (useful for startup debugging)"""
        if not self._registry:
            log.info("GPIO registry is empty")
            return

        log.info(f"GPIO registry ({len(self._registry)} pins):")
        for pin, component in sorted(self._registry.items()):
            log.info(f"  GPIO {pin:2d} → {component}")