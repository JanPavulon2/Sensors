from __future__ import annotations

from enum import Enum, auto
from typing import NewType, TypeAlias
from uuid import UUID, uuid4

from core.domain.ids import parse_uuid


class AutoNameStrEnum(str, Enum):
    """String enum that derives lowercase values from member names."""

    def _generate_next_value_(name, start, count, last_values):
        return name.lower()


class AutoSnakeStrEnum(str, Enum):
    """String enum that derives snake_case values from member names."""

    def _generate_next_value_(name, start, count, last_values):
        return name.lower()


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

NodeId = NewType("NodeId", UUID)
NodeLinkId = NewType("NodeLinkId", UUID)
DeviceInstanceId = NewType("DeviceInstanceId", UUID)
ConnectionId = NewType("ConnectionId", UUID)
PortId = NewType("PortId", UUID)
PortName = NewType("PortName", str)


def new_node_id() -> NodeId:
    return NodeId(uuid4())


def new_node_link_id() -> NodeLinkId:
    return NodeLinkId(uuid4())


def new_device_instance_id() -> DeviceInstanceId:
    return DeviceInstanceId(uuid4())


def new_connection_id() -> ConnectionId:
    return ConnectionId(uuid4())


def new_port_id() -> PortId:
    return PortId(uuid4())


def as_node_id(value: str | UUID) -> NodeId:
    return NodeId(parse_uuid(value))


def as_node_link_id(value: str | UUID) -> NodeLinkId:
    return NodeLinkId(parse_uuid(value))


def as_device_instance_id(value: str | UUID) -> DeviceInstanceId:
    return DeviceInstanceId(parse_uuid(value))


def as_connection_id(value: str | UUID) -> ConnectionId:
    return ConnectionId(parse_uuid(value))


def as_port_id(value: str | UUID) -> PortId:
    return PortId(parse_uuid(value))


def as_port_name(value: str) -> PortName:
    return PortName(value)
