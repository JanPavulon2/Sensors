from dataclasses import dataclass, field
from enum import Enum, auto
from uuid import UUID


class NodeType(Enum):
    ESP32 = auto()
    RASPBERRY_PI_4 = auto()
    RASPBERRY_PI_5 = auto()
    FRONTEND_RUNTIME = auto()
    OTHER = auto()


@dataclass(frozen=True)
class Node:
    """Core node model (type/profile), reused by NodeInstance."""

    id: UUID
    node_type: NodeType
    default_capabilities: list[str] = field(default_factory=list)
