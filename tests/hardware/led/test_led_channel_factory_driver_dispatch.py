"""Tests that LedChannelFactory builds the strip its configuration asked for.

Run on a machine with neither rpi_ws281x nor spidev installed, which is exactly
the situation in which the old factory silently handed back a VirtualStrip.
"""

import pytest

from hardware.led import VirtualStrip
from hardware.led.driver_selection import LedDriverUnavailableError
from hardware.led.led_channel_factory import LedChannelFactory


def test_virtual_driver_builds_a_virtual_strip():
    mapping = {"gpio": 18, "color_order": "GRB", "count": 8, "driver": "virtual"}

    strip = LedChannelFactory._create_physical_strip(
        gpio_pin=18, pixel_count=8, mapping=mapping
    )

    assert isinstance(strip, VirtualStrip)
    assert strip.led_count == 8


def test_missing_driver_key_means_ws281x_and_fails_loudly_when_it_is_absent():
    """The Raspberry Pi 4 guarantee, stated as a test.

    hardware.yaml declares no driver, so this mapping must resolve to ws281x.
    On a Pi 4 that constructs a WS281xStrip; here rpi_ws281x does not exist, so
    the factory must say so rather than return a VirtualStrip.
    """
    mapping = {"gpio": 18, "color_order": "BRG", "count": 51}

    with pytest.raises(LedDriverUnavailableError, match="rpi_ws281x"):
        LedChannelFactory._create_physical_strip(
            gpio_pin=18, pixel_count=51, mapping=mapping
        )


def test_spi_driver_without_spidev_also_fails_loudly():
    mapping = {"gpio": 10, "color_order": "GRB", "count": 30, "driver": "spi"}

    with pytest.raises(LedDriverUnavailableError, match="spidev"):
        LedChannelFactory._create_physical_strip(
            gpio_pin=10, pixel_count=30, mapping=mapping
        )
