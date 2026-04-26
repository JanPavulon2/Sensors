from __future__ import annotations

from hardware.hardware_coordinator import HardwareBundle
from controllers.led_controller.lighting_controller import LightingController
from hardware.gpio import IGPIOManager
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
            hardware: HardwareBundle containing led channels
        """
        self.hardware = hardware

    @property
    def shutdown_priority(self) -> int:
        """LED clearing runs after animation stops."""
        return 100

    async def shutdown(self) -> None:
        """Clear all LEDs on all led channels."""
        log.info("Clearing LEDs on all channels...")

        try:
            # Clear all leds on all channels (there may be multiple GPIO pins)
            for gpio_pin, led_channel in self.hardware.led_channels.items():
                try:
                    led_channel.clear()
                    log.debug(f"Cleared GPIO {gpio_pin}")
                except Exception as e:
                    log.error(f"Error clearing led channel on GPIO: {gpio_pin}: {e}")

            log.info("All LED channels cleared")

        except Exception as e:
            log.error(f"Error during LED channel: {e}", exc_info=True)
            raise

