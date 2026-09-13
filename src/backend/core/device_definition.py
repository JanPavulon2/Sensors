from dataclasses import dataclass, field

from core.port_definition import PortDefinition


@dataclass(frozen=True)
class DeviceDefinition:
    """Blueprint for a device family/type (ports, semantics, expected config).

    `id` is a readable slug ("mosfet_driver_1ch", "single_diode"), matching
    DeviceInstance.definition_id - this is the catalog the add/edit UI picks
    from, so its ids are authored, not generated.
    """

    id: str
    name: str
    ports: tuple[PortDefinition, ...] = field(default_factory=tuple)
