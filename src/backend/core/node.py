from dataclasses import dataclass, field
from enum import Enum


class NodeKind(str, Enum):
    PI = "pi"
    ESP32 = "esp32"
    BROWSER = "browser"
    OTHER = "other"


@dataclass(frozen=True)
class Node:
    """Execution node where one or more device instances run."""

    id: str
    kind: NodeKind
    address: str
    port: int
    capabilities: tuple[str, ...] = field(default_factory=tuple)
