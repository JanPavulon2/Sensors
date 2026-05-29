from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from core.message import Message
from core.node_transport import NodeTransport
from core.primitives import JsonObject


@dataclass(frozen=True)
class NodeLink:
    """Typed connection between two execution nodes."""

    id: UUID
    from_node_id: UUID
    to_node_id: UUID
    transport: NodeTransport


@dataclass(frozen=True)
class NodeMessage:
    """Envelope used when a message crosses node boundaries."""

    connection_id: UUID
    from_node_id: UUID
    to_node_id: UUID
    from_device_id: UUID
    from_port_id: UUID
    to_device_id: UUID
    to_port_id: UUID
    message: Message

    def to_dict(self) -> dict[str, object]:
        return {
            "connection_id": str(self.connection_id),
            "from_node_id": str(self.from_node_id),
            "to_node_id": str(self.to_node_id),
            "from_device_id": str(self.from_device_id),
            "from_port_id": str(self.from_port_id),
            "to_device_id": str(self.to_device_id),
            "to_port_id": str(self.to_port_id),
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
            connection_id=_require_uuid(data, "connection_id"),
            from_node_id=_require_uuid(data, "from_node_id"),
            to_node_id=_require_uuid(data, "to_node_id"),
            from_device_id=_require_uuid(data, "from_device_id"),
            from_port_id=_require_uuid(data, "from_port_id"),
            to_device_id=_require_uuid(data, "to_device_id"),
            to_port_id=_require_uuid(data, "to_port_id"),
            message=Message(
                type=_parse_message_type(message_data),
                name=_require_str(message_data, "name"),
                payload=_require_mapping(message_data, "payload"),
            ),
        )


class NodeMessenger(Protocol):
    async def send(self, packet: NodeMessage) -> None:
        """Deliver a message to another node."""


def _require_uuid(data: dict[str, object], key: str) -> UUID:
    return UUID(_require_str(data, key))


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
