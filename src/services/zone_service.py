"""Zone service - Business logic for zones"""

from typing import List, Optional, Any
from models.enums import ZoneID, ParamID, ZoneRenderMode
from models.domain import ZoneCombined
from models.color import Color
from services.data_assembler import DataAssembler
from services.application_state_service import ApplicationStateService
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.ZONE)

class ZoneService:
    """High-level zone operations"""

    def __init__(self, assembler: DataAssembler, app_state_service: ApplicationStateService):
        self.assembler = assembler
        self.zones = assembler.build_zones()
        self._by_id = {zone.config.id: zone for zone in self.zones}
        self.app_state_service = app_state_service

        # Track which zone was last modified to enable selective saves
        self._last_modified_zone_id: Optional[ZoneID] = None

        log.info(f"ZoneService initialized with {len(self.zones)} zones")

    def get_zone(self, zone_id: ZoneID) -> ZoneCombined:
        """Get zone by ID"""
        return self._by_id[zone_id]

    def get_all(self) -> List[ZoneCombined]:
        """Get all zones"""
        return self.zones

    def get_selected_zone(self) -> Optional[ZoneCombined]:
        """
        Get currently selected zone based on ApplicationState.selected_zone_index

        Per-zone mode: The selected zone determines which zone's mode and parameters
        are being edited. A zone is always selected (even if not visible due to lack
        of pulse), allowing per-zone mode toggling via BTN4.

        Returns:
            Selected ZoneCombined object or None if app_state_service not available
        """
        if not self.app_state_service:
            log.warn("Cannot get selected zone: app_state_service not configured")
            return None

        app_state = self.app_state_service.get_state()
        zone_index = app_state.selected_zone_index

        if 0 <= zone_index < len(self.zones):
            return self.zones[zone_index]
        else:
            log.warn(f"Invalid zone index: {zone_index}, clamping to 0")
            return self.zones[0] if self.zones else None

    def get_enabled(self) -> List[ZoneCombined]:
        """Get only enabled zones"""
        return [zone for zone in self.zones if zone.config.enabled]

    def get_by_render_mode(self, mode: ZoneRenderMode) -> List[ZoneCombined]:
        """Get zones filtered by render mode"""
        return [zone for zone in self.zones if zone.state.mode == mode]

    def get_total_pixel_count(self) -> int:
        """Get total pixel count from all enabled zones"""
        return sum(zone.config.pixel_count for zone in self.get_all())

    def set_color(self, zone_id: ZoneID, color: Color) -> None:
        """Set zone color"""
        zone = self.get_zone(zone_id)
        zone.state.color = color
        log.info(f"Set {zone.config.display_name} color: {color.mode.name}")
        self._save_zone(zone_id)

    def set_brightness(self, zone_id: ZoneID, brightness: int) -> None:
        """Set zone brightness"""
        zone = self.get_zone(zone_id)
        zone.set_param_value(ParamID.ZONE_BRIGHTNESS, brightness)
        log.info(f"Set {zone.config.display_name} brightness: {brightness}%")
        self._save_zone(zone_id)

    def adjust_parameter(self, zone_id: ZoneID, param_id: ParamID, delta: int) -> None:
        """Adjust zone parameter by delta steps"""
        zone = self.get_zone(zone_id)
        zone.adjust_param(param_id, delta)
        log.info(f"Adjusted {zone.config.display_name}.{param_id.name}: {zone.get_param_value(param_id)}")
        self._save_zone(zone_id)

    def set_parameter(self, zone_id: ZoneID, param_id: ParamID, value: Any) -> None:
        """Set zone parameter value directly"""
        zone = self.get_zone(zone_id)
        zone.set_param_value(param_id, value)
        log.info(f"Set {zone.config.display_name}.{param_id.name} = {value}")
        self._save_zone(zone_id)

    def get_rgb(self, zone_id: ZoneID) -> tuple[int, int, int]:
        """Get zone RGB color with brightness applied"""
        zone = self.get_zone(zone_id)
        return zone.get_rgb()

    def get_zones_states(self) -> dict[ZoneID, tuple[Color, int]]:
        """Get current zone states as dict of (Color, brightness)"""
        return {
            zone.config.id: (zone.state.color, zone.brightness)
            for zone in self.get_all()
        }

    def get_zones_by_gpio(self, gpio_pin: int) -> List[ZoneCombined]:
        """
        Get all zones assigned to a specific GPIO pin

        Useful for:
        - Debugging multi-GPIO setups
        - Verifying zone→GPIO mappings
        - Per-GPIO strip operations

        Args:
            gpio_pin: GPIO pin number (18, 19, etc.)

        Returns:
            List of zones on this GPIO (may be empty)

        Example:
            gpio_18_zones = zone_service.get_zones_by_gpio(18)
            # Returns: [FLOOR, LEFT, TOP, RIGHT, BOTTOM, LAMP]
        """
        return [zone for zone in self.zones if zone.config.gpio == gpio_pin]

    def get_all_gpios(self) -> List[int]:
        """
        Get sorted list of all GPIO pins in use

        Useful for:
        - Iterating over all GPIO pins
        - Discovering which GPIOs are configured
        - Multi-GPIO hardware operations

        Returns:
            Sorted list of unique GPIO pin numbers

        Example:
            gpios = zone_service.get_all_gpios()
            # Returns: [18, 19]

            for gpio in gpios:
                zones = zone_service.get_zones_by_gpio(gpio)
                print(f"GPIO {gpio}: {len(zones)} zones")
        """
        return sorted(set(zone.config.gpio for zone in self.zones))

    def _save_zone(self, zone_id: ZoneID) -> None:
        """
        Save only the specified zone to state.json.

        This is more efficient than saving all zones when only one was modified.
        The assembler's debouncing will batch rapid saves within 500ms window.

        Args:
            zone_id: ID of the zone to save
        """
        self._last_modified_zone_id = zone_id
        zone = self.get_zone(zone_id)
        # Pass only the modified zone to reduce I/O (assembler handles debouncing)
        self.assembler.save_zone_state([zone])

    def save(self) -> None:
        """Persist current state"""
        self.assembler.save_zone_state(self.zones)

    def save_state(self) -> None:
        """Persist current state (alias for save)"""
        self.save()
