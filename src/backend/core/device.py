
# =========================================================
# core/device.py
# =========================================================

import uuid
from typing import Dict, List, Tuple
from core.port import Port, PortDirection
from core.message import Message


def gen_id():
    return str(uuid.uuid4())


class Device:
    def __init__(self, name: str):
        self.id = gen_id()
        self.name = name
        self.ports: Dict[str, Port] = {}

    def add_port(self, name: str, direction: PortDirection):
        port = Port(gen_id(), name, direction, self.id)
        self.ports[port.id] = port
        return port

    async def handle_message(self, port: Port, message: Message) -> List[Tuple[str, Message]]:
        return []

