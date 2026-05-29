from dataclasses import dataclass, field
from uuid import UUID

from core.port_definition import PortDefinition


@dataclass(frozen=True)
class DeviceDefinition:
    """Blueprint for a device family/type (ports, semantics, expected config)."""

    id: UUID
    name: str
    ports: tuple[PortDefinition, ...] = field(default_factory=tuple)
