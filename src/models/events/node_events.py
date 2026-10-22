"""Remote node connectivity events (ESP32 heartbeat registry watchdog)"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.domain.node import NodeSnapshot
from models.events.base import Event
from models.events.types import EventType
from models.events.sources import EventSource


@dataclass(init=False)
class NodeCameOnlineEvent(Event):
    """A remote node started or resumed sending heartbeats"""
    node_id: str
    node_type: str
    address: str

    def __init__(self, node_id: str, node_type: str, address: str):
        super().__init__(
            type=EventType.NODE_CAME_ONLINE,
            source=EventSource.NODE_REGISTRY,
        )
        self.node_id = node_id
        self.node_type = node_type
        self.address = address


@dataclass(init=False)
class NodeWentOfflineEvent(Event):
    """A remote node stopped sending heartbeats within the online threshold"""
    node_id: str
    node_type: str
    address: str

    def __init__(self, node_id: str, node_type: str, address: str):
        super().__init__(
            type=EventType.NODE_WENT_OFFLINE,
            source=EventSource.NODE_REGISTRY,
        )
        self.node_id = node_id
        self.node_type = node_type
        self.address = address


@dataclass(init=False)
class NodeSnapshotUpdatedEvent(Event):
    """A node's snapshot changed (heartbeat received, online/offline transition)"""
    snapshot: NodeSnapshot

    def __init__(self, snapshot: NodeSnapshot):
        super().__init__(
            type=EventType.NODE_SNAPSHOT_UPDATED,
            source=EventSource.NODE_REGISTRY,
        )
        self.snapshot = snapshot


@dataclass(init=False)
class NodeAppliedStateReportedEvent(Event):
    """A node reported the state it is actually applying to its hardware.

    Published on every heartbeat that carries an `applied_state` payload.
    RemoteZoneStateService subscribes and reconciles against desired state -
    routed through the event bus rather than a direct call so the registry does
    not have to depend on the zone layer (which already depends on it).
    """
    node_id: str
    applied_states: List[Dict[str, Any]]

    def __init__(self, node_id: str, applied_states: List[Dict[str, Any]]):
        super().__init__(
            type=EventType.NODE_APPLIED_STATE_REPORTED,
            source=EventSource.NODE_REGISTRY,
        )
        self.node_id = node_id
        self.applied_states = applied_states
