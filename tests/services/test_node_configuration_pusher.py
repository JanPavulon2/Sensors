"""NodeConfigurationPusher: turning rig wiring into the node.config payload the
firmware needs, so adding a fixture in the UI reaches real hardware."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.device_instance import DeviceInstance
from services.node_configuration_pusher import NodeConfigurationPusher
from services.rig_service import RigService

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
      config: {channel_pins: {ch0: 23}}
  fixture_instances:
    - id: desk_diode
      definition_id: single_diode
      node_id: "AA:BB"
      label: "Desk diode"
      config:
        bindings: [{module_instance_id: desk_dimmer, channel_name: ch0, role: SINGLE}]
  zones: []
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
def pusher(rig: RigService, node_registry: AsyncMock) -> NodeConfigurationPusher:
    return NodeConfigurationPusher(
        rig_service=rig,
        node_registry_service=node_registry,
        remote_zone_state_service=AsyncMock(),
        event_bus=MagicMock(),
    )


def test_single_mosfet_channel_becomes_one_pwm_channel(pusher: NodeConfigurationPusher) -> None:
    configuration = pusher.build_configuration("AA:BB")

    assert configuration["interface"] == "ANALOG_PWM"
    assert configuration["channels"] == [{"role": "SINGLE", "pin": 23}]
    assert configuration["pixel_count"] == 1


def test_three_channel_rgb_wiring_becomes_three_roled_channels(
    rig: RigService, pusher: NodeConfigurationPusher
) -> None:
    rig.upsert_driver_instance(
        DeviceInstance(
            id="rgb_dimmer",
            definition_id="mosfet_driver_3ch",
            node_id="CC:DD",
            label="RGB dimmer",
            config={"channel_pins": {"ch0": 25, "ch1": 26, "ch2": 27}},
        )
    )
    rig.upsert_fixture_instance(
        DeviceInstance(
            id="rgb_strip",
            definition_id="analog_rgb_strip",
            node_id="CC:DD",
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

    configuration = pusher.build_configuration("CC:DD")

    assert configuration["channels"] == [
        {"role": "RED", "pin": 25},
        {"role": "GREEN", "pin": 26},
        {"role": "BLUE", "pin": 27},
    ]


def test_addressable_strip_reports_its_pixel_count(
    rig: RigService, pusher: NodeConfigurationPusher
) -> None:
    rig.upsert_driver_instance(
        DeviceInstance(
            id="strip_output",
            definition_id="addressable_data_output",
            node_id="EE:FF",
            label="Strip output",
            config={"channel_pins": {"data": 4}},
        )
    )
    rig.upsert_fixture_instance(
        DeviceInstance(
            id="strip",
            definition_id="addressable_strip",
            node_id="EE:FF",
            label="Strip",
            config={
                "bindings": [
                    {"module_instance_id": "strip_output", "channel_name": "data", "role": "DATA"}
                ]
            },
        )
    )

    configuration = pusher.build_configuration("EE:FF")

    assert configuration["interface"] == "ADDRESSABLE_DATA"
    assert configuration["pixel_count"] == 30


def test_node_with_nothing_wired_gets_no_configuration(pusher: NodeConfigurationPusher) -> None:
    assert pusher.build_configuration("ZZ:ZZ") is None


def test_version_changes_when_the_wiring_changes(
    rig: RigService, pusher: NodeConfigurationPusher
) -> None:
    before = pusher.build_configuration("AA:BB")["version"]

    rig.upsert_driver_instance(
        DeviceInstance(
            id="desk_dimmer",
            definition_id="mosfet_driver_1ch",
            node_id="AA:BB",
            label="Desk dimmer",
            config={"channel_pins": {"ch0": 19}},
        )
    )
    after = pusher.build_configuration("AA:BB")["version"]

    assert before != after


def test_pushing_sends_the_node_config_command(
    pusher: NodeConfigurationPusher, node_registry: AsyncMock
) -> None:
    assert asyncio.run(pusher.push_configuration("AA:BB")) is True

    node_id, command_name, payload = node_registry.send_command.await_args.args
    assert (node_id, command_name) == ("AA:BB", "node.config")
    assert payload["channels"] == [{"role": "SINGLE", "pin": 23}]


def test_pushing_to_an_unwired_node_is_a_no_op(
    pusher: NodeConfigurationPusher, node_registry: AsyncMock
) -> None:
    assert asyncio.run(pusher.push_configuration("ZZ:ZZ")) is False
    node_registry.send_command.assert_not_awaited()
