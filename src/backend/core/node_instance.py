from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class NodeInstance:
    """Concrete runtime instance for a given core Node model."""

    id: UUID
    node_id: UUID
    address: str
    port: int
    capabilities: list[str] = field(default_factory=list)
