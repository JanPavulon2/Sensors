
# =========================================================
# core/device.py
# =========================================================

import uuid
from uuid import UUID
from typing import Dict, List, Tuple
from core.port import Port, PortDirection
from core.message import Message


def gen_id() -> UUID:
    return uuid.uuid4()


class Device:
    def __init__(self, name: str):
        self.id = gen_id()
        self.name = name
        self.ports: Dict[UUID, Port] = {}

    def add_port(self, name: str, direction: PortDirection):
        port = Port(gen_id(), name, direction, self.id)
        self.ports[port.id] = port
        return port

    async def handle_message(self, port: Port, message: Message) -> List[Tuple[UUID, Message]]:
        return []
