from __future__ import annotations
from typing import Dict, TYPE_CHECKING, List

from components import ControlPanel
from hardware.gpio.gpio_manager import GPIOManager
from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory
from zone_layer.zone_strip import ZoneStrip

if TYPE_CHECKING:
    from managers.hardware_manager import HardwareManager

log = get_logger().for_category(LogCategory.HARDWARE)


class HardwareCoordinator:
    """
    Creates ALL hardware objects for the system:

      - ControlPanel (buttons + encoders)
      - ZoneStrips (built via ZoneStripFactory)
      - Provides GPIO + HardwareManager in bundle

    No knowledge of FrameManager, ZoneService, animations,
    or domain-level logic.
    """

    def __init__(self, hardware_manager: HardwareManager, gpio_manager: GPIOManager):
        self.hardware_manager = hardware_manager
        self.gpio_manager = gpio_manager

    def initialize(self, all_zones) -> "HardwareBundle":
        from hardware.zone_strip_factory import ZoneStripFactory

        log.info("HardwareCoordinator: Initializing hardware layer...")

        control_panel = ControlPanel(
            self.hardware_manager,
            self.gpio_manager
        )

        zone_strips = ZoneStripFactory.create(all_zones, self.hardware_manager)

        return HardwareBundle(
            control_panel=control_panel,
            zone_strips=zone_strips,
            gpio_manager=self.gpio_manager,
            hardware_manager=self.hardware_manager
        )


class HardwareBundle:
    """
    Bundles all hardware objects for higher-level application init.
    """

    def __init__(
        self, 
        control_panel: ControlPanel, 
        zone_strips: Dict[int, ZoneStrip], 
        gpio_manager: GPIOManager, 
        hardware_manager: HardwareManager
    ):
        self.control_panel = control_panel
        self.zone_strips = zone_strips
        self.gpio_manager = gpio_manager
        self.hardware_manager = hardware_manager
