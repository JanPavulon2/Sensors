# factory.py

from typing import Optional
from runtime.runtime_info import RuntimeInfo
from hardware.led.strip_interface import IPhysicalStrip
from hardware.led.virtual_strip import VirtualStrip



def create_strip(
    *,
    pixel_count: int,
    gpio_pin: Optional[int],
    color_order: str = "BGR",
) -> IPhysicalStrip:
    """
    Factory that NEVER crashes the app on PC / WSL.
    """

    if RuntimeInfo.is_raspberry_pi() and RuntimeInfo.has_ws281x():
        try:
            from hardware.led.ws281x_strip import WS281xStrip
            assert gpio_pin is not None
            
            return WS281xStrip(
                pixel_count=pixel_count,
                gpio_pin=gpio_pin,
                color_order=color_order
            )
        except Exception:
            pass
        
    return VirtualStrip(pixel_count)
