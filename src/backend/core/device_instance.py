from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import UUID


@dataclass(frozen=True)
class DeviceInstance:
    """Concrete deployed device bound to a node and a definition."""

    id: UUID
    definition_id: UUID
    node_id: UUID
    label: str
    config: Mapping[str, Any] = field(default_factory=dict)
