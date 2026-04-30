
# =========================================================
# core/device.py
# =========================================================

from typing import Dict, List, Tuple
from core.port import Port, PortDirection
from core.message import Message
from core.primitives import DeviceInstanceId, PortId, PortName, new_device_instance_id, new_port_id


class Device:
    def __init__(self, name: str):
        self.id: DeviceInstanceId = new_device_instance_id()
        self.name = name
        self.ports: Dict[PortId, Port] = {}

    def add_port(self, name: str, direction: PortDirection):
        port = Port(new_port_id(), PortName(name), direction, self.id)
        self.ports[port.id] = port
        return port

    async def handle_message(self, port: Port, message: Message) -> List[Tuple[PortId, Message]]:
        return []

