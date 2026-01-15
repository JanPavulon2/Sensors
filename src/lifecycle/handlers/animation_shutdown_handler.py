from __future__ import annotations
import asyncio

from controllers.led_controller.lighting_controller import LightingController
from lifecycle.shutdown_protocol import IShutdownHandler
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SHUTDOWN)

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
        log.info("Stopping all animations...")

        try:
            engine = self.lighting_controller.animation_engine

            if engine:
                if engine.tasks:
                    log.debug(f"Found {len(engine.tasks)} active animation task(s)")
                    await engine.stop_all()
                    log.info("All animations stopped successfully")
                else:
                    log.debug("No active animations to stop")
            else:
                log.warn("No animation engine found")

        except asyncio.CancelledError:
            log.warn("Cancelled during shutdown (unexpected)")
            raise
        except Exception as e:
            log.error(f"Error stopping animations: {e}", exc_info=True)
            