"""Module - the middle aggregate level from 01-naming-convention.md.

A Module is a hardware block composed of several Peripherals ("zlozony blok
hardware z kilku peripheral"). A MOSFET dimmer board is a Module composed of
one or more MOSFET_CHANNEL Peripherals; a WS281x output is a Module with a
single DATA-carrying channel.

This is what makes "the driver module is physically a separate device from the
diode it drives" expressible: the Module describes the driver, LightFixture
(core/light.py) describes the light, and ChannelBinding links them.

Module is a BLUEPRINT, like Peripheral and DeviceDefinition - it describes a
type of board, not a deployed one. The deployed board is a DeviceInstance whose
definition_id names this module and whose `config` carries the deployment facts
(which node, which GPIO pin per channel). See core/device_instance.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.hardware_control_interface import HardwareControlInterface
from core.peripheral import Peripheral


@dataclass(frozen=True)
class Module:
    """Blueprint for a hardware block composed of several peripherals."""

    id: str
    name: str
    control_interface: HardwareControlInterface
    peripherals: tuple[Peripheral, ...] = field(default_factory=tuple)

    @property
    def channel_count(self) -> int:
        return len(self.peripherals)

    def channel_names(self) -> tuple[str, ...]:
        return tuple(peripheral.name for peripheral in self.peripherals)

    def has_channel(self, channel_name: str) -> bool:
        return any(peripheral.name == channel_name for peripheral in self.peripherals)

    def find_channel(self, channel_name: str) -> Peripheral | None:
        for peripheral in self.peripherals:
            if peripheral.name == channel_name:
                return peripheral
        return None
