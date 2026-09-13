"""How a light is physically driven by its node.

One of the three axes in docs/architecture-vnext/03-led-taxonomy.md, and listed
under Core in 01-naming-convention.md. Deliberately separate from:
- LightComponentType / LightFixture (what emits the light)
- CommunicationProtocol / TransportProtocol (how data reaches the node)

Keep in sync with 03-led-taxonomy.md.
"""

from __future__ import annotations

from enum import Enum, auto


class HardwareControlInterface(Enum):
    """Electrical control method a driver module uses for its outputs."""

    # One PWM duty cycle per channel (MOSFET dimmer boards). Brightness only
    # per channel - colour is only possible by combining channels (3x for RGB).
    ANALOG_PWM = auto()

    # Serial per-pixel data line (WS281x-like). Every pixel individually
    # addressable with its own colour.
    ADDRESSABLE_DATA = auto()

    # Regulated constant-current driver (COB / high-power modules). Like
    # ANALOG_PWM from the host's point of view: brightness per channel.
    CONSTANT_CURRENT_DRIVER = auto()


# Interfaces whose channels expose a continuously variable output rather than a
# plain on/off. Used by capability derivation to decide on "dimming".
DIMMABLE_CONTROL_INTERFACES: frozenset[HardwareControlInterface] = frozenset(
    {
        HardwareControlInterface.ANALOG_PWM,
        HardwareControlInterface.ADDRESSABLE_DATA,
        HardwareControlInterface.CONSTANT_CURRENT_DRIVER,
    }
)
