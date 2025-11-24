"""
Hardware Layer

Zawiera wyłącznie niskopoziomową obsługę sprzętu:

- GPIO (GPIOManager)
- LED strip driver (WS281xStrip + IPhysicalStrip)
- LED hardware enums (chip types, color order)
- Inne fizyczne urządzenia, jeśli kiedyś dodamy (np. I2C, SPI)

"""
from .gpio.gpio_manager import GPIOManager
from .led.strip_interface import IPhysicalStrip
from .led.ws281x_strip import WS281xStrip, WS281xConfig
from .led.enums import LEDChipType, ColorOrder

__all__ = [
    "GPIOManager",
    "IPhysicalStrip",
    "WS281xStrip",
    "WS281xConfig",
    "LEDChipType",
    "ColorOrder",
]