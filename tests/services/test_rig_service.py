"""RigService: catalog loading, wiring validation, derived capabilities and
persistence round-trip."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.device_instance import DeviceInstance
from models.domain.remote_zone import RemoteZone
from services.rig_service import RigService, RigValidationError

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
    - id: addressable_data_output
      name: "Addressable data line"
      control_interface: ADDRESSABLE_DATA
      channels: [data]
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
    - id: addressable_strip
      name: "Addressable strip"
      component_type: ADDRESSABLE_PIXEL
      component_count: 30
      addressable_group_count: 30

rig:
  driver_instances:
    - id: desk_dimmer
      definition_id: mosfet_driver_1ch
      node_id: "AA:BB"
      label: "Desk dimmer"
      config:
        channel_pins: {ch0: 23}
  fixture_instances:
    - id: desk_diode
      definition_id: single_diode
      node_id: "AA:BB"
      label: "Desk diode"
      config:
        nominal_color: [255, 170, 80]
        white_profile: WARM
        bindings:
          - {module_instance_id: desk_dimmer, channel_name: ch0, role: SINGLE}
  zones:
    - zone_id: desk
      display_name: "Desk"
      node_id: "AA:BB"
      device_instance_ids: [desk_diode]
      sync_group: workshop
      state: {color: [255, 170, 80], brightness: 70, is_on: true, render_mode: STATIC}
"""


@pytest.fixture
def catalog_path(tmp_path: Path) -> Path:
    path = tmp_path / "rig.yaml"
    path.write_text(CATALOG_YAML)
    return path


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    return tmp_path / "state" / "rig.json"


@pytest.fixture
def rig(catalog_path: Path, state_path: Path) -> RigService:
    return RigService(catalog_path=catalog_path, state_path=state_path)


def test_bootstraps_from_yaml_when_no_state_file_exists(rig: RigService) -> None:
    assert [zone.zone_id for zone in rig.list_zones()] == ["desk"]
    assert rig.get_zone_state("desk").brightness == 70


def test_single_mosfet_diode_reports_only_switch_and_dimming(rig: RigService) -> None:
    """The bug this whole chapter exists for: a MOSFET-dimmed white diode used
    to advertise addressable_pixels and color_control_rgb."""
    capabilities = rig.get_zone_capabilities("desk")

    assert capabilities == {"switch_binary", "dimming"}
    assert "addressable_pixels" not in capabilities
    assert "color_control_rgb" not in capabilities


def test_user_declared_diode_colour_is_preserved(rig: RigService) -> None:
    instance = rig.get_fixture_instance("desk_diode")

    assert instance.config["nominal_color"] == [255, 170, 80]
    assert instance.config["white_profile"] == "WARM"


def test_three_channel_rgb_wiring_yields_colour_control(rig: RigService) -> None:
    rig.upsert_driver_instance(
        DeviceInstance(
            id="rgb_dimmer",
            definition_id="mosfet_driver_3ch",
            node_id="AA:BB",
            label="RGB dimmer",
            config={"channel_pins": {"ch0": 25, "ch1": 26, "ch2": 27}},
        )
    )
    rig.upsert_fixture_instance(
        DeviceInstance(
            id="rgb_strip",
            definition_id="analog_rgb_strip",
            node_id="AA:BB",
            label="RGB strip",
            config={
                "bindings": [
                    {"module_instance_id": "rgb_dimmer", "channel_name": "ch0", "role": "RED"},
                    {"module_instance_id": "rgb_dimmer", "channel_name": "ch1", "role": "GREEN"},
                    {"module_instance_id": "rgb_dimmer", "channel_name": "ch2", "role": "BLUE"},
                ]
            },
        )
    )

    capabilities = rig.get_fixture_instance_capabilities("rgb_strip")

    assert capabilities == {"switch_binary", "dimming", "color_control_rgb"}


def test_binding_to_a_channel_the_driver_does_not_have_is_rejected(rig: RigService) -> None:
    with pytest.raises(RigValidationError, match="no channel 'ch7'"):
        rig.upsert_fixture_instance(
            DeviceInstance(
                id="bad",
                definition_id="single_diode",
                node_id="AA:BB",
                label="Bad",
                config={
                    "bindings": [
                        {"module_instance_id": "desk_dimmer", "channel_name": "ch7", "role": "SINGLE"}
                    ]
                },
            )
        )


def test_fixture_cannot_be_driven_from_a_different_node(rig: RigService) -> None:
    with pytest.raises(RigValidationError, match="cannot be driven from a different node"):
        rig.upsert_fixture_instance(
            DeviceInstance(
                id="remote_fixture",
                definition_id="single_diode",
                node_id="CC:DD",
                label="Elsewhere",
                config={
                    "bindings": [
                        {"module_instance_id": "desk_dimmer", "channel_name": "ch0", "role": "SINGLE"}
                    ]
                },
            )
        )


def test_unknown_fixture_definition_is_rejected(rig: RigService) -> None:
    with pytest.raises(RigValidationError, match="Unknown fixture definition"):
        rig.upsert_fixture_instance(
            DeviceInstance(id="x", definition_id="nope", node_id="AA:BB", label="X")
        )


def test_driver_still_in_use_cannot_be_deleted(rig: RigService) -> None:
    with pytest.raises(RigValidationError, match="still drives fixture"):
        rig.delete_driver_instance("desk_dimmer")


def test_deleting_a_fixture_removes_it_from_its_zone(rig: RigService) -> None:
    rig.delete_fixture_instance("desk_diode")

    assert rig.get_zone("desk").device_instance_ids == []
    assert rig.get_zone_capabilities("desk") == set()


def test_zone_cannot_contain_a_fixture_from_another_node(rig: RigService) -> None:
    rig.upsert_fixture_instance(
        DeviceInstance(id="other", definition_id="single_diode", node_id="CC:DD", label="Other")
    )

    with pytest.raises(RigValidationError, match="is on node CC:DD"):
        rig.upsert_zone(
            RemoteZone(
                zone_id="desk",
                display_name="Desk",
                node_id="AA:BB",
                device_instance_ids=["other"],
            )
        )


def test_state_survives_a_save_and_reload(catalog_path: Path, state_path: Path) -> None:
    rig = RigService(catalog_path=catalog_path, state_path=state_path)
    rig.update_zone_state("desk", brightness=42, is_on=False)
    rig.save_now()

    reloaded = RigService(catalog_path=catalog_path, state_path=state_path)
    state = reloaded.get_zone_state("desk")

    assert state.brightness == 42
    assert state.is_on is False


def test_saved_file_contains_only_the_editable_half(rig: RigService, state_path: Path) -> None:
    rig.save_now()
    saved = json.loads(state_path.read_text())

    assert set(saved) == {"driver_instances", "fixture_instances", "zones"}
    assert "catalog" not in saved
