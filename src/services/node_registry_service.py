"""Node Registry Service - registers ESP32 heartbeats as HostEngine
NodeInstances and routes outbound commands to them over HTTP.

Owns the core.host_engine.HostEngine (src/backend/core) that models
nodes/devices/connections, bridging the app-wide EventBus/ServiceContainer
world with that generic routing engine. Replaces the old standalone
in-memory dict registry in api/routes/nodes.py (see
docs/architecture-vnext/05-esp32-rpi-roadmap.md Phase 4: "fold today's
standalone nodes.py registry into that model").
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from core.capabilities import split_known_node_capabilities
from core.esp32_command_device import Esp32CommandDevice
from core.host_engine import HostEngine
from core.http_node_transport import HttpNodeTransport
from core.message import Message, MessageType
from core.node import Node, NodeType
from core.node_command_router_device import NodeCommandRouterDevice
from core.node_instance import NodeInstance
from models.domain.node import NodeSnapshot
from models.events import (
    NodeAppliedStateReportedEvent,
    NodeCameOnlineEvent,
    NodeSnapshotUpdatedEvent,
    NodeWentOfflineEvent,
)
from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.API)

ONLINE_THRESHOLD_SECONDS = 15.0
WATCHDOG_POLL_INTERVAL_SECONDS = 5.0

_ESP32_NODE_TEMPLATE = Node(id=uuid.uuid4(), node_type=NodeType.ESP32, default_capabilities=[])


class NodeRegistryService:
    """Registers ESP32 heartbeats as HostEngine NodeInstances and routes
    outbound commands to them over HTTP."""

    def __init__(self, event_bus: EventBus, node_shared_secret: str):
        self.event_bus = event_bus
        self._transport = HttpNodeTransport(node_shared_secret)
        self._host_engine = HostEngine()
        self._router = NodeCommandRouterDevice()
        self._host_engine.register_device(self._router)

        self._instance_id_by_external_id: Dict[str, UUID] = {}
        self._last_seen_by_external_id: Dict[str, datetime] = {}
        self._online_by_external_id: Dict[str, bool] = {}
        self._firmware_by_external_id: Dict[str, str] = {}

        self._watchdog_task: Optional[asyncio.Task] = None

    async def run_engine_loop(self) -> None:
        """Drives HostEngine's internal message queue. Must run as a
        background task for send_command()/emit() to actually reach
        _deliver() - HostEngine.start() is an infinite consumer loop."""
        await self._host_engine.start()

    async def register_or_update_node(
        self,
        external_node_id: str,
        node_type: str,
        address: str,
        command_port: int,
        firmware: str,
        capabilities: List[str],
        applied_states: Optional[List[dict]] = None,
    ) -> NodeSnapshot:
        known_capabilities, unknown_capabilities = split_known_node_capabilities(capabilities)
        if unknown_capabilities:
            log.warn(
                f"Node '{external_node_id}' reported unrecognized capabilities: {unknown_capabilities}"
            )

        received_at = datetime.now(timezone.utc)
        self._last_seen_by_external_id[external_node_id] = received_at
        self._firmware_by_external_id[external_node_id] = firmware

        instance_id = self._instance_id_by_external_id.get(external_node_id)
        is_new_node = instance_id is None
        if is_new_node:
            instance_id = uuid.uuid4()
            self._instance_id_by_external_id[external_node_id] = instance_id

        node_instance = NodeInstance(
            id=instance_id,
            node_id=_ESP32_NODE_TEMPLATE.id,
            address=address,
            port=command_port,
            capabilities=known_capabilities,
        )
        # NodeInstance must be registered (HostEngine.register_node) BEFORE
        # register_device() below - register_device() raises ValueError if
        # its node_id isn't already a key in HostEngine.nodes, so a brand
        # new node's NodeInstance has to exist first even though this is its
        # first heartbeat.
        self._host_engine.register_node(node_instance, transport=self._transport)

        if is_new_node:
            self._register_new_node(instance_id, external_node_id)

        if not self._online_by_external_id.get(external_node_id, False):
            self._online_by_external_id[external_node_id] = True
            log.info(f"Node '{external_node_id}' came online")
            await self.event_bus.publish(
                NodeCameOnlineEvent(node_id=external_node_id, node_type=node_type, address=address)
            )

        # Published even when empty so subscribers can tell "node reported
        # nothing" from "node never heartbeat at all".
        if applied_states:
            await self.event_bus.publish(
                NodeAppliedStateReportedEvent(
                    node_id=external_node_id, applied_states=applied_states
                )
            )

        snapshot = self._build_snapshot(external_node_id, node_instance)
        await self.event_bus.publish(NodeSnapshotUpdatedEvent(snapshot=snapshot))
        return snapshot

    def _register_new_node(self, instance_id: UUID, external_node_id: str) -> None:
        command_device = Esp32CommandDevice()
        self._host_engine.register_device(command_device, node_id=instance_id)

        router_output_port = self._router.add_target(external_node_id)
        self._host_engine.connect(router_output_port, command_device.command_input_port)

        log.info(f"Registered new node '{external_node_id}' as instance {instance_id}")

    def _build_snapshot(self, external_node_id: str, node_instance: NodeInstance) -> NodeSnapshot:
        return NodeSnapshot(
            instance_id=str(node_instance.id),
            external_node_id=external_node_id,
            node_type=_ESP32_NODE_TEMPLATE.node_type.name,
            address=node_instance.address,
            command_port=node_instance.port,
            firmware=self._firmware_by_external_id.get(external_node_id, "unknown"),
            capabilities=node_instance.capabilities,
            online=self._online_by_external_id.get(external_node_id, False),
            last_seen=self._last_seen_by_external_id[external_node_id],
            last_command_delivered=self._transport.last_delivery_succeeded(node_instance.address),
        )

    def get_node(self, external_node_id: str) -> Optional[NodeSnapshot]:
        instance_id = self._instance_id_by_external_id.get(external_node_id)
        if instance_id is None:
            return None
        node_instance = self._host_engine.nodes[instance_id].node_instance
        return self._build_snapshot(external_node_id, node_instance)

    def list_nodes(self) -> List[NodeSnapshot]:
        return [self.get_node(external_node_id) for external_node_id in self._instance_id_by_external_id]

    async def send_command(self, external_node_id: str, command_name: str, payload: dict) -> None:
        if external_node_id not in self._instance_id_by_external_id:
            raise ValueError(f"Unknown node: {external_node_id}")

        router_output_port = self._router.get_target_port(external_node_id)
        if router_output_port is None:
            raise ValueError(f"No command route registered for node: {external_node_id}")

        await self._host_engine.emit(
            router_output_port,
            Message(type=MessageType.COMMAND, name=command_name, payload=payload),
        )

    def _is_stale(self, external_node_id: str, now: datetime) -> bool:
        last_seen = self._last_seen_by_external_id.get(external_node_id)
        if last_seen is None:
            return False
        return (now - last_seen).total_seconds() > ONLINE_THRESHOLD_SECONDS

    async def _run_watchdog(self) -> None:
        while True:
            await asyncio.sleep(WATCHDOG_POLL_INTERVAL_SECONDS)
            now = datetime.now(timezone.utc)

            for external_node_id in list(self._instance_id_by_external_id):
                if self._online_by_external_id.get(external_node_id, False) and self._is_stale(external_node_id, now):
                    self._online_by_external_id[external_node_id] = False
                    log.warn(
                        f"Node '{external_node_id}' went offline (no heartbeat for over {ONLINE_THRESHOLD_SECONDS:.0f}s)"
                    )

                    node_instance = self._host_engine.nodes[self._instance_id_by_external_id[external_node_id]].node_instance
                    await self.event_bus.publish(
                        NodeWentOfflineEvent(
                            node_id=external_node_id,
                            node_type=_ESP32_NODE_TEMPLATE.node_type.name,
                            address=node_instance.address,
                        )
                    )
                    await self.event_bus.publish(NodeSnapshotUpdatedEvent(snapshot=self.get_node(external_node_id)))

    def start_watchdog(self) -> None:
        if self._watchdog_task is None:
            self._watchdog_task = asyncio.create_task(self._run_watchdog())
            log.info("Node registry watchdog started")

    async def stop_watchdog(self) -> None:
        if self._watchdog_task is None:
            return
        self._watchdog_task.cancel()
        try:
            await self._watchdog_task
        except asyncio.CancelledError:
            pass
        self._watchdog_task = None
        log.info("Node registry watchdog stopped")

    async def close(self) -> None:
        await self._transport.close()
