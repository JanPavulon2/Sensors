"""The `driver` field has to survive the trip from YAML to the factory.

Without this, hardware.local.yaml could declare `driver: spi` and the factory
would still silently resolve every strip to ws281x.
"""

from hardware.gpio.gpio_manager_mock import MockGPIOManager
from hardware.led.driver_selection import LedDriverName, resolve_driver_name
from managers.hardware_manager import HardwareManager


def _hardware_manager_for(strip_entries: list) -> HardwareManager:
    # HardwareManager parses and registers GPIO in its constructor.
    return HardwareManager(
        data={"led_strips": strip_entries, "buzzers": [], "encoders": [], "buttons": []},
        gpio_manager=MockGPIOManager(),
    )


def test_declared_driver_reaches_the_gpio_to_zones_mapping():
    manager = _hardware_manager_for(
        [
            {
                "id": "AUX_5V",
                "gpio": 10,
                "driver": "spi",
                "type": "WS2812_5V",
                "color_order": "GRB",
                "count": 30,
                "voltage": 5,
            }
        ]
    )

    mapping = manager.get_gpio_to_zones_mapping()[0]

    assert mapping["driver"] == "spi"
    assert resolve_driver_name(mapping, environment={}) == LedDriverName.SPI


def test_strip_without_a_driver_key_still_resolves_to_ws281x():
    """Every entry in the committed hardware.yaml looks like this."""
    manager = _hardware_manager_for(
        [
            {
                "id": "MAIN_12V",
                "gpio": 18,
                "type": "WS2811_12V",
                "color_order": "BRG",
                "count": 51,
                "voltage": 12,
            }
        ]
    )

    mapping = manager.get_gpio_to_zones_mapping()[0]

    assert resolve_driver_name(mapping, environment={}) == LedDriverName.WS281X
