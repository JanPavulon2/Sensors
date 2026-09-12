from datetime import datetime, timezone

from models.domain.node import NodeSnapshot
from models.events import EventType
from models.events.node_events import NodeSnapshotUpdatedEvent
from models.events.sources import EventSource


def _make_snapshot() -> NodeSnapshot:
    return NodeSnapshot(
        instance_id="11111111-1111-1111-1111-111111111111",
        external_node_id="AA:BB:CC:DD:EE:FF",
        node_type="ESP32",
        address="10.0.0.5",
        command_port=8080,
        firmware="diuna-esp32-poc",
        capabilities=["render_output"],
        online=True,
        last_seen=datetime.now(timezone.utc),
    )


def test_node_snapshot_holds_all_expected_fields() -> None:
    snapshot = _make_snapshot()

    assert snapshot.external_node_id == "AA:BB:CC:DD:EE:FF"
    assert snapshot.online is True


def test_node_snapshot_updated_event_wraps_snapshot() -> None:
    snapshot = _make_snapshot()

    event = NodeSnapshotUpdatedEvent(snapshot=snapshot)

    assert event.type == EventType.NODE_SNAPSHOT_UPDATED
    assert event.source == EventSource.NODE_REGISTRY
    assert event.snapshot is snapshot
