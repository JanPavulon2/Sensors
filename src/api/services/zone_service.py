"""
API Zone Service - Business logic layer between routes and domain

EXPLANATION:
The domain has its own ZoneService (in services/zone_service.py).
This API service is a WRAPPER that:
1. Converts API request objects to domain objects (e.g., ColorRequest → Color)
2. Calls the domain service
3. Converts domain objects back to API response objects (Color → ColorResponse)
4. Handles domain-to-HTTP error mapping

This separation keeps routes clean and focused on HTTP handling.
"""

from typing import List, Optional
from models.enums import ZoneID, ColorMode, LogCategory
from models.color import Color
from models.domain.zone import ZoneCombined
from services.zone_service import ZoneService as DomainZoneService
from managers.color_manager import ColorManager

from api.schemas.zone import (
    ZoneResponse, ZoneStateResponse, ColorResponse, ZoneListResponse,
    ColorRequest, ZoneRenderModeEnum
)
from api.middleware.error_handler import ZoneNotFoundError, InvalidColorModeError

from utils.logger import get_logger
from utils.enum_helper import EnumHelper

log = get_logger().for_category(LogCategory.SYSTEM)


class ZoneAPIService:
    """API wrapper over domain ZoneService"""

    def __init__(
        self,
        zone_service: DomainZoneService,
        color_manager: ColorManager
    ):
        """
        Args:
            zone_service: Domain-level ZoneService
            color_manager: Color manager for preset operations
        """
        self.zone_service = zone_service
        self.color_manager = color_manager

    def get_all_zones(self) -> ZoneListResponse:
        """Get all zones with current state"""
        zones = self.zone_service.get_all()
        zone_responses = [self._zone_to_response(z) for z in zones]
        return ZoneListResponse(zones=zone_responses, count=len(zone_responses))

    def get_zone(self, zone_id: str) -> ZoneResponse:
        """Get single zone by ID

        Args:
            zone_id: Zone ID string (e.g., 'FLOOR')

        Returns:
            ZoneResponse with current state

        Raises:
            ZoneNotFoundError: If zone doesn't exist
        """
        try:
            zone_enum = ZoneID[zone_id.upper()]
            zone = self.zone_service.get_zone(zone_enum)
            return self._zone_to_response(zone)
        except KeyError:
            # Zone ID doesn't exist
            valid_ids = [z.name for z in ZoneID]
            raise ZoneNotFoundError(zone_id)

    def update_zone_color(self, zone_id: str, color_request: ColorRequest) -> ZoneResponse:
        """Update zone color

        Args:
            zone_id: Zone ID string
            color_request: New color specification

        Returns:
            Updated ZoneResponse

        Raises:
            ZoneNotFoundError: If zone doesn't exist
            InvalidColorModeError: If color mode invalid
        """
        try:
            zone_enum = ZoneID[zone_id.upper()]
        except KeyError:
            raise ZoneNotFoundError(zone_id)

        # Convert API request to domain Color object
        color = self._request_to_color(color_request)

        # Update in domain service
        self.zone_service.set_color(zone_enum, color)

        # Fetch updated zone and return
        zone = self.zone_service.get_zone(zone_enum)
        return self._zone_to_response(zone)

    def update_zone_brightness(self, zone_id: str, brightness: int) -> ZoneResponse:
        """Update zone brightness

        Args:
            zone_id: Zone ID string
            brightness: Brightness 0-255

        Returns:
            Updated ZoneResponse
        """
        try:
            zone_enum = ZoneID[zone_id.upper()]
        except KeyError:
            raise ZoneNotFoundError(zone_id)

        self.zone_service.set_brightness(zone_enum, brightness)

        zone = self.zone_service.get_zone(zone_enum)
        return self._zone_to_response(zone)

    def reset_zone(self, zone_id: str) -> ZoneResponse:
        """Reset zone to default state

        Returns zone to its initial/default color and brightness
        """
        try:
            zone_enum = ZoneID[zone_id.upper()]
        except KeyError:
            raise ZoneNotFoundError(zone_id)

        # Reset to black color
        default_color = Color.from_hue(0)
        self.zone_service.set_color(zone_enum, default_color)
        self.zone_service.set_brightness(zone_enum, 100)

        zone = self.zone_service.get_zone(zone_enum)
        return self._zone_to_response(zone)

    # ===== CONVERSION HELPERS =====

    def _request_to_color(self, color_request: ColorRequest) -> Color:
        """Convert ColorRequest to domain Color object

        Handles all color modes: RGB, HUE, PRESET, HSV

        Args:
            color_request: API request with color specification

        Returns:
            Domain Color object

        Raises:
            InvalidColorModeError: If mode/values invalid
        """
        mode = color_request.mode

        if mode == "RGB":
            if not color_request.rgb:
                raise InvalidColorModeError(mode, ["HUE", "RGB", "PRESET", "HSV"])
            r, g, b = color_request.rgb
            return Color.from_rgb(r, g, b)

        elif mode == "HUE":
            if color_request.hue is None:
                raise InvalidColorModeError(mode, ["HUE", "RGB", "PRESET", "HSV"])
            return Color.from_hue(color_request.hue)

        elif mode == "PRESET":
            if not color_request.preset:
                raise InvalidColorModeError(mode, ["HUE", "RGB", "PRESET", "HSV"])
            return Color.from_preset(color_request.preset, self.color_manager)

        elif mode == "HSV":
            # HSV conversion: store as HUE, brightness is separate
            if color_request.hue is None:
                raise InvalidColorModeError(mode, ["HUE", "RGB", "PRESET", "HSV"])
            return Color.from_hue(color_request.hue)

        else:
            valid = ["HUE", "RGB", "PRESET", "HSV"]
            raise InvalidColorModeError(mode, valid)

    def _color_to_response(self, color: Color) -> ColorResponse:
        """Convert domain Color to API response"""
        r, g, b = color.to_rgb()

        response_dict = {
            "mode": color.mode.name,
            "rgb": [r, g, b],
            "hue": None,
            "brightness": None,
            "preset": None,
            "saturation": None
        }

        # Add mode-specific fields
        if color.mode == ColorMode.HUE:
            response_dict["hue"] = color.to_hue()
        elif color.mode == ColorMode.PRESET:
            response_dict["preset"] = color._preset_name

        return ColorResponse(**response_dict)

    def _zone_to_response(self, zone: ZoneCombined) -> ZoneResponse:
        """Convert domain ZoneCombined to API response"""
        return ZoneResponse(
            id=zone.config.id.name,
            name=zone.config.display_name,
            pixel_count=zone.config.pixel_count,
            state=ZoneStateResponse(
                color=self._color_to_response(zone.state.color),
                brightness=zone.brightness,
                enabled=zone.config.enabled,
                render_mode=zone.state.mode.name,
                animation_id=zone.state.animation_id.name if zone.state.animation_id else None
            ),
            gpio=zone.config.gpio,
            layout=None  # TODO: Add layout support in future
        )
