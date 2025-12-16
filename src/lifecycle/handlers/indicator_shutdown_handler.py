from __future__ import annotations

from lifecycle.shutdown_protocol import IShutdownHandler
from utils.logger import get_logger, LogCategory
from zone_layer.selected_zone_indicator import SelectedZoneIndicator

log = get_logger().for_category(LogCategory.SHUTDOWN)


from typing import Protocol, List
from models.color import Color

class IndicatorShutdownHandler(IShutdownHandler):
    """
    Shutdown handler for selected zone indicator.
    Priority: 115 
    """

    def __init__(self, indicator: SelectedZoneIndicator):
        """
        Initialize LED shutdown handler.

        Args:
            hardware: HardwareBundle containing zone strips
        """
        self.indicator = indicator

    @property
    def shutdown_priority(self) -> int:
        return 115

    async def shutdown(self) -> None:
        log.info("Stopping Selected Zone Indicator...")
            
        try:
            await self.indicator.stop_async()
            log.info("Selected Zone Indicator stopped")
        except Exception as e:
            log.error(f"Error during indicator shutdown: {e}", exc_info=True)
            raise

