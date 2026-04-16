from dataclasses import dataclass
from typing import Protocol

from core.message import Message
from core.node import NodeTransport
from core.primitives import (
    ConnectionId,
    DeviceInstanceId,
    JsonObject,
    NodeId,
    NodeLinkId,
    PortName,
    as_connection_id,
    as_device_instance_id,
    as_node_id,
    as_node_link_id,
    as_port_name,
)


@dataclass(frozen=True)
class NodeLink:
    """Typed connection between two execution nodes."""

    id: NodeLinkId
    from_node_id: NodeId
    to_node_id: NodeId
    transport: NodeTransport


@dataclass(frozen=True)
class NodeMessage:
    """Envelope used when a message crosses node boundaries."""

    connection_id: ConnectionId
    from_node_id: NodeId
    to_node_id: NodeId
    from_device_id: DeviceInstanceId
    from_port: PortName
    to_device_id: DeviceInstanceId
    to_port: PortName
    message: Message

    def to_dict(self) -> dict[str, object]:
        return {
            "connection_id": str(self.connection_id),
            "from_node_id": str(self.from_node_id),
            "to_node_id": str(self.to_node_id),
            "from_device_id": str(self.from_device_id),
            "from_port": str(self.from_port),
            "to_device_id": str(self.to_device_id),
            "to_port": str(self.to_port),
            "message": {
                "type": self.message.type.value,
                "name": self.message.name,
                "payload": dict(self.message.payload),
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "NodeMessage":
        message_data = _require_mapping(data, "message")

        return cls(
            connection_id=as_connection_id(_require_str(data, "connection_id")),
            from_node_id=as_node_id(_require_str(data, "from_node_id")),
            to_node_id=as_node_id(_require_str(data, "to_node_id")),
            from_device_id=as_device_instance_id(_require_str(data, "from_device_id")),
            from_port=as_port_name(_require_str(data, "from_port")),
            to_device_id=as_device_instance_id(_require_str(data, "to_device_id")),
            to_port=as_port_name(_require_str(data, "to_port")),
            message=Message(
                type=_parse_message_type(message_data),
                name=_require_str(message_data, "name"),
                payload=_require_mapping(message_data, "payload"),
            ),
        )


class NodeMessenger(Protocol):
    async def send(self, packet: NodeMessage) -> None:
        """Deliver a message to another node."""


def _require_str(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _require_mapping(data: dict[str, object], key: str) -> JsonObject:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value


def _parse_message_type(data: JsonObject):
    from core.message import MessageType

    raw_value = _require_str(data, "type")
    return MessageType(raw_value)
