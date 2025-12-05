"""
Shutdown handlers for application components.

Each handler is responsible for shutting down one aspect of the application.
They are called in priority order by ShutdownCoordinator.
"""

from __future__ import annotations
import asyncio

from typing import List, Optional

from hardware.hardware_coordinator import HardwareBundle
from controllers.led_controller.lighting_controller import LightingController
from hardware.gpio.gpio_manager import GPIOManager
from lifecycle.shutdown_protocol import IShutdownHandler
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SHUTDOWN)

"""
IShutdownHandler Protocol
========================
Hardware abstraction for LED strips.
Minimal contract for any physical driver (WS281x, APA102, etc).
"""

from typing import Protocol, List
from models.color import Color

class AnimationShutdownHandler(IShutdownHandler):
    """
    Shutdown handler for animation engine.

    Stops all running animations and animation service (FrameManager).
    Must run BEFORE LEDShutdownHandler to prevent race conditions where
    FrameManager continues submitting frames after LEDs are cleared.

    Priority: 105 (runs FIRST, before LED clearing)
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
        """Animations shutdown FIRST (before LEDs cleared)."""
        return 105

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

