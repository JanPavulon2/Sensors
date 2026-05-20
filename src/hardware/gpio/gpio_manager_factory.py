from hardware.gpio.gpio_manager_interface import IGPIOManager
from runtime.runtime_info import RuntimeInfo
 
 
def create_gpio_manager() -> 'IGPIOManager':
    """
    Select GPIO backend based on available hardware and libraries:
      - RPi 1–4 + RPi.GPIO installed  → HardwareGPIOManager
      - RPi 5   + lgpio installed      → HardwareLGPIOManager
      - anything else                  → MockGPIOManager
    """
    rt = RuntimeInfo()
 
    if rt.is_raspberry_pi():
        if rt.has_lgpio():
            from hardware.gpio.gpio_manager_lgpio import HardwareLGPIOManager
            return HardwareLGPIOManager()
        elif rt.has_gpio():
            from hardware.gpio.gpio_manager_hardware import HardwareGPIOManager
            return HardwareGPIOManager()
        
    from hardware.gpio.gpio_manager_mock import MockGPIOManager
    return MockGPIOManager()
 
