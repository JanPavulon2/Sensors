"""Remote node connectivity events (ESP32 heartbeat registry watchdog)"""

from dataclasses import dataclass

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
