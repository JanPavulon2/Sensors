from __future__ import annotations

from core.device import Device
from core.message import Message, MessageType
from core.port import Port, PortDirection


class WhiteLedDevice(Device):
    """Simple white LED actuator (on/off)."""

    def __init__(self, name: str = "white_led"):
        super().__init__(name)
        self.is_on = False
        self.input_port = self.add_port("cmd_in", PortDirection.INPUT)
        self.state_port = self.add_port("state_out", PortDirection.OUTPUT)

    async def handle_message(self, port: Port, message: Message):
        if port.id != self.input_port.id:
            return []

        if message.name in {"led.set", "led.on", "led.off"}:
            if message.name == "led.on":
                self.is_on = True
            elif message.name == "led.off":
                self.is_on = False
            else:
                self.is_on = bool(message.payload.get("is_on", False))

            return [
                (
                    self.state_port.name,
                    Message(
                        type=MessageType.EVENT,
                        name="led.state_changed",
                        payload={"is_on": self.is_on},
                    ),
                )
            ]

        return []


class RelayDevice(Device):
    """Simple relay actuator (open/closed represented as on/off)."""

    def __init__(self, name: str = "relay"):
        super().__init__(name)
        self.is_on = False
        self.input_port = self.add_port("cmd_in", PortDirection.INPUT)
        self.state_port = self.add_port("state_out", PortDirection.OUTPUT)

    async def handle_message(self, port: Port, message: Message):
        if port.id != self.input_port.id:
            return []

        if message.name in {"relay.set", "relay.on", "relay.off"}:
            if message.name == "relay.on":
                self.is_on = True
            elif message.name == "relay.off":
                self.is_on = False
            else:
                self.is_on = bool(message.payload.get("is_on", False))

            return [
                (
                    self.state_port.name,
                    Message(
                        type=MessageType.EVENT,
                        name="relay.state_changed",
                        payload={"is_on": self.is_on},
                    ),
                )
            ]

        return []


class ButtonDevice(Device):
    """Simple button source. Incoming message can simulate hardware press/release."""

    def __init__(self, name: str = "button"):
        super().__init__(name)
        self.command_port = self.add_port("cmd_in", PortDirection.INPUT)
        self.event_port = self.add_port("event_out", PortDirection.OUTPUT)

    async def handle_message(self, port: Port, message: Message):
        if port.id != self.command_port.id:
            return []

        if message.name == "button.press":
            return [
                (
                    self.event_port.name,
                    Message(type=MessageType.EVENT, name="button.pressed", payload={}),
                )
            ]

        if message.name == "button.release":
            return [
                (
                    self.event_port.name,
                    Message(type=MessageType.EVENT, name="button.released", payload={}),
                )
            ]

        return []
