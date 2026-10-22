from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional, Protocol

from core.node_instance import NodeInstance

if TYPE_CHECKING:
    from core.node_link import NodeMessage


class TransportProtocol(Enum):
    WEB_API = auto()
    SOCKET = auto()
    STREAM = auto()
    EVENT = auto()
    MQTT = auto()
    UART = auto()


class NodeTransport(Protocol):
    """Protocol-agnostic transport contract for host -> node message delivery."""

    async def send(
        self,
        destination_node: NodeInstance,
        packet: "NodeMessage",
    ) -> None:
        ...


@dataclass(frozen=True)
class ConnectedNode:
    """Runtime pairing: node instance + selected transport adapter."""

    node_instance: NodeInstance
    transport: Optional[NodeTransport] = None
