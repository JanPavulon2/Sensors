from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3] / "src" / "backend"))

from core.device import Device
from core.host_engine import HostEngine
from core.message import Message, MessageType
from core.node import Node, NodeType
from core.node_instance import NodeInstance
from core.port import PortDirection


class RecordingDevice(Device):
    def __init__(self, name: str):
        super().__init__(name)
        self.received = []

    async def handle_message(self, port, message):
        self.received.append((port.id, message.name))
        return []


class TransportSpy:
    def __init__(self):
        self.calls = []

    async def send(self, destination_node, packet):
        self.calls.append((destination_node.id, packet.to_device_id, packet.to_port_id, packet.message.name))


def test_register_device_rejects_unknown_node() -> None:
    host_engine = HostEngine()
    sensor_device = Device("sensor")

    with pytest.raises(ValueError):
        host_engine.register_device(sensor_device, node_id=uuid4())


def test_connect_creates_uuid_based_connection_and_indexes_source_port() -> None:
    host_engine = HostEngine()

    source_device = Device("source")
    source_output_port = source_device.add_port("output", PortDirection.OUTPUT)
    host_engine.register_device(source_device)

    destination_device = Device("destination")
    destination_input_port = destination_device.add_port("input", PortDirection.INPUT)
    host_engine.register_device(destination_device)

    connection = host_engine.connect(source_output_port, destination_input_port)

    assert isinstance(connection.id, UUID)
    assert connection.from_port == source_output_port.id
    assert connection.to_port == destination_input_port.id
    assert connection.from_port in host_engine.connections_by_source_port


def test_handle_routes_to_local_host_device() -> None:
    host_engine = HostEngine()

    source_device = Device("source")
    source_output_port = source_device.add_port("output", PortDirection.OUTPUT)
    host_engine.register_device(source_device)

    destination_device = RecordingDevice("destination")
    destination_input_port = destination_device.add_port("input", PortDirection.INPUT)
    host_engine.register_device(destination_device)

    host_engine.connect(source_output_port, destination_input_port)

    ping_message = Message(type=MessageType.EVENT, name="ping")
    asyncio.run(host_engine._handle(ping_message, source_output_port.id))

    assert destination_device.received == [(destination_input_port.id, "ping")]


def test_handle_forwards_to_remote_node_transport() -> None:
    host_engine = HostEngine()

    remote_node = Node(id=uuid4(), node_type=NodeType.ESP32)
    remote_node_instance = NodeInstance(
        id=uuid4(),
        node_id=remote_node.id,
        address="10.0.0.10",
        port=9000,
        capabilities=["render_output"],
    )
    transport_spy = TransportSpy()
    host_engine.register_node(remote_node_instance, transport=transport_spy)

    source_device = Device("source")
    source_output_port = source_device.add_port("output", PortDirection.OUTPUT)
    host_engine.register_device(source_device)

    remote_destination_device = Device("remote_destination")
    remote_destination_input_port = remote_destination_device.add_port("input", PortDirection.INPUT)
    host_engine.register_device(remote_destination_device, node_id=remote_node_instance.id)

    host_engine.connect(source_output_port, remote_destination_input_port)

    frame_message = Message(type=MessageType.EVENT, name="frame")
    asyncio.run(host_engine._handle(frame_message, source_output_port.id))

    assert len(transport_spy.calls) == 1
    destination_node_id, destination_device_id, destination_port_id, message_name = transport_spy.calls[0]
    assert destination_node_id == remote_node_instance.id
    assert destination_device_id == remote_destination_device.id
    assert destination_port_id == remote_destination_input_port.id
    assert message_name == "frame"
