from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Connection:
    """Connection between two device instance ports."""

    id: UUID
    from_device_id: UUID
    from_port_name: str
    to_device_id: UUID
    to_port_name: str
