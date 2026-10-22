from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from models.domain.node import NodeSnapshot
from models.domain.remote_zone import RemoteZone
from services.multi_node_sync_broadcaster import MultiNodeSyncBroadcaster


def _make_node_snapshot(node_id: str, address: str, online: bool) -> NodeSnapshot:
    return NodeSnapshot(
        instance_id=f"instance-{node_id}",
        external_node_id=node_id,
        node_type="ESP32",
        address=address,
        command_port=8080,
        firmware="diuna-esp32-poc",
        capabilities=[],
        online=online,
        last_seen=datetime.now(timezone.utc),
    )


def test_compute_sync_groups_excludes_zones_without_a_sync_group() -> None:
    remote_zone_state_service = MagicMock()
    remote_zone_state_service.list_zones.return_value = [
        RemoteZone(zone_id="strip_1", display_name="Strip 1", node_id="AA", device_instance_ids=[], sync_group=None),
    ]
    node_registry_service = MagicMock()
    node_registry_service.get_node.return_value = _make_node_snapshot("AA", "10.0.0.5", online=True)

    broadcaster = MultiNodeSyncBroadcaster(remote_zone_state_service, node_registry_service)

    assert broadcaster.compute_sync_groups() == {}


def test_compute_sync_groups_excludes_offline_nodes() -> None:
    remote_zone_state_service = MagicMock()
    remote_zone_state_service.list_zones.return_value = [
        RemoteZone(zone_id="strip_1", display_name="Strip 1", node_id="AA", device_instance_ids=[], sync_group="workshop"),
    ]
    node_registry_service = MagicMock()
    node_registry_service.get_node.return_value = _make_node_snapshot("AA", "10.0.0.5", online=False)

    broadcaster = MultiNodeSyncBroadcaster(remote_zone_state_service, node_registry_service)

    assert broadcaster.compute_sync_groups() == {}


def test_compute_sync_groups_groups_online_members_by_sync_group() -> None:
    remote_zone_state_service = MagicMock()
    remote_zone_state_service.list_zones.return_value = [
        RemoteZone(zone_id="strip_1", display_name="Strip 1", node_id="AA", device_instance_ids=[], sync_group="workshop"),
        RemoteZone(zone_id="strip_2", display_name="Strip 2", node_id="BB", device_instance_ids=[], sync_group="workshop"),
    ]
    node_registry_service = MagicMock()
    node_registry_service.get_node.side_effect = lambda node_id: _make_node_snapshot(
        node_id, f"10.0.0.{node_id}", online=True
    )

    broadcaster = MultiNodeSyncBroadcaster(remote_zone_state_service, node_registry_service)

    assert broadcaster.compute_sync_groups() == {"workshop": ["10.0.0.AA", "10.0.0.BB"]}
