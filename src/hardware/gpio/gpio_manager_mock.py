from typing import Dict
from hardware.gpio import IGPIOManager
from models.enums import GPIOPullMode, GPIOInitialState
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.HARDWARE)

class MockGPIOManager(IGPIOManager):

    def __init__(self):
        self._registry: Dict[int, str] = {}  # pin -> component_name
        self._values: Dict[int, int] = {}
        log.info("Mock GPIO manager initialized")

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
        self._registry[pin] = component
        self._values[pin] = 1
        
    def register_output(
        self,
        pin: int,
        component: str,
        initial: GPIOInitialState = GPIOInitialState.LOW
    ) -> None:
        self._check_available(pin, component)
        self._registry[pin] = component
        self._values[pin] = int(initial == GPIOInitialState.HIGH)

    def register_ws281x(self, pin: int, component: str) -> None:
        self._check_available(pin, component)
        self._registry[pin] = component

    
    # -------------------------------
    # IO
    # -------------------------------
    
    def read(self, pin: int) -> int:
        return self._values.get(pin, 0)

    def write(self, pin: int, value: int) -> None:
        self._values[pin] = int(value)

    # -------------------------------
    # Lifecycle
    # -------------------------------

    def cleanup(self) -> None:
        self._registry.clear()
        self._values.clear()
        log.info(f"Mock GPIO Manager cleanup finished ({len(self._registry)} pins)")
        

    def get_registry(self) -> Dict[int, str]:
        return self._registry.copy()
    
    
    # -------------------------------
    # Internals
    # -------------------------------

    def _check_available(self, pin: int, component: str) -> None:
        if pin in self._registry:
            raise ValueError(
                f"GPIO {pin} already registered by {self._registry[pin]}"
            )
            