from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from models.color import Color
from services.remote_zone_render_bridge import RemoteZoneRenderBridge


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    config_file = tmp_path / "esp32_zones.yaml"
    config_file.write_text(
        """
remote_zones:
  - node_id: "AA:BB:CC:DD:EE:FF"
    zone_label: "esp32_strip_1"
    display_name: "Workshop Strip"
    pixel_count: 30
    sync_group: "workshop"
"""
    )
    return config_file


@pytest.fixture
def fake_node_registry_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def bridge(fake_node_registry_service: AsyncMock, config_path: Path) -> RemoteZoneRenderBridge:
    return RemoteZoneRenderBridge(node_registry_service=fake_node_registry_service, config_path=config_path)


def test_list_zones_returns_configs_from_yaml(bridge: RemoteZoneRenderBridge) -> None:
    zones = bridge.list_zones()

    assert len(zones) == 1
    assert zones[0].zone_label == "esp32_strip_1"


def test_get_zones_for_node_filters_by_node_id(bridge: RemoteZoneRenderBridge) -> None:
    assert len(bridge.get_zones_for_node("AA:BB:CC:DD:EE:FF")) == 1
    assert bridge.get_zones_for_node("unknown") == []


def test_get_state_returns_default_state(bridge: RemoteZoneRenderBridge) -> None:
    state = bridge.get_state("esp32_strip_1")

    assert state.is_on is True
    assert state.brightness == 100


def test_set_color_pushes_zone_state_command(
    bridge: RemoteZoneRenderBridge, fake_node_registry_service: AsyncMock
) -> None:
    asyncio.run(bridge.set_color("esp32_strip_1", Color.from_rgb(10, 20, 30)))

    fake_node_registry_service.send_command.assert_awaited_once_with(
        "AA:BB:CC:DD:EE:FF",
        "zone.state",
        {
            "is_on": True,
            "brightness": 100,
            "color": {"r": 10, "g": 20, "b": 30},
            "render_mode": "STATIC",
        },
    )


def test_set_brightness_clamps_and_pushes(
    bridge: RemoteZoneRenderBridge, fake_node_registry_service: AsyncMock
) -> None:
    asyncio.run(bridge.set_brightness("esp32_strip_1", 150))

    assert bridge.get_state("esp32_strip_1").brightness == 100
    fake_node_registry_service.send_command.assert_awaited_once()


def test_set_color_raises_for_unknown_zone(bridge: RemoteZoneRenderBridge) -> None:
    with pytest.raises(ValueError):
        asyncio.run(bridge.set_color("unknown", Color.from_rgb(0, 0, 0)))
