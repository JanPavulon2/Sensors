from __future__ import annotations

import uuid
from typing import Dict, List, Optional
from uuid import UUID

from core.connection import Connection
from core.device import Device
from core.event_bus import EventBus
from core.message import Message
from core.node import Node, NodeType
from core.node_instance import NodeInstance
from core.node_transport import ConnectedNode, NodeTransport
from core.port import Port


def _to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)


class HostEngine:
    """Host orchestration engine routing messages between local and remote nodes."""

    def __init__(self, host_node_id: UUID | str | None = None):
        self.host_node_id = _to_uuid(host_node_id) if host_node_id else uuid.uuid4()
        self.host_node = Node(
            id=uuid.uuid4(),
            node_type=NodeType.OTHER,
            default_capabilities=["orchestrator"],
        )

        self.devices: Dict[str, Device] = {}
        self.connections: List[Connection] = []
        self.connections_by_source_port: Dict[str, List[Connection]] = {}
        self.port_index: Dict[str, Port] = {}

        self.nodes: Dict[UUID, ConnectedNode] = {}
        self.device_node_index: Dict[str, UUID] = {}

        self.register_node(
            NodeInstance(
                id=self.host_node_id,
                node_id=self.host_node.id,
                address="localhost",
                port=0,
                capabilities=list(self.host_node.default_capabilities),
            )
        )

        self.event_bus = EventBus()
        self.event_bus.subscribe(self._handle)

    def register_node(self, node_instance: NodeInstance, transport: Optional[NodeTransport] = None) -> None:
        self.nodes[node_instance.id] = ConnectedNode(node_instance=node_instance, transport=transport)

    def register_device(self, device: Device, node_id: Optional[UUID | str] = None) -> None:
        assigned_node_id = _to_uuid(node_id) if node_id is not None else self.host_node_id
        if assigned_node_id not in self.nodes:
            raise ValueError(f"Node '{assigned_node_id}' is not registered")

        self.devices[device.id] = device
        self.device_node_index[device.id] = assigned_node_id

        for port in device.ports.values():
            self.port_index[port.id] = port

    def connect(self, source_port: Port, destination_port: Port, connection_id: Optional[UUID | str] = None) -> Connection:
        connection = Connection(
            id=_to_uuid(connection_id) if connection_id is not None else uuid.uuid4(),
            from_device_id=_to_uuid(source_port.device_id),
            from_port=_to_uuid(source_port.id),
            to_device_id=_to_uuid(destination_port.device_id),
            to_port=_to_uuid(destination_port.id),
        )
        self.connections.append(connection)
        source_port_key = str(connection.from_port)
        self.connections_by_source_port.setdefault(source_port_key, []).append(connection)
        return connection

    async def emit(self, source_port: Port, message: Message) -> None:
        await self.event_bus.publish(message, source_port.id)

    async def _handle(self, message: Message, source_port_id: str) -> None:
        for connection in self.connections_by_source_port.get(source_port_id, []):
            await self._deliver(connection, message)

    async def _deliver(self, connection: Connection, message: Message) -> None:
        destination_port = self.port_index.get(str(connection.to_port))
        if destination_port is None:
            return

        destination_device_key = str(connection.to_device_id)
        destination_node_id = self.device_node_index.get(destination_device_key, self.host_node_id)

        if destination_node_id == self.host_node_id and destination_device_key in self.devices:
            destination_device = self.devices[destination_device_key]
            output_messages = await destination_device.handle_message(destination_port, message)
            for output_port_id, output_message in output_messages:
                await self.event_bus.publish(output_message, output_port_id)
            return

        connected_node = self.nodes.get(destination_node_id)
        if connected_node is None or connected_node.transport is None:
            return

        await connected_node.transport.send(
            connected_node.node_instance,
            destination_device_key,
            str(connection.to_port),
            message,
        )

    async def start(self) -> None:
        await self.event_bus.run()
