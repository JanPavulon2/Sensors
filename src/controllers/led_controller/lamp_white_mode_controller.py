"""LampWhiteModeController - desk lamp white mode feature"""

from __future__ import annotations

import asyncio
from models.enums import ZoneID
from models.color import Color
from utils.logger import get_logger, LogCategory
from services import ServiceContainer

log = get_logger().for_category(LogCategory.GENERAL)


class LampWhiteModeController:
    """
    Desk lamp white mode feature controller

    Responsibilities:
    - Toggle LAMP zone to/from warm white
    - Save/restore previous lamp color
    - Exclude lamp from zone selector when active
    """

    def __init__(self, services: ServiceContainer):
        """
        Initialize lamp white mode controller with dependency injection.

        Args:
            services: ServiceContainer with all core services and managers
        """
        self.zone_service = services.zone_service
        self.app_state = services.app_state_service
        self.color_manager = services.color_manager

        self.lamp_white_mode = self.app_state.get_state().lamp_white_mode
        self.lamp_white_saved_state = self.app_state.get_state().lamp_white_saved_state

    async def toggle(self):
        """Toggle LAMP zone to/from warm white preset"""
        lamp = self.zone_service.get_zone(ZoneID.LAMP)

        if not self.lamp_white_mode:
            # Enable: save state and apply warm white
            self.lamp_white_saved_state = {
                "color": lamp.state.color.to_dict(),
                "brightness": lamp.brightness
            }
            self.lamp_white_mode = True

            warm = Color.from_preset("warm_white", self.color_manager)
            self.zone_service.set_color(ZoneID.LAMP, warm)
            self.zone_service.set_brightness(ZoneID.LAMP, 100)

            # Refresh lamp after service changes and render
            lamp = self.zone_service.get_zone(ZoneID.LAMP)
            # TODO: self.strip_controller.render_zone_combined(lamp)  # Controller disabled
            # TODO: Direct FrameManager submission needed here

            log.info("Lamp white mode ON")
        else:
            # Disable: restore saved state
            if self.lamp_white_saved_state:
                from_dict = Color.from_dict(
                    self.lamp_white_saved_state["color"],
                    self.color_manager
                )
                brightness = self.lamp_white_saved_state["brightness"]
                self.zone_service.set_color(ZoneID.LAMP, from_dict)
                self.zone_service.set_brightness(ZoneID.LAMP, brightness)

                lamp = self.zone_service.get_zone(ZoneID.LAMP)
                # TODO: self.strip_controller.render_zone_combined(lamp)  # Controller disabled
                # TODO: Direct FrameManager submission needed here

            self.lamp_white_saved_state = None
            self.lamp_white_mode = False
            log.info("Lamp white mode OFF")

        self.app_state.set_lamp_white_mode(self.lamp_white_mode)
        self.app_state.set_lamp_white_saved_state(self.lamp_white_saved_state)
