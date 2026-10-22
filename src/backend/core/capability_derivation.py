"""Derives device capabilities from what the hardware actually is.

Replaces the hardcoded ESP32_LED_STRIP_DEVICE_CAPABILITIES list that used to
claim every ESP32 drove an addressable RGB strip. Capability is "what this can
do" (04-capabilities.md); it follows from the driver module's control interface
crossed with the fixture's component type and channel bindings, so it should be
computed, never declared by hand.

Every string produced here must exist in DEVICE_CAPABILITIES (core/capabilities.py).
"""

from __future__ import annotations

from typing import Iterable, Sequence

from core.capabilities import DEVICE_CAPABILITIES
from core.hardware_control_interface import DIMMABLE_CONTROL_INTERFACES
from core.light import (
    COLOUR_CHANNEL_ROLES,
    ChannelBinding,
    ChannelRole,
    LightComponentType,
    LightFixture,
)
from core.module import Module


def derive_fixture_capabilities(
    fixture: LightFixture,
    module: Module,
    bindings: Sequence[ChannelBinding],
) -> set[str]:
    """Capabilities of one fixture driven by one module over the given channels."""
    capabilities: set[str] = {"switch_binary"}

    if module.control_interface in DIMMABLE_CONTROL_INTERFACES:
        capabilities.add("dimming")

    bound_roles = {binding.role for binding in bindings}
    bound_colour_channel_count = len(bound_roles & COLOUR_CHANNEL_ROLES)

    if fixture.component_type is LightComponentType.RGB:
        if bound_colour_channel_count >= 3:
            capabilities.add("color_control_rgb")

    elif fixture.component_type is LightComponentType.RGBW:
        if bound_colour_channel_count >= 3 and ChannelRole.WHITE in bound_roles:
            capabilities.add("color_control_rgbw")
        elif bound_colour_channel_count >= 3:
            # Wired for colour but the dedicated white channel is missing, so
            # it behaves as a plain RGB fixture.
            capabilities.add("color_control_rgb")

    elif fixture.component_type is LightComponentType.ADDRESSABLE_PIXEL:
        # Each pixel carries its own RGB value over the data line - colour does
        # not depend on how many driver channels are bound.
        capabilities.add("color_control_rgb")
        if fixture.is_individually_addressable:
            capabilities.add("addressable_pixels")

    _assert_known(capabilities)
    return capabilities


def derive_zone_capabilities(fixture_capabilities: Iterable[set[str]]) -> set[str]:
    """A zone drives all its fixtures with one shared state, so it can only
    offer what every one of them supports - hence the intersection.

    An empty zone has no capabilities (not "all of them").
    """
    capability_sets = list(fixture_capabilities)
    if not capability_sets:
        return set()
    return set.intersection(*(set(capabilities) for capabilities in capability_sets))


def _assert_known(capabilities: set[str]) -> None:
    unknown = capabilities - DEVICE_CAPABILITIES
    if unknown:
        raise ValueError(
            f"Derived capabilities not present in the DEVICE_CAPABILITIES vocabulary: "
            f"{sorted(unknown)}. Add them to core/capabilities.py and 04-capabilities.md first."
        )
