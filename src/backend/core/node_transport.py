from __future__ import annotations

import json
from typing import TYPE_CHECKING, Awaitable, Callable, Protocol, runtime_checkable

from core.node_link import NodeMessage, NodeMessenger
from core.node import NodeTransport

if TYPE_CHECKING:
    from core.runtime import Runtime
    from core.node_link import NodeLink


class NodePacketCodec(Protocol):
    def encode(self, packet: NodeMessage) -> bytes:
        """Serialize a node message for transport."""

    def decode(self, payload: bytes) -> NodeMessage:
        """Deserialize a node message from transport bytes."""


class NodePacketChannel(Protocol):
    async def send(self, payload: bytes) -> None:
        """Send raw bytes across a transport."""

    def set_receiver(
        self,
        receiver: Callable[[bytes], Awaitable[None]],
    ) -> None:
        """Register the callback invoked for inbound bytes."""


@runtime_checkable
class ManagedNodePacketChannel(NodePacketChannel, Protocol):
    async def start(self) -> None:
        """Start background transport resources."""

    async def stop(self) -> None:
        """Stop background transport resources."""


class JsonNodePacketCodec:
    """Transport-neutral JSON codec for cross-node messages."""

    def encode(self, packet: NodeMessage) -> bytes:
        return json.dumps(packet.to_dict()).encode("utf-8")

    def decode(self, payload: bytes) -> NodeMessage:
        return NodeMessage.from_dict(json.loads(payload.decode("utf-8")))


class ChannelNodeMessenger(NodeMessenger):
    """Adapts any byte channel into the NodeMessenger protocol."""

    def __init__(
        self,
        channel: NodePacketChannel,
        codec: NodePacketCodec,
    ):
        self._channel = channel
        self._codec = codec

    async def send(self, packet: NodeMessage) -> None:
        await self._channel.send(self._codec.encode(packet))


class NodeTransportBinding:
    """Wires a byte channel to encode outbound and decode inbound packets."""

    def __init__(
        self,
        channel: NodePacketChannel,
        codec: NodePacketCodec,
        inbound_handler: Callable[[NodeMessage], Awaitable[None]],
    ):
        self._channel = channel
        self._codec = codec
        self._inbound_handler = inbound_handler
        self._channel.set_receiver(self._receive)

    @property
    def messenger(self) -> NodeMessenger:
        return ChannelNodeMessenger(self._channel, self._codec)

    async def start(self) -> None:
        if isinstance(self._channel, ManagedNodePacketChannel):
            await self._channel.start()

    async def stop(self) -> None:
        if isinstance(self._channel, ManagedNodePacketChannel):
            await self._channel.stop()

    async def _receive(self, payload: bytes) -> None:
        await self._inbound_handler(self._codec.decode(payload))


class NodeTransportPlugin(Protocol):
    transport: NodeTransport

    def bind(
        self,
        runtime: "Runtime",
        link: "NodeLink",
    ) -> NodeTransportBinding:
        """Create and bind the transport for one node link."""


class InMemoryNodeChannel:
    """Simple channel pair for tests and local development."""

    def __init__(self):
        self._peer: "InMemoryNodeChannel | None" = None
        self._receiver: Callable[[bytes], Awaitable[None]] | None = None

    def attach_peer(self, peer: "InMemoryNodeChannel") -> None:
        self._peer = peer

    def set_receiver(
        self,
        receiver: Callable[[bytes], Awaitable[None]],
    ) -> None:
        self._receiver = receiver

    async def send(self, payload: bytes) -> None:
        if self._peer is None or self._peer._receiver is None:
            raise ValueError("In-memory channel is not connected")

        await self._peer._receiver(payload)


def create_in_memory_channel_pair() -> tuple[InMemoryNodeChannel, InMemoryNodeChannel]:
    left = InMemoryNodeChannel()
    right = InMemoryNodeChannel()
    left.attach_peer(right)
    right.attach_peer(left)
    return left, right
