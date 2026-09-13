from __future__ import annotations

import httpx

from core.node_instance import NodeInstance
from core.node_link import NodeMessage
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.API)

HTTP_COMMAND_TIMEOUT_SECONDS = 3.0


class HttpNodeTransport:
    """Concrete NodeTransport that POSTs commands to a node's HTTP command
    server. Implements the `NodeTransport` Protocol (core/node_transport.py)
    under TransportProtocol.WEB_API - the RPi push side of Phase 4's "RPi5
    sends commands" (the ESP32 side is the WebServer added to
    firmware/firmware/src/main.cpp).

    send() deliberately swallows delivery failures (logs and returns) rather
    than raising: it runs inside HostEngine's single shared message-queue
    consumer loop (core/event_bus.py's `run()`, no try/except of its own), so
    letting an exception escape here - e.g. one unreachable/offline ESP32 -
    would kill that loop forever, silently breaking command delivery to
    *every* node for the rest of the process's life. A dropped command to one
    node must never take down delivery to the others.
    """

    def __init__(self, shared_secret: str):
        self._shared_secret = shared_secret
        self._client = httpx.AsyncClient(timeout=HTTP_COMMAND_TIMEOUT_SECONDS)
        # Swallowing failures keeps the engine loop alive but would otherwise
        # make delivery invisible - a PUT could return 204 for a node that is
        # unplugged. Recording the last outcome per address lets the API report
        # honestly without this method having to raise or block.
        self._last_delivery_succeeded_by_address: dict[str, bool] = {}

    def last_delivery_succeeded(self, address: str) -> bool | None:
        """True/False once a command has been attempted for this address,
        None if nothing has been sent to it yet."""
        return self._last_delivery_succeeded_by_address.get(address)

    async def send(self, destination_node: NodeInstance, packet: NodeMessage) -> None:
        url = f"http://{destination_node.address}:{destination_node.port}/command"
        body = {
            "name": packet.message.name,
            "payload": packet.message.payload,
        }

        try:
            response = await self._client.post(
                url,
                json=body,
                headers={"X-Node-Secret": self._shared_secret},
            )
            response.raise_for_status()
            self._last_delivery_succeeded_by_address[destination_node.address] = True
        except httpx.HTTPError as error:
            self._last_delivery_succeeded_by_address[destination_node.address] = False
            log.warn(f"Failed to deliver command '{packet.message.name}' to {url}: {error}")

    async def close(self) -> None:
        await self._client.aclose()
