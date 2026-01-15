from __future__ import annotations

from controllers.led_controller.lighting_controller import LightingController
from hardware.gpio.gpio_manager_interface import IGPIOManager
from lifecycle.shutdown_protocol import IShutdownHandler
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SHUTDOWN)

"""
IShutdownHandler Protocol
========================
Hardware abstraction for LED strips.
Minimal contract for any physical driver (WS281x, APA102, etc).
"""

class GPIOShutdownHandler(IShutdownHandler):
    """
    Shutdown handler for GPIO hardware.

    Cleans up GPIO pins and resets hardware state.
    This should be one of the last shutdown steps.

    Priority: 10 (shutdown last)
    """

    def __init__(self, gpio_manager: IGPIOManager):
        """
        Initialize GPIO shutdown handler.

        Args:
            gpio_manager: GPIOManager instance for hardware cleanup
        """
        self.gpio_manager = gpio_manager

    @property
    def shutdown_priority(self) -> int:
        """GPIO cleanup has low priority (happens last)."""
        return 10

    async def shutdown(self) -> None:
        """Clean up GPIO."""
        log.info("Cleaning up GPIO...")

        try:
            self.gpio_manager.cleanup()
            log.debug("GPIO cleaned up")
        except Exception as e:
            log.error(f"Error cleaning up GPIO: {e}")
