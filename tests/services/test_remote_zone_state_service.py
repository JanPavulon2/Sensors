"""RemoteZoneStateService: pushing desired state, capability-independent
mutations, and reconciliation when a node reports something different."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.color import Color
from services.remote_zone_state_service import RemoteZoneStateService
from services.rig_service import RigService

CATALOG_YAML = """
catalog:
  drivers:
    - id: mosfet_driver_1ch
      name: "1-channel MOSFET dimmer"
      control_interface: ANALOG_PWM
      channels: [ch0]
  fixtures:
    - id: single_diode
      name: "Single diode"
      component_type: SINGLE_COLOR
      component_count: 1
      addressable_group_count: 1

rig:
  driver_instances:
    - id: desk_dimmer
      definition_id: mosfet_driver_1ch
      node_id: "AA:BB"
      label: "Desk dimmer"
      config: {channel_pins: {ch0: 23}}
  fixture_instances:
    - id: desk_diode
      definition_id: single_diode
      node_id: "AA:BB"
      label: "Desk diode"
      config:
        nominal_color: [255, 170, 80]
        bindings: [{module_instance_id: desk_dimmer, channel_name: ch0, role: SINGLE}]
  zones:
    - zone_id: desk
      display_name: "Desk"
      node_id: "AA:BB"
      device_instance_ids: [desk_diode]
      state: {color: [10, 20, 30], brightness: 80, is_on: true, render_mode: STATIC}
"""


@pytest.fixture
def rig(tmp_path: Path) -> RigService:
    catalog = tmp_path / "rig.yaml"
    catalog.write_text(CATALOG_YAML)
    return RigService(catalog_path=catalog, state_path=tmp_path / "rig.json")


@pytest.fixture
def node_registry() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def state_service(node_registry: AsyncMock, rig: RigService) -> RemoteZoneStateService:
    return RemoteZoneStateService(
        node_registry_service=node_registry, rig_service=rig, event_bus=MagicMock()
    )


def _applied(**overrides) -> dict:
    payload = {
        "zone_id": "desk",
        "is_on": True,
        "brightness": 80,
        "color": {"r": 10, "g": 20, "b": 30},
        "render_mode": "STATIC",
    }
    payload.update(overrides)
    return payload


def test_set_brightness_clamps_and_pushes(
    state_service: RemoteZoneStateService, node_registry: AsyncMock
) -> None:
    asyncio.run(state_service.set_brightness("desk", 150))

    assert state_service.get_state("desk").brightness == 100
    node_registry.send_command.assert_awaited_once()


def test_set_color_pushes_the_full_zone_state(
    state_service: RemoteZoneStateService, node_registry: AsyncMock
) -> None:
    asyncio.run(state_service.set_color("desk", Color.from_rgb(1, 2, 3)))

    node_registry.send_command.assert_awaited_once_with(
        "AA:BB",
        "zone.state",
        {
            "zone_id": "desk",
            "is_on": True,
            "brightness": 80,
            "color": {"r": 1, "g": 2, "b": 3},
            "render_mode": "STATIC",
        },
    )


def test_set_render_mode_accepts_breathe(state_service: RemoteZoneStateService) -> None:
    asyncio.run(state_service.set_render_mode("desk", "breathe"))

    assert state_service.get_state("desk").render_mode == "BREATHE"


def test_set_render_mode_rejects_unknown_modes(state_service: RemoteZoneStateService) -> None:
    with pytest.raises(ValueError, match="Unsupported render mode"):
        asyncio.run(state_service.set_render_mode("desk", "DISCO"))


def test_matching_applied_state_needs_no_correction(
    state_service: RemoteZoneStateService, node_registry: AsyncMock
) -> None:
    corrected = asyncio.run(state_service.reconcile_node("AA:BB", [_applied()]))

    assert corrected == []
    node_registry.send_command.assert_not_awaited()
    assert state_service.is_in_sync("desk") is True


@pytest.mark.parametrize(
    "drift",
    [
        {"brightness": 5},
        {"is_on": False},
        {"render_mode": "BREATHE"},
        {"color": {"r": 255, "g": 0, "b": 0}},
    ],
)
def test_drifted_state_is_repushed(
    state_service: RemoteZoneStateService, node_registry: AsyncMock, drift: dict
) -> None:
    corrected = asyncio.run(state_service.reconcile_node("AA:BB", [_applied(**drift)]))

    assert corrected == ["desk"]
    node_registry.send_command.assert_awaited_once()
    assert state_service.is_in_sync("desk") is False


def test_node_reporting_nothing_is_left_alone(
    state_service: RemoteZoneStateService, node_registry: AsyncMock
) -> None:
    """Older firmware sends no applied_state - that must not trigger a re-push
    on every single heartbeat."""
    corrected = asyncio.run(state_service.reconcile_node("AA:BB", []))

    assert corrected == []
    node_registry.send_command.assert_not_awaited()


def test_push_all_for_node_resends_every_zone(
    state_service: RemoteZoneStateService, node_registry: AsyncMock
) -> None:
    asyncio.run(state_service.push_all_for_node("AA:BB"))

    node_registry.send_command.assert_awaited_once()


def test_pushing_an_unknown_zone_raises(state_service: RemoteZoneStateService) -> None:
    with pytest.raises(ValueError, match="Unknown remote zone"):
        asyncio.run(state_service.push_state("nope"))
