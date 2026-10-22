from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3] / "src" / "backend"))

from core.light import LightComponentType, LightFixture
from core.peripheral_type import PeripheralType


def _fixture(**overrides) -> LightFixture:
    defaults = dict(
        id="f",
        name="Fixture",
        component_type=LightComponentType.SINGLE_COLOR,
        component_count=1,
        addressable_group_count=1,
    )
    defaults.update(overrides)
    return LightFixture(**defaults)


def test_single_diode_is_not_individually_addressable() -> None:
    assert _fixture().is_individually_addressable is False


def test_cob_strip_has_many_components_but_one_group() -> None:
    cob_strip = _fixture(component_count=300, addressable_group_count=1)

    assert cob_strip.component_count == 300
    assert cob_strip.is_individually_addressable is False


def test_ws2812_strip_is_individually_addressable() -> None:
    strip = _fixture(
        component_type=LightComponentType.ADDRESSABLE_PIXEL,
        component_count=30,
        addressable_group_count=30,
    )

    assert strip.is_individually_addressable is True


def test_addressable_group_count_cannot_exceed_component_count() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        _fixture(component_count=1, addressable_group_count=30)


@pytest.mark.parametrize("count", [0, -1])
def test_component_count_must_be_positive(count: int) -> None:
    with pytest.raises(ValueError, match="component_count must be >= 1"):
        _fixture(component_count=count)


def test_component_type_maps_to_peripheral_type() -> None:
    assert _fixture().peripheral_type is PeripheralType.WHITE_LED
    assert _fixture(component_type=LightComponentType.RGB).peripheral_type is PeripheralType.RGB_LED
    assert (
        _fixture(component_type=LightComponentType.ADDRESSABLE_PIXEL).peripheral_type
        is PeripheralType.ARGB_LED
    )
