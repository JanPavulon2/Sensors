"""
Which driver renders a strip - decided, not guessed.
====================================================
Previously LedChannelFactory asked `RuntimeInfo.has_ws281x()` and silently
substituted a VirtualStrip when the answer was no. An application that had
quietly stopped driving any hardware still started up looking healthy, which is
exactly how a Raspberry Pi 5 spent months appearing to render to LEDs that were
never lit.

So the driver is now declared per strip in the hardware configuration and a
declared driver that cannot be loaded is a startup failure. VirtualStrip is
still available - but only to someone who asked for it by name.

Kept apart from led_channel_factory so the decision is a pure function: it can
be tested without rpi_ws281x, without spidev and without a Raspberry Pi.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Callable, Dict, Mapping, Optional

# Environment variable that forces one driver for every strip, whatever the
# configuration says. Intended for working on a PC or under WSL, where no
# hardware exists at all.
LED_DRIVER_ENVIRONMENT_VARIABLE = "DIUNA_LED_DRIVER"

# Key a strip's hardware mapping uses to declare its driver. Absent means
# ws281x, which is what every entry in the committed hardware.yaml relies on.
LED_DRIVER_MAPPING_KEY = "driver"


class LedDriverName(StrEnum):
    WS281X = "ws281x"
    SPI = "spi"
    VIRTUAL = "virtual"


class LedDriverUnavailableError(RuntimeError):
    """A driver was declared in configuration but its Python module is missing."""


# Python module each driver needs before it can be constructed. VirtualStrip
# needs nothing, so it is absent here and always considered available.
REQUIRED_MODULE_BY_DRIVER: Dict[LedDriverName, str] = {
    LedDriverName.WS281X: "rpi_ws281x",
    LedDriverName.SPI: "spidev",
}

INSTALL_HINT_BY_DRIVER: Dict[LedDriverName, str] = {
    LedDriverName.WS281X: "pip install rpi_ws281x (Raspberry Pi 4 and earlier only)",
    LedDriverName.SPI: "sudo apt install python3-spidev, or pip install spidev",
}


def _parse_driver_name(raw_value: str) -> LedDriverName:
    try:
        return LedDriverName(raw_value.strip().lower())
    except ValueError:
        supported = ", ".join(driver.value for driver in LedDriverName)
        raise ValueError(
            f"Unknown LED driver '{raw_value}'. Supported drivers: {supported}"
        ) from None


def resolve_driver_name(
    mapping: Mapping[str, object],
    environment: Mapping[str, str],
) -> LedDriverName:
    """Decide which driver a single strip mapping should be rendered by.

    The environment override wins over configuration, because its whole purpose
    is to run somewhere the configured hardware does not exist.
    """
    override = environment.get(LED_DRIVER_ENVIRONMENT_VARIABLE)
    if override:
        return _parse_driver_name(override)

    declared = mapping.get(LED_DRIVER_MAPPING_KEY)
    if declared is None:
        return LedDriverName.WS281X

    return _parse_driver_name(str(declared))


def verify_driver_available(
    driver_name: LedDriverName,
    module_is_available: Callable[[str], bool],
) -> None:
    """Raise if the declared driver's module cannot be imported.

    Never substitutes another driver - that substitution is the bug this module
    exists to prevent.
    """
    required_module: Optional[str] = REQUIRED_MODULE_BY_DRIVER.get(driver_name)
    if required_module is None:
        return

    if module_is_available(required_module):
        return

    hint = INSTALL_HINT_BY_DRIVER.get(driver_name, "")
    raise LedDriverUnavailableError(
        f"LED driver '{driver_name.value}' is configured but its module "
        f"'{required_module}' is not installed, so nothing would be rendered to "
        f"real hardware. Install it ({hint}), correct the 'driver' field in the "
        f"hardware configuration, or set {LED_DRIVER_ENVIRONMENT_VARIABLE}=virtual "
        f"to run without hardware on purpose."
    )
