from typing import Protocol, Dict
from models.enums import GPIOPullMode, GPIOInitialState

class IGPIOManager(Protocol):
    
    # -------------------------------
    # Registration
    # -------------------------------
    
    def register_input(
        self,
        pin: int,
        component: str,
        pull_mode: GPIOPullMode = GPIOPullMode.PULL_UP
    ) -> None:
        ...

    def register_output(
        self,
        pin: int,
        component: str,
        initial: GPIOInitialState = GPIOInitialState.LOW
    ) -> None:
        ...

    def register_ws281x(self, pin: int, component: str) -> None:
        ...


    # -------------------------------
    # IO
    # -------------------------------

    def read(self, pin: int) -> int:
        """Read GPIO pin value (0 or 1)"""
        ...

    def write(self, pin: int, value: int) -> None:
        """Write value to GPIO pin (0 or 1)"""
        ...
        
        
    # -------------------------------
    # Lifecycle / Debug
    # -------------------------------

    def cleanup(self) -> None:
        ...

    def get_registry(self) -> Dict[int, str]:
        ...
        