from dataclasses import dataclass, field
from uuid import UUID

from core.peripheral_type import PeripheralType
from core.port_definition import PortDefinition


@dataclass(frozen=True)
class Peripheral:
    """Blueprint for a single hardware peripheral class."""

    id: UUID
    name: str
    peripheral_type: PeripheralType
    ports: list[PortDefinition] = field(default_factory=list)
