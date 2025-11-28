"""
Shutdown handlers for application components.

Each handler is responsible for shutting down one aspect of the application.
They are called in priority order by ShutdownCoordinator.
"""

import asyncio
from typing import List, Optional

from hardware.hardware_coordinator import HardwareBundle
from controllers.led_controller.lighting_controller import LightingController
from hardware.gpio.gpio_manager import GPIOManager
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SYSTEM)


class LEDShutdownHandler:
    """
    Shutdown handler for LED hardware.

    Clears all LEDs immediately to prevent them from being left on.
    This should be the first shutdown step.

    Priority: 100 (shutdown first)
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
        """LED clearing has highest priority."""
        return 100

    async def shutdown(self) -> None:
        """Clear all LEDs on all GPIO strips."""
        log.info("Clearing LEDs on all GPIO strips...")

        try:
            # Clear all zone strips (there may be multiple GPIO pins)
            for gpio_pin, strip in self.hardware.zone_strips.items():
                try:
                    strip.clear()
                    log.debug(f"✓ Cleared GPIO {gpio_pin}")
                except Exception as e:
                    log.error(f"Error clearing GPIO {gpio_pin}: {e}")

            log.info("✓ All LEDs cleared")

        except Exception as e:
            log.error(f"Error during LED clearing: {e}", exc_info=True)
            raise


class AnimationShutdownHandler:
    """
    Shutdown handler for animation engine.

    Stops all running animations and animation service.

    Priority: 80
    """

    def __init__(self, led_controller: LightingController):
        """
        Initialize animation shutdown handler.

        Args:
            led_controller: LightingController with animation engine
        """
        self.led_controller = led_controller

    @property
    def shutdown_priority(self) -> int:
        """Animations shutdown second."""
        return 80

    async def shutdown(self) -> None:
        """Stop animation engine and service."""
        log.info("Stopping animations...")

        # Stop animation service
        try:
            self.led_controller.animation_mode_controller.animation_service.stop_all()
            log.debug("✓ Animation service stopped")
        except Exception as e:
            log.error(f"Error stopping animation service: {e}")

        # Stop animation engine
        try:
            if (
                self.led_controller.animation_engine
                and self.led_controller.animation_engine.is_running()
            ):
                await self.led_controller.animation_engine.stop()
                log.debug("✓ Animation engine stopped")
        except Exception as e:
            log.error(f"Error stopping animation engine: {e}")


class APIServerShutdownHandler:
    """
    Shutdown handler for FastAPI/uvicorn server.

    Stops the HTTP/WebSocket API server and releases port 8000.

    Priority: 60
    """

    def __init__(self, api_server):
        """
        Initialize API server shutdown handler.

        Args:
            api_server: uvicorn.Server instance
        """
        self.api_server = api_server

    @property
    def shutdown_priority(self) -> int:
        """API server shuts down after animations."""
        return 60

    async def shutdown(self) -> None:
        """Shutdown uvicorn server."""
        log.info("Stopping API server...")

        try:
            if self.api_server and self.api_server.started:
                await self.api_server.shutdown()
                # Give it a moment to release the port
                await asyncio.sleep(0.1)
                log.debug("✓ API server stopped")
        except Exception as e:
            log.error(f"Error stopping API server: {e}")


class TaskCancellationHandler:
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
        log.info("Cancelling background tasks...")

        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                log.debug(f"Cancelled task: {task.get_name()}")

        # Wait for all tasks to finish (either complete or raise CancelledError)
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        log.debug("✓ All tasks cancelled")


class GPIOShutdownHandler:
    """
    Shutdown handler for GPIO hardware.

    Cleans up GPIO pins and resets hardware state.
    This should be one of the last shutdown steps.

    Priority: 10 (shutdown last)
    """

    def __init__(self, gpio_manager: GPIOManager):
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
            log.debug("✓ GPIO cleaned up")
        except Exception as e:
            log.error(f"Error cleaning up GPIO: {e}")
