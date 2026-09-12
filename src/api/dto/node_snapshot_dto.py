from dataclasses import asdict
from typing import Any, Dict

from models.domain.node import NodeSnapshot


def node_snapshot_to_dict(snapshot: NodeSnapshot) -> Dict[str, Any]:
    """Shared REST/Socket.IO serialization for NodeSnapshot - centralizes the
    datetime -> ISO string conversion so it isn't duplicated across the REST
    route, the broadcaster, and on_connect's initial snapshot emit."""
    data = asdict(snapshot)
    data["last_seen"] = snapshot.last_seen.isoformat()
    return data
