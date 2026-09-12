"""Remote Zone Render Bridge - forwards remote-zone state changes to the
owning ESP32 node via NodeRegistryService.send_command(), instead of through
FrameManager (which only drives locally-wired GPIO strips - see
docs/architecture-vnext/05-esp32-rpi-roadmap.md Phase 6: "RPi streams zone
state, ESP32 renders it locally")."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from models.color import Color
from models.domain.remote_zone import RemoteZoneConfig, RemoteZoneState, load_remote_zone_configs
from services.node_registry_service import NodeRegistryService
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.ZONE)


class RemoteZoneRenderBridge:
    def __init__(self, node_registry_service: NodeRegistryService, config_path: Path):
        self.node_registry_service = node_registry_service
        self._configs_by_label: Dict[str, RemoteZoneConfig] = {
            config.zone_label: config for config in load_remote_zone_configs(config_path)
        }
        self._states_by_label: Dict[str, RemoteZoneState] = {
            label: RemoteZoneState(color=Color.from_rgb(255, 255, 255))
            for label in self._configs_by_label
        }

    def list_zones(self) -> List[RemoteZoneConfig]:
        return list(self._configs_by_label.values())

    def get_zones_for_node(self, node_id: str) -> List[RemoteZoneConfig]:
        return [config for config in self._configs_by_label.values() if config.node_id == node_id]

    def get_state(self, zone_label: str) -> RemoteZoneState:
        return self._require_state(zone_label)

    async def set_color(self, zone_label: str, color: Color) -> None:
        state = self._require_state(zone_label)
        state.color = color
        await self._push_state(zone_label)

    async def set_brightness(self, zone_label: str, brightness: int) -> None:
        state = self._require_state(zone_label)
        state.brightness = max(0, min(100, brightness))
        await self._push_state(zone_label)

    async def set_is_on(self, zone_label: str, is_on: bool) -> None:
        state = self._require_state(zone_label)
        state.is_on = is_on
        await self._push_state(zone_label)

    def _require_state(self, zone_label: str) -> RemoteZoneState:
        if zone_label not in self._states_by_label:
            raise ValueError(f"Unknown remote zone: {zone_label}")
        return self._states_by_label[zone_label]

    async def _push_state(self, zone_label: str) -> None:
        config = self._configs_by_label[zone_label]
        state = self._states_by_label[zone_label]
        red, green, blue = state.color.to_rgb()

        await self.node_registry_service.send_command(
            config.node_id,
            "zone.state",
            {
                "is_on": state.is_on,
                "brightness": state.brightness,
                "color": {"r": red, "g": green, "b": blue},
                "render_mode": state.render_mode,
            },
        )
        log.info(f"Pushed state to remote zone '{zone_label}'", node_id=config.node_id)
