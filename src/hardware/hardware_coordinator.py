from __future__ import annotations
from typing import Dict, TYPE_CHECKING

from hardware.input.control_panel import ControlPanel
from hardware.gpio import IGPIOManager
from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory
from hardware.led.led_channel import LedChannel

if TYPE_CHECKING:
    from managers.hardware_manager import HardwareManager

log = get_logger().for_category(LogCategory.HARDWARE)


class HardwareCoordinator:
    """
    Creates ALL hardware objects for the system:

      - ControlPanel (buttons + encoders)
      - LedChannels (built via LedChannelFactory)
      - Provides GPIO + HardwareManager in bundle

    No knowledge of FrameManager, ZoneService, animations,
    or domain-level logic.
    """

    def __init__(self, hardware_manager: HardwareManager, gpio_manager: IGPIOManager):
        self.hardware_manager = hardware_manager
        self.gpio_manager = gpio_manager

    def initialize(self, all_zones) -> "HardwareBundle":
        from hardware.led.led_channel_factory import LedChannelFactory

        log.info("HardwareCoordinator: Initializing hardware layer...")

        control_panel = ControlPanel(
            self.hardware_manager,
            self.gpio_manager
        )

        led_channels = LedChannelFactory.create(all_zones, self.hardware_manager)

        return HardwareBundle(
            control_panel=control_panel,
            led_channels=led_channels,
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
        led_channels: Dict[int, LedChannel], 
        gpio_manager: IGPIOManager, 
        hardware_manager: HardwareManager
    ):
        self.control_panel = control_panel
        self.led_channels = led_channels
        self.gpio_manager = gpio_manager
        self.hardware_manager = hardware_manager
