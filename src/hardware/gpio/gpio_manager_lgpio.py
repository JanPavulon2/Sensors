"""
GPIO Manager - lgpio Implementation (RPi 5)
 
Drop-in replacement for HardwareGPIOManager on Raspberry Pi 5,
which uses the RP1 chip incompatible with RPi.GPIO.
 
Uses lgpio library via /dev/gpiochip0.
 
Architecture: Infrastructure Layer (Layer 1.5)
"""
 
from typing import Dict
from hardware.gpio import IGPIOManager
from models.enums import GPIOPullMode, GPIOInitialState
from utils.logger import get_logger, LogCategory
 
log = get_logger().for_category(LogCategory.HARDWARE)
 
 
class HardwareLGPIOManager(IGPIOManager):
    """
    Infrastructure component managing GPIO pin allocation via lgpio.
 
    Implements identical interface to HardwareGPIOManager.
    Targets RPi 5 (RP1 GPIO chip) where RPi.GPIO is not supported.
 
    Layer: Infrastructure (Layer 1.5)
    """
 
    def __init__(self, gpiochip: int = 0):
        try:
            import lgpio
        except ImportError as e:
            raise RuntimeError("lgpio not available — install with: sudo apt install swig libgpiod-dev && pip install lgpio") from e
 
        self._lgpio = lgpio
        self._handle = lgpio.gpiochip_open(gpiochip)
        self._registry: Dict[int, str] = {}
 
        log.info(f"LGPIO manager initialized (chip {gpiochip})")
 
    # -------------------------------
    # GPIO Constants
    # -------------------------------
 
    @property
    def HIGH(self) -> int:
        return 1
 
    @property
    def LOW(self) -> int:
        return 0
 
    # -------------------------------
    # Registration
    # -------------------------------
 
    def register_input(
        self,
        pin: int,
        component: str,
        pull_mode: GPIOPullMode = GPIOPullMode.PULL_UP
    ) -> None:
        self._check_available(pin, component)
 
        pull_flag = {
            GPIOPullMode.PULL_UP:   self._lgpio.SET_PULL_UP,
            GPIOPullMode.PULL_DOWN: self._lgpio.SET_PULL_DOWN,
            GPIOPullMode.NO_PULL:   self._lgpio.SET_PULL_NONE,
        }[pull_mode]
 
        self._lgpio.gpio_claim_input(self._handle, pin, pull_flag)
        self._registry[pin] = component
 
        log.info(
            "GPIO pin registered (INPUT)",
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
        self._check_available(pin, component)
 
        level = 1 if initial == GPIOInitialState.HIGH else 0
        self._lgpio.gpio_claim_output(self._handle, pin, level)
        self._registry[pin] = component
 
        log.info(
            "GPIO pin registered (OUTPUT)",
            pin=pin,
            component=component,
            initial=initial.name
        )
 
    def register_ws281x(self, pin: int, component: str) -> None:
        # DMA-based, lgpio nie setup-uje pinu — tylko rejestrujemy konflikt
        self._check_available(pin, component)
        self._registry[pin] = component
 
        log.info(
            "GPIO pin registered (WS281x/DMA)",
            pin=pin,
            component=component
        )
 
    # -------------------------------
    # IO
    # -------------------------------
 
    def read(self, pin: int) -> int:
        return self._lgpio.gpio_read(self._handle, pin)
 
    def write(self, pin: int, value) -> None:
        self._lgpio.gpio_write(self._handle, pin, int(value))
 
    # -------------------------------
    # Lifecycle
    # -------------------------------
 
    def cleanup(self) -> None:
        pin_count = len(self._registry)
        log.info(f"Cleaning up {pin_count} GPIO pins (lgpio)")
 
        for pin in list(self._registry.keys()):
            try:
                self._lgpio.gpio_free(self._handle, pin)
            except Exception:
                pass
 
        self._lgpio.gpiochip_close(self._handle)
        self._registry.clear()
 
        log.info("LGPIO cleanup complete")
 
    def get_registry(self) -> Dict[int, str]:
        return self._registry.copy()
 
    # -------------------------------
    # Internals
    # -------------------------------
 
    def _check_available(self, pin: int, component: str) -> None:
        if pin in self._registry:
            existing_owner = self._registry[pin]
            error_msg = (
                f"GPIO pin conflict detected: Pin {pin} requested by '{component}' "
                f"is already registered to '{existing_owner}'"
            )
            log.error(error_msg)
            raise ValueError(error_msg)
 
    def log_registry(self) -> None:
        if not self._registry:
            log.info("GPIO registry is empty")
            return
 
        log.info(f"GPIO registry ({len(self._registry)} pins):")
        for pin, component in sorted(self._registry.items()):
            log.info(f"  GPIO {pin:2d} → {component}")
 
