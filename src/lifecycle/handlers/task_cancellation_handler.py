from __future__ import annotations
import asyncio
from typing import List

from hardware.hardware_coordinator import HardwareBundle
from controllers.led_controller.lighting_controller import LightingController
from hardware.gpio.gpio_manager import GPIOManager
from lifecycle.shutdown_protocol import IShutdownHandler
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SHUTDOWN)

class TaskCancellationHandler(IShutdownHandler):
    """
    Shutdown handler for asyncio tasks.

    Cancels and awaits all registered tasks to ensure graceful task cleanup.

    Priority: 40
    """

    def __init__(self, tasks: List[asyncio.Task]):
        """  
        Initialize task cancellation handler.

        Args:
            tasks: List of asyncio.Task objects to cancel
        """
        self.tasks = tasks

    @property
    def shutdown_priority(self) -> int:
        """Tasks are cancelled after controllers."""
        return 40

    async def shutdown(self) -> None:
        """Cancel and await all tasks."""
        log.info("Cancelling selected background tasks...")

        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                log.debug(f"Cancelled task: {task.get_name()}")

        # Wait for all tasks to finish (either complete or raise CancelledError)
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        log.debug("All tasks cancelled")
