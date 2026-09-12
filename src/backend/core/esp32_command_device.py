from __future__ import annotations

from core.device import Device
from core.message import Message
from core.port import Port, PortDirection


class Esp32CommandDevice(Device):
    """Addressable command endpoint standing in for a remote ESP32 node.

    Registered under the node's NodeInstance so HostEngine._deliver() routes
    connected messages through that node's NodeTransport instead of handling
    them locally (see HostEngine._deliver: local devices call
    handle_message() directly, remote ones go through transport.send()).
    handle_message() here is therefore never actually invoked in production -
    the real command execution happens in ESP32 firmware after
    NodeTransport.send() delivers the payload over HTTP. This class exists
    purely to give the Connection graph an addressable port pair.
    """

    def __init__(self, name: str = "esp32_command_device"):
        super().__init__(name)
        self.command_input_port: Port = self.add_port("cmd_in", PortDirection.INPUT)
        self.state_output_port: Port = self.add_port("state_out", PortDirection.OUTPUT)

    async def handle_message(self, port: Port, message: Message):
        return []
