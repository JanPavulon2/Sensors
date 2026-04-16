from dataclasses import dataclass, field
from typing import Mapping, Any


@dataclass(frozen=True)
class DeviceInstance:
    """Concrete deployed device bound to a node and a definition."""

    id: str
    definition_id: str
    node_id: str
    label: str
    config: Mapping[str, Any] = field(default_factory=dict)
