# =========================================================
# core/runtime.py
# =========================================================

from typing import Dict, List
from core.device import Device
from core.connection import Connection
from core.port import Port
from core.message import Message
from core.event_bus import EventBus


class Runtime:
    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.connections: List[Connection] = []
        self.port_index: Dict[str, Port] = {}

        self.bus = EventBus()
        self.bus.subscribe(self._handle)

    def register_device(self, device: Device):
        self.devices[device.id] = device
        for port in device.ports.values():
            self.port_index[port.id] = port

    def connect(self, from_port: Port, to_port: Port):
        self.connections.append(Connection(from_port.id, to_port.id))

    async def emit(self, port: Port, message: Message):
        await self.bus.publish(message, port.id)

    async def _handle(self, message: Message, port_id: str):
        for conn in self.connections:
            if conn.from_port == port_id:
                target_port = self.port_index[conn.to_port]
                device = self.devices[target_port.device_id]

                outputs = await device.handle_message(target_port, message)

                for out_port_id, out_msg in outputs:
                    await self.bus.publish(out_msg, out_port_id)

    async def start(self):
        await self.bus.run()

