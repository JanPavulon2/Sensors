from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

import httpx

sys.path.append(str(Path(__file__).resolve().parents[3] / "src" / "backend"))

from core.http_node_transport import HttpNodeTransport
from core.message import Message, MessageType
from core.node_instance import NodeInstance
from core.node_link import NodeMessage


def _make_packet(message: Message) -> NodeMessage:
    return NodeMessage(
        connection_id=uuid4(),
        from_node_id=uuid4(),
        to_node_id=uuid4(),
        from_device_id=uuid4(),
        from_port_id=uuid4(),
        to_device_id=uuid4(),
        to_port_id=uuid4(),
        message=message,
    )


def test_send_posts_command_to_node_address_and_port() -> None:
    captured_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"status": "ok"})

    transport = HttpNodeTransport(shared_secret="test-secret")
    transport._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    destination = NodeInstance(id=uuid4(), node_id=uuid4(), address="10.0.0.5", port=8080)
    packet = _make_packet(Message(type=MessageType.COMMAND, name="identify", payload={"a": 1}))

    asyncio.run(transport.send(destination, packet))

    assert len(captured_requests) == 1
    request = captured_requests[0]
    assert str(request.url) == "http://10.0.0.5:8080/command"
    assert request.headers["x-node-secret"] == "test-secret"


def test_send_swallows_http_errors_instead_of_raising() -> None:
    # send() runs inside HostEngine's single shared consumer loop, which has
    # no exception handling of its own - one node's delivery failure must
    # never propagate and kill command delivery to every other node.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = HttpNodeTransport(shared_secret="test-secret")
    transport._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    destination = NodeInstance(id=uuid4(), node_id=uuid4(), address="10.0.0.5", port=8080)
    packet = _make_packet(Message(type=MessageType.COMMAND, name="identify"))

    asyncio.run(transport.send(destination, packet))  # must not raise


def test_send_swallows_connection_errors_instead_of_raising() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = HttpNodeTransport(shared_secret="test-secret")
    transport._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    destination = NodeInstance(id=uuid4(), node_id=uuid4(), address="10.0.0.5", port=8080)
    packet = _make_packet(Message(type=MessageType.COMMAND, name="identify"))

    asyncio.run(transport.send(destination, packet))  # must not raise
