"""Remote node domain models (ESP32 nodes registered via heartbeat)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class NodeSnapshot:
    """Read-only view of a registered remote node, for REST/Socket.IO DTOs."""
    instance_id: str
    external_node_id: str
    node_type: str
    address: str
    command_port: int
    firmware: str
    capabilities: List[str] = field(default_factory=list)
    online: bool = False
    last_seen: datetime = field(default_factory=datetime.utcnow)

    # Outcome of the most recent command delivery attempt to this node's
    # address. None until something has actually been sent. Surfaced because
    # HttpNodeTransport must swallow delivery failures (it runs inside
    # HostEngine's shared consumer loop), so without this the API would imply
    # every command succeeded even for an unplugged node.
    last_command_delivered: Optional[bool] = None
