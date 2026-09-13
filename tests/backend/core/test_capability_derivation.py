"""Capability derivation across every hardware shape the rig model supports.

These are the cases from docs/architecture-vnext/03-led-taxonomy.md, plus the
one that started this chapter: a single MOSFET-dimmed diode must NOT report
addressable_pixels or color_control_rgb.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3] / "src" / "backend"))

from core.capability_derivation import derive_fixture_capabilities, derive_zone_capabilities
from core.hardware_control_interface import HardwareControlInterface
from core.light import ChannelBinding, ChannelRole, LightComponentType, LightFixture
from core.module import Module
from core.peripheral import Peripheral
from core.peripheral_type import PeripheralType


def _module(control_interface: HardwareControlInterface, channel_names: list[str]) -> Module:
    peripheral_type = (
        PeripheralType.MOSFET_CHANNEL
        if control_interface is HardwareControlInterface.ANALOG_PWM
        else PeripheralType.ARGB_LED
    )
    return Module(
        id="m",
        name="Module",
        control_interface=control_interface,
        peripherals=tuple(
            Peripheral(id=name, name=name, peripheral_type=peripheral_type)
            for name in channel_names
        ),
    )


def _bindings(*roles: ChannelRole) -> list[ChannelBinding]:
    return [
        ChannelBinding(module_instance_id="mi", channel_name=f"ch{index}", role=role)
        for index, role in enumerate(roles)
    ]


def test_single_diode_on_one_mosfet_channel() -> None:
    """The actual hardware on this desk. Brightness only - no colour, no pixels."""
    fixture = LightFixture(id="f", name="Desk diode", component_type=LightComponentType.SINGLE_COLOR)
    module = _module(HardwareControlInterface.ANALOG_PWM, ["ch0"])

    capabilities = derive_fixture_capabilities(fixture, module, _bindings(ChannelRole.SINGLE))

    assert capabilities == {"switch_binary", "dimming"}


def test_cob_white_strip_on_one_mosfet_channel() -> None:
    """Hundreds of LEDs, still one dimmer - same capabilities as a single diode."""
    fixture = LightFixture(
        id="f",
        name="COB strip",
        component_type=LightComponentType.SINGLE_COLOR,
        component_count=300,
        addressable_group_count=1,
    )
    module = _module(HardwareControlInterface.ANALOG_PWM, ["ch0"])

    capabilities = derive_fixture_capabilities(fixture, module, _bindings(ChannelRole.SINGLE))

    assert capabilities == {"switch_binary", "dimming"}
    assert "addressable_pixels" not in capabilities


def test_analog_rgb_strip_on_three_mosfet_channels() -> None:
    """Real colour control without any addressable data line."""
    fixture = LightFixture(
        id="f",
        name="Analog RGB strip",
        component_type=LightComponentType.RGB,
        component_count=150,
        addressable_group_count=1,
    )
    module = _module(HardwareControlInterface.ANALOG_PWM, ["ch0", "ch1", "ch2"])

    capabilities = derive_fixture_capabilities(
        fixture, module, _bindings(ChannelRole.RED, ChannelRole.GREEN, ChannelRole.BLUE)
    )

    assert capabilities == {"switch_binary", "dimming", "color_control_rgb"}
    assert "addressable_pixels" not in capabilities


def test_rgb_fixture_with_only_two_channels_bound_loses_colour() -> None:
    fixture = LightFixture(id="f", name="Half-wired RGB", component_type=LightComponentType.RGB)
    module = _module(HardwareControlInterface.ANALOG_PWM, ["ch0", "ch1"])

    capabilities = derive_fixture_capabilities(
        fixture, module, _bindings(ChannelRole.RED, ChannelRole.GREEN)
    )

    assert capabilities == {"switch_binary", "dimming"}


def test_rgbw_needs_a_dedicated_white_channel() -> None:
    fixture = LightFixture(id="f", name="RGBW strip", component_type=LightComponentType.RGBW)
    module = _module(HardwareControlInterface.ANALOG_PWM, ["ch0", "ch1", "ch2", "ch3"])

    with_white = derive_fixture_capabilities(
        fixture,
        module,
        _bindings(ChannelRole.RED, ChannelRole.GREEN, ChannelRole.BLUE, ChannelRole.WHITE),
    )
    without_white = derive_fixture_capabilities(
        fixture, module, _bindings(ChannelRole.RED, ChannelRole.GREEN, ChannelRole.BLUE)
    )

    assert "color_control_rgbw" in with_white
    assert without_white == {"switch_binary", "dimming", "color_control_rgb"}


def test_ws2812_strip() -> None:
    fixture = LightFixture(
        id="f",
        name="WS2812 strip",
        component_type=LightComponentType.ADDRESSABLE_PIXEL,
        component_count=30,
        addressable_group_count=30,
    )
    module = _module(HardwareControlInterface.ADDRESSABLE_DATA, ["data"])

    capabilities = derive_fixture_capabilities(fixture, module, _bindings(ChannelRole.DATA))

    assert capabilities == {"switch_binary", "dimming", "color_control_rgb", "addressable_pixels"}


def test_single_ws2812_pixel_has_colour_but_is_not_addressable() -> None:
    """One pixel is individually coloured but there is nothing to address."""
    fixture = LightFixture(
        id="f",
        name="Single pixel",
        component_type=LightComponentType.ADDRESSABLE_PIXEL,
        component_count=1,
        addressable_group_count=1,
    )
    module = _module(HardwareControlInterface.ADDRESSABLE_DATA, ["data"])

    capabilities = derive_fixture_capabilities(fixture, module, _bindings(ChannelRole.DATA))

    assert capabilities == {"switch_binary", "dimming", "color_control_rgb"}


def test_zone_capabilities_are_the_intersection_of_its_fixtures() -> None:
    rgb_strip = {"switch_binary", "dimming", "color_control_rgb"}
    plain_diode = {"switch_binary", "dimming"}

    assert derive_zone_capabilities([rgb_strip, plain_diode]) == {"switch_binary", "dimming"}


def test_empty_zone_has_no_capabilities() -> None:
    assert derive_zone_capabilities([]) == set()
