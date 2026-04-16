from dataclasses import dataclass, field

from core.port_definition import PortDefinition


@dataclass(frozen=True)
class DeviceDefinition:
    """Blueprint for a device family/type (ports, semantics, expected config)."""

    id: str
    name: str
    ports: tuple[PortDefinition, ...] = field(default_factory=tuple)
