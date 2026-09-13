"""Tests for which output driver a strip mapping resolves to.

This is the guard on the promise that a Raspberry Pi 4 checkout keeps behaving
exactly as it did: hardware.yaml carries no `driver` key, so absence must mean
rpi_ws281x, and a driver that was asked for but cannot be loaded must fail
loudly rather than quietly degrade to a VirtualStrip - the silent fallback that
previously made a Pi 5 look like it was driving real LEDs when it was not.
"""

import pytest

from hardware.led.driver_selection import (
    LedDriverName,
    LedDriverUnavailableError,
    resolve_driver_name,
    verify_driver_available,
)


def test_mapping_without_a_driver_key_resolves_to_ws281x():
    """hardware.yaml on the Pi 4 has no `driver` field anywhere."""
    mapping = {"gpio": 18, "color_order": "BRG", "count": 51}

    assert resolve_driver_name(mapping, environment={}) == LedDriverName.WS281X


def test_mapping_can_declare_the_spi_driver():
    mapping = {"gpio": 10, "color_order": "GRB", "count": 30, "driver": "spi"}

    assert resolve_driver_name(mapping, environment={}) == LedDriverName.SPI


def test_environment_override_forces_virtual_for_every_strip():
    """The documented escape hatch for working on a PC or under WSL."""
    mapping = {"gpio": 18, "color_order": "BRG", "count": 51}

    resolved = resolve_driver_name(mapping, environment={"DIUNA_LED_DRIVER": "virtual"})

    assert resolved == LedDriverName.VIRTUAL


def test_unknown_driver_name_is_rejected():
    mapping = {"gpio": 18, "driver": "neopixel_over_carrier_pigeon"}

    with pytest.raises(ValueError, match="neopixel_over_carrier_pigeon"):
        resolve_driver_name(mapping, environment={})


def test_declared_driver_that_cannot_be_loaded_raises_instead_of_falling_back():
    """The whole point: no VirtualStrip unless VirtualStrip was asked for."""
    with pytest.raises(LedDriverUnavailableError, match="rpi_ws281x"):
        verify_driver_available(LedDriverName.WS281X, module_is_available=lambda name: False)


def test_virtual_driver_is_always_available():
    verify_driver_available(LedDriverName.VIRTUAL, module_is_available=lambda name: False)
