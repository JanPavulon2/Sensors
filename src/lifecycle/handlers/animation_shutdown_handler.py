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
    Stops all running animation tasks before LED cleanup.
    """

    def __init__(
        self, 
        lighting_controller: LightingController
    ):
        self.lighting_controller = lighting_controller

    @property
    def shutdown_priority(self) -> int:
        return 130  # FIRST

    async def shutdown(self) -> None:
        log.info("Stopping animations...")

        # 1) Stop AnimationEngine tasks
        try:
            animation_service = self.lighting_controller.animation_mode_controller.animation_service
            
            if animation_service:
                animation_service.stop_all()
                log.debug("AnimationService stopped")
        
        except Exception as e:
            log.error(f"Error stopping AnimationService: {e}")
                            
        
        
        # --- 2) Stop new AnimationEngine
        try:
            engine = self.lighting_controller.animation_engine

            if engine and engine.tasks:
                await engine.stop_all()
                log.debug("AnimationEngine stopped")

        except Exception as e:
            log.error(f"Error stopping AnimationEngine: {e}")
            