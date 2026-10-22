from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3] / "src" / "backend"))

from core.message import Message, MessageType
from core.node_link import NodeMessage


def test_node_message_serialization_round_trip() -> None:
    packet = NodeMessage(
        connection_id=uuid4(),
        from_node_id=uuid4(),
        to_node_id=uuid4(),
        from_device_id=uuid4(),
        from_port_id=uuid4(),
        to_device_id=uuid4(),
        to_port_id=uuid4(),
        message=Message(type=MessageType.EVENT, name="ping", payload={"n": 1}),
    )

    restored = NodeMessage.from_dict(packet.to_dict())

    assert restored == packet


def test_node_message_from_dict_rejects_non_mapping_message() -> None:
    with pytest.raises(ValueError):
        NodeMessage.from_dict(
            {
                "connection_id": str(uuid4()),
                "from_node_id": str(uuid4()),
                "to_node_id": str(uuid4()),
                "from_device_id": str(uuid4()),
                "from_port_id": str(uuid4()),
                "to_device_id": str(uuid4()),
                "to_port_id": str(uuid4()),
                "message": "nope",
            }
        )


def test_node_message_from_dict_rejects_non_mapping_payload() -> None:
    with pytest.raises(ValueError):
        NodeMessage.from_dict(
            {
                "connection_id": str(uuid4()),
                "from_node_id": str(uuid4()),
                "to_node_id": str(uuid4()),
                "from_device_id": str(uuid4()),
                "from_port_id": str(uuid4()),
                "to_device_id": str(uuid4()),
                "to_port_id": str(uuid4()),
                "message": {"type": "event", "name": "ping", "payload": "nope"},
            }
        )

