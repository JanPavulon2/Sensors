from __future__ import annotations

from hardware.hardware_coordinator import HardwareBundle
from controllers.led_controller.lighting_controller import LightingController
from hardware.gpio.gpio_manager import GPIOManager
from lifecycle.shutdown_protocol import IShutdownHandler
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SHUTDOWN)


from typing import Protocol, List
from models.color import Color

class LEDShutdownHandler(IShutdownHandler):
    """
    Shutdown handler for LED hardware.

    Clears all LEDs to prevent them from being left on.
    Runs AFTER animation engine stops to prevent race conditions
    where FrameManager continues submitting frames after clearing.

    Priority: 100 (runs second, after animations stop)
    """

    def __init__(self, hardware: HardwareBundle):
        """
        Initialize LED shutdown handler.

        Args:
            hardware: HardwareBundle containing zone strips
        """
        self.hardware = hardware

    @property
    def shutdown_priority(self) -> int:
        """LED clearing runs after animation stops."""
        return 100

    async def shutdown(self) -> None:
        """Clear all LEDs on all GPIO strips."""
        log.info("Clearing LEDs on all GPIO strips...")

        try:
            # Clear all zone strips (there may be multiple GPIO pins)
            for gpio_pin, strip in self.hardware.zone_strips.items():
                try:
                    strip.clear()
                    log.debug(f"Cleared GPIO {gpio_pin}")
                except Exception as e:
                    log.error(f"Error clearing GPIO {gpio_pin}: {e}")

            log.info("All LEDs cleared")

        except Exception as e:
            log.error(f"Error during LED clearing: {e}", exc_info=True)
            raise

