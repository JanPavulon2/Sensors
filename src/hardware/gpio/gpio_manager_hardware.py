"""
GPIO Manager - Infrastructure Layer Component

Centralized GPIO pin allocation and lifecycle management.
Provides conflict detection and resource tracking for all GPIO operations.

Architecture: Infrastructure Layer (Layer 1.5)
- Sits between HAL components and RPi.GPIO hardware driver
- Manages pin registry and prevents conflicts
- Centralizes GPIO.setup() and cleanup() operations
"""

from typing import Dict
from hardware.gpio import IGPIOManager
from models.enums import GPIOPullMode, GPIOInitialState
from utils.logger import get_logger, LogCategory
 
log = get_logger().for_category(LogCategory.HARDWARE)

class HardwareGPIOManager(IGPIOManager):
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
        try:
            import RPi.GPIO as GPIO
        except ImportError as e:
            raise RuntimeError("RPi.GPIO not available") from e
  
        self._gpio = GPIO
        self._registry: Dict[int, str] = {}  # pin -> component_name

        self._gpio.setmode(self._gpio.BCM)
        self._gpio.setwarnings(False)

        log.info("GPIO manager initialized (BCM mode)")

    
    # -------------------------------
    # Registration
    # -------------------------------

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
            GPIOPullMode.PULL_UP: self._gpio.PUD_UP,
            GPIOPullMode.PULL_DOWN: self._gpio.PUD_DOWN,
            GPIOPullMode.NO_PULL: self._gpio.PUD_OFF
        }[pull_mode]

        self._gpio.setup(pin, self._gpio.IN, pull_up_down=gpio_pull)
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
            GPIOInitialState.LOW: self._gpio.LOW,
            GPIOInitialState.HIGH: self._gpio.HIGH
        }[initial]

        self._gpio.setup(pin, self._gpio.OUT, initial=gpio_initial)
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
        """
        self._check_available(pin, component)

        self._registry[pin] = component

        log.info(
            f"GPIO pin registered (OUTPUT)", 
            pin=pin, 
            component=component
        )


    # -------------------------------
    # IO
    # -------------------------------

    def read(self, pin: int) -> int:
        return int(self._gpio.input(pin))

    def write(self, pin: int, value) -> None:
        self._gpio.output(pin, value)
   
   
    # -------------------------------
    # Lifecycle
    # -------------------------------
    
    def cleanup(self) -> None:
        """
        Cleanup all registered GPIO pins

        Called on application shutdown to release GPIO resources.
        """
        pin_count = len(self._registry)
        log.info(f"Cleaning up {pin_count} GPIO pins")

        self._gpio.cleanup()
        self._registry.clear()

        log.info("GPIO cleanup complete")

    def get_registry(self) -> Dict[int, str]:
        """
        Get current pin allocations (for debugging)

        Returns:
            Dict mapping pin number to component name
        """
        return self._registry.copy()

 
    def _check_available(self, pin: int, component: str) -> None:
        """
        Check if pin is available for registration

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

    
    def log_registry(self) -> None:
        """Log all registered pins (useful for startup debugging)"""
        if not self._registry:
            log.info("GPIO registry is empty")
            return

        log.info(f"GPIO registry ({len(self._registry)} pins):")
        for pin, component in sorted(self._registry.items()):
            log.info(f"  GPIO {pin:2d} → {component}")