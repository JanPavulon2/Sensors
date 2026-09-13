"""Multi-Node Sync Broadcaster - periodically multicasts a shared phase
reference so ESP32 nodes in the same sync_group stay visually in lockstep
while running the built-in BREATHE animation (see
docs/architecture-vnext/05-esp32-rpi-roadmap.md Phase 7). Deliberately scoped
to phase-sync for that one animation - extend the payload if a future
animation needs the same treatment, don't generalize speculatively now."""

from __future__ import annotations

import asyncio
import json
import socket
import time
from typing import Dict, List

from services.node_registry_service import NodeRegistryService
from services.remote_zone_state_service import RemoteZoneStateService
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SYSTEM)

SYNC_MULTICAST_GROUP = "239.255.10.10"
SYNC_MULTICAST_PORT = 41234
SYNC_BROADCAST_INTERVAL_SECONDS = 2.0
SYNC_CYCLE_DURATION_MILLISECONDS = 2400  # matches firmware's breathe full cycle


class MultiNodeSyncBroadcaster:
    def __init__(self, remote_zone_state_service: RemoteZoneStateService, node_registry_service: NodeRegistryService):
        self.remote_zone_state_service = remote_zone_state_service
        self.node_registry_service = node_registry_service
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    def compute_sync_groups(self) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {}
        for zone in self.remote_zone_state_service.list_zones():
            if zone.sync_group is None:
                continue

            node_snapshot = self.node_registry_service.get_node(zone.node_id)
            if node_snapshot is None or not node_snapshot.online:
                continue

            groups.setdefault(zone.sync_group, []).append(node_snapshot.address)
        return groups

    async def start(self) -> None:
        while True:
            await asyncio.sleep(SYNC_BROADCAST_INTERVAL_SECONDS)
            self._broadcast_sync_groups()

    def _broadcast_sync_groups(self) -> None:
        for sync_group_name, member_addresses in self.compute_sync_groups().items():
            if len(member_addresses) < 2:
                continue

            reference_epoch_milliseconds = int(time.time() * 1000)
            packet = json.dumps(
                {
                    "sync_group": sync_group_name,
                    "reference_epoch_ms": reference_epoch_milliseconds,
                    "cycle_duration_ms": SYNC_CYCLE_DURATION_MILLISECONDS,
                }
            ).encode("utf-8")

            self._socket.sendto(packet, (SYNC_MULTICAST_GROUP, SYNC_MULTICAST_PORT))
            log.debug(f"Broadcast sync reference for group '{sync_group_name}'", members=len(member_addresses))
