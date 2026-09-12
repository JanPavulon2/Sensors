"""Remote zone domain models (Phase 6 - LED zones rendered on ESP32 nodes,
not on the RPi's own GPIO strips - remote zones render on the ESP32 itself,
so they intentionally do not go through ZoneID/ZoneService/FrameManager)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml

from models.color import Color


@dataclass(frozen=True)
class RemoteZoneConfig:
    """Immutable remote zone configuration from esp32_zones.yaml"""
    node_id: str
    zone_label: str
    display_name: str
    pixel_count: int
    sync_group: Optional[str] = None


@dataclass
class RemoteZoneState:
    """Mutable remote zone state, mirrored to the owning ESP32 via
    RemoteZoneRenderBridge/NodeRegistryService."""
    color: Color
    brightness: int = 100
    is_on: bool = True
    render_mode: str = "STATIC"  # "STATIC" or "BREATHE" - matches firmware's built-in animations


def load_remote_zone_configs(config_path: Path) -> List[RemoteZoneConfig]:
    """Loads esp32_zones.yaml independently of ConfigManager's include
    system, since remote zones are a separate concern from the local
    GPIO-strip pipeline ConfigManager/HardwareManager own."""
    if not config_path.exists():
        return []

    with open(config_path, "r", encoding="utf-8") as config_file:
        raw_data = yaml.safe_load(config_file) or {}

    return [
        RemoteZoneConfig(
            node_id=entry["node_id"],
            zone_label=entry["zone_label"],
            display_name=entry.get("display_name", entry["zone_label"]),
            pixel_count=entry.get("pixel_count", 1),
            sync_group=entry.get("sync_group"),
        )
        for entry in raw_data.get("remote_zones", [])
    ]
