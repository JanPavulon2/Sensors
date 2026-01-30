# factory.py
from runtime.runtime_info import RuntimeInfo
from hardware.gpio.gpio_manager_interface import IGPIOManager
from hardware.gpio.gpio_manager_hardware import HardwareGPIOManager
from hardware.gpio.gpio_manager_mock import MockGPIOManager

def create_gpio_manager() -> 'IGPIOManager':
    rt = RuntimeInfo()
    
    if rt.has_gpio():
        return HardwareGPIOManager()
    else:
        return MockGPIOManager()