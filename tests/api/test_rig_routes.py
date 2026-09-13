"""Rig API: catalog, wiring CRUD, derived capabilities, and the capability
guard that refuses control the hardware physically cannot perform."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_service_container
from api.main import create_app
from services.remote_zone_state_service import RemoteZoneStateService
from services.rig_service import RigService
from services.service_container import ServiceContainer

CATALOG_YAML = """
catalog:
  drivers:
    - id: mosfet_driver_1ch
      name: "1-channel MOSFET dimmer"
      control_interface: ANALOG_PWM
      channels: [ch0]
    - id: mosfet_driver_3ch
      name: "3-channel MOSFET dimmer"
      control_interface: ANALOG_PWM
      channels: [ch0, ch1, ch2]
  fixtures:
    - id: single_diode
      name: "Single diode"
      component_type: SINGLE_COLOR
      component_count: 1
      addressable_group_count: 1
    - id: analog_rgb_strip
      name: "Analog RGB strip"
      component_type: RGB
      component_count: 150
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
        white_profile: WARM
        bindings: [{module_instance_id: desk_dimmer, channel_name: ch0, role: SINGLE}]
  zones:
    - zone_id: desk
      display_name: "Desk"
      node_id: "AA:BB"
      device_instance_ids: [desk_diode]
      state: {color: [255, 170, 80], brightness: 80, is_on: true, render_mode: STATIC}
"""


@pytest.fixture
def rig(tmp_path: Path) -> RigService:
    catalog = tmp_path / "rig.yaml"
    catalog.write_text(CATALOG_YAML)
    return RigService(catalog_path=catalog, state_path=tmp_path / "rig.json")


@pytest.fixture
def client(rig: RigService) -> TestClient:
    node_registry = AsyncMock()
    state_service = RemoteZoneStateService(
        node_registry_service=node_registry, rig_service=rig, event_bus=MagicMock()
    )
    app = create_app()

    async def fake_get_service_container() -> ServiceContainer:
        container = AsyncMock(spec=ServiceContainer)
        container.node_registry_service = node_registry
        container.rig_service = rig
        container.remote_zone_state_service = state_service
        # Only reached for PRESET colours, which these tests do not use.
        container.color_manager = AsyncMock()
        return container

    app.dependency_overrides[get_service_container] = fake_get_service_container
    test_client = TestClient(app)
    test_client.node_registry = node_registry  # type: ignore[attr-defined]
    return test_client


def test_catalog_lists_drivers_and_fixtures(client: TestClient) -> None:
    body = client.get("/api/v1/rig/catalog").json()

    assert [driver["id"] for driver in body["drivers"]] == [
        "mosfet_driver_1ch",
        "mosfet_driver_3ch",
    ]
    assert body["drivers"][0]["control_interface"] == "ANALOG_PWM"
    assert body["drivers"][0]["channels"] == ["ch0"]
    assert body["fixtures"][0]["component_type"] == "SINGLE_COLOR"


def test_zone_reports_derived_capabilities_not_assumed_ones(client: TestClient) -> None:
    body = client.get("/api/v1/rig/zones/desk").json()

    assert body["capabilities"] == ["dimming", "switch_binary"]
    assert body["fixtures"][0]["config"]["nominal_color"] == [255, 170, 80]


def test_brightness_is_accepted_for_a_dimmable_diode(client: TestClient) -> None:
    response = client.put("/api/v1/rig/zones/desk/brightness", json={"brightness": 42})

    assert response.status_code == 204
    assert client.get("/api/v1/rig/zones/desk/state").json()["brightness"] == 42


def test_colour_is_refused_for_a_single_white_diode(client: TestClient) -> None:
    """The point of derived capabilities: asking a MOSFET-dimmed white diode
    for a colour is a client bug, not a silent 204."""
    response = client.put(
        "/api/v1/rig/zones/desk/color",
        json={"color": {"mode": "RGB", "rgb": [255, 0, 0]}},
    )

    assert response.status_code == 409
    assert "color_control_rgb" in response.json()["detail"]


def test_render_mode_can_be_switched_to_breathe(client: TestClient) -> None:
    response = client.put("/api/v1/rig/zones/desk/render-mode", json={"render_mode": "BREATHE"})

    assert response.status_code == 204
    assert client.get("/api/v1/rig/zones/desk/state").json()["render_mode"] == "BREATHE"


def test_unknown_render_mode_is_rejected(client: TestClient) -> None:
    response = client.put("/api/v1/rig/zones/desk/render-mode", json={"render_mode": "DISCO"})

    assert response.status_code == 400


def test_editing_a_fixture_updates_its_user_declared_colour(client: TestClient) -> None:
    response = client.put(
        "/api/v1/rig/fixtures/desk_diode",
        json={
            "id": "desk_diode",
            "definition_id": "single_diode",
            "node_id": "AA:BB",
            "label": "Desk diode (cold)",
            "nominal_color": [200, 220, 255],
            "white_profile": "COLD",
            "bindings": [
                {"module_instance_id": "desk_dimmer", "channel_name": "ch0", "role": "SINGLE"}
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["config"]["nominal_color"] == [200, 220, 255]
    assert response.json()["capabilities"] == ["dimming", "switch_binary"]


def test_wiring_a_three_channel_rgb_fixture_unlocks_colour(client: TestClient) -> None:
    client.put(
        "/api/v1/rig/drivers/rgb_dimmer",
        json={
            "id": "rgb_dimmer",
            "definition_id": "mosfet_driver_3ch",
            "node_id": "AA:BB",
            "label": "RGB dimmer",
            "channel_pins": {"ch0": 25, "ch1": 26, "ch2": 27},
        },
    )
    response = client.put(
        "/api/v1/rig/fixtures/rgb_strip",
        json={
            "id": "rgb_strip",
            "definition_id": "analog_rgb_strip",
            "node_id": "AA:BB",
            "label": "RGB strip",
            "bindings": [
                {"module_instance_id": "rgb_dimmer", "channel_name": "ch0", "role": "RED"},
                {"module_instance_id": "rgb_dimmer", "channel_name": "ch1", "role": "GREEN"},
                {"module_instance_id": "rgb_dimmer", "channel_name": "ch2", "role": "BLUE"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["capabilities"] == ["color_control_rgb", "dimming", "switch_binary"]


def test_binding_to_a_missing_channel_is_a_bad_request(client: TestClient) -> None:
    response = client.put(
        "/api/v1/rig/fixtures/broken",
        json={
            "id": "broken",
            "definition_id": "single_diode",
            "node_id": "AA:BB",
            "label": "Broken",
            "bindings": [
                {"module_instance_id": "desk_dimmer", "channel_name": "ch9", "role": "SINGLE"}
            ],
        },
    )

    assert response.status_code == 400


def test_deleting_a_driver_still_in_use_is_refused(client: TestClient) -> None:
    response = client.delete("/api/v1/rig/drivers/desk_dimmer")

    assert response.status_code == 400
    assert "still drives fixture" in response.json()["detail"]


def test_unknown_zone_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/rig/zones/nope").status_code == 404
