# =========================================================
# core/runtime.py
# =========================================================

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol

from core.connection import Connection
from core.device import Device
from core.event_bus import EventBus
from core.message import Message
from core.node import Node, NodeKind
from core.port import Port


class NodeTransport(Protocol):
    """Transport adapter used by host runtime to deliver messages to remote nodes."""

    async def send(self, node: Node, device_id: str, port_id: str, message: Message) -> None:
        ...


@dataclass(frozen=True)
class RegisteredNode:
    node: Node
    transport: Optional[NodeTransport] = None


class Runtime:
    """
    Host runtime that routes messages between local devices and remote-node devices.

    - Local devices are handled in-process via Device.handle_message().
    - Remote devices are forwarded to a node-specific transport adapter.
    """

    def __init__(self, host_node_id: str = "host"):
        self.host_node_id = host_node_id

        self.devices: Dict[str, Device] = {}
        self.connections: List[Connection] = []
        self.connections_from: Dict[str, List[Connection]] = {}
        self.port_index: Dict[str, Port] = {}

        self.nodes: Dict[str, RegisteredNode] = {}
        self.device_node_index: Dict[str, str] = {}

        # Register host as a logical node (separate from physical render nodes)
        self.register_node(
            Node(
                id=self.host_node_id,
                kind=NodeKind.OTHER,
                address="localhost",
                port=0,
                capabilities=("orchestrator",),
            )
        )

        self.bus = EventBus()
        self.bus.subscribe(self._handle)

    def register_node(self, node: Node, transport: Optional[NodeTransport] = None) -> None:
        self.nodes[node.id] = RegisteredNode(node=node, transport=transport)

    def register_device(self, device: Device, node_id: Optional[str] = None) -> None:
        assigned_node_id = node_id or self.host_node_id
        if assigned_node_id not in self.nodes:
            raise ValueError(f"Node '{assigned_node_id}' is not registered")

        self.devices[device.id] = device
        self.device_node_index[device.id] = assigned_node_id

        for port in device.ports.values():
            self.port_index[port.id] = port

    def connect(self, from_port: Port, to_port: Port, connection_id: Optional[str] = None) -> Connection:
        conn = Connection(
            id=connection_id or str(uuid.uuid4()),
            from_device_id=from_port.device_id,
            from_port=from_port.id,
            to_device_id=to_port.device_id,
            to_port=to_port.id,
        )
        self.connections.append(conn)
        self.connections_from.setdefault(conn.from_port, []).append(conn)
        return conn

    async def emit(self, port: Port, message: Message) -> None:
        await self.bus.publish(message, port.id)

    async def _handle(self, message: Message, port_id: str) -> None:
        for conn in self.connections_from.get(port_id, []):
            await self._deliver(conn, message)

    async def _deliver(self, conn: Connection, message: Message) -> None:
        target_port = self.port_index.get(conn.to_port)
        if target_port is None:
            return

        node_id = self.device_node_index.get(conn.to_device_id, self.host_node_id)

        if node_id == self.host_node_id and conn.to_device_id in self.devices:
            device = self.devices[conn.to_device_id]
            outputs = await device.handle_message(target_port, message)
            for out_port_id, out_msg in outputs:
                await self.bus.publish(out_msg, out_port_id)
            return

        registered_node = self.nodes.get(node_id)
        if registered_node is None or registered_node.transport is None:
            return

        await registered_node.transport.send(
            registered_node.node,
            conn.to_device_id,
            conn.to_port,
            message,
        )

    async def start(self) -> None:
        await self.bus.run()
