from __future__ import annotations

from typing import Dict, Optional

from core.device import Device
from core.message import Message
from core.port import Port, PortDirection


class NodeCommandRouterDevice(Device):
    """Local fan-out point: one dedicated output port per registered node.

    HostEngine.connect() wires each port 1:1 to that node's
    Esp32CommandDevice input port. A single shared output port would
    broadcast to every connection from it (see HostEngine._handle), which is
    wrong for node-targeted commands - hence one port per node here.
    """

    def __init__(self, name: str = "node_command_router"):
        super().__init__(name)
        self._output_port_by_node_id: Dict[str, Port] = {}

    def add_target(self, node_external_id: str) -> Port:
        port = self.add_port(f"cmd_out_{node_external_id}", PortDirection.OUTPUT)
        self._output_port_by_node_id[node_external_id] = port
        return port

    def get_target_port(self, node_external_id: str) -> Optional[Port]:
        return self._output_port_by_node_id.get(node_external_id)

    async def handle_message(self, port: Port, message: Message):
        return []
