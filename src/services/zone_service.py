"""Zone service - Business logic for zones"""

from typing import List, Optional, Any
from models.enums import ZoneID, ParamID
from models.domain import ZoneCombined
from models.color import Color
from services.data_assembler import DataAssembler
from utils.logger import get_category_logger, LogCategory

log = get_category_logger(LogCategory.ZONE)


class ZoneService:
    """High-level zone operations"""

    def __init__(self, assembler: DataAssembler):
        self.assembler = assembler
        self.zones = assembler.build_zones()
        self._by_id = {zone.config.id: zone for zone in self.zones}

        log(f"ZoneService initialized with {len(self.zones)} zones")

    def get_zone(self, zone_id: ZoneID) -> ZoneCombined:
        """Get zone by ID"""
        return self._by_id[zone_id]

    def get_all(self) -> List[ZoneCombined]:
        """Get all zones"""
        return self.zones

    def get_enabled(self) -> List[ZoneCombined]:
        """Get only enabled zones"""
        return [zone for zone in self.zones if zone.config.enabled]

    def get_total_pixel_count(self) -> int:
        """Get total pixel count from all enabled zones"""
        return sum(zone.config.pixel_count for zone in self.get_all())

    def set_color(self, zone_id: ZoneID, color: Color) -> None:
        """Set zone color"""
        zone = self.get_zone(zone_id)
        zone.state.color = color
        log(f"Set {zone.config.display_name} color: {color.mode.name}")
        self.save()

    def set_brightness(self, zone_id: ZoneID, brightness: int) -> None:
        """Set zone brightness"""
        zone = self.get_zone(zone_id)
        zone.set_param_value(ParamID.ZONE_BRIGHTNESS, brightness)
        log(f"Set {zone.config.display_name} brightness: {brightness}%")
        self.save()

    def adjust_parameter(self, zone_id: ZoneID, param_id: ParamID, delta: int) -> None:
        """Adjust zone parameter by delta steps"""
        zone = self.get_zone(zone_id)
        zone.adjust_param(param_id, delta)
        log(f"Adjusted {zone.config.display_name}.{param_id.name}: {zone.get_param_value(param_id)}")
        self.save()

    def set_parameter(self, zone_id: ZoneID, param_id: ParamID, value: Any) -> None:
        """Set zone parameter value directly"""
        zone = self.get_zone(zone_id)
        zone.set_param_value(param_id, value)
        log(f"Set {zone.config.display_name}.{param_id.name} = {value}")
        self.save()

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
        
    def save(self) -> None:
        """Persist current state"""
        self.assembler.save_zone_state(self.zones)
