from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3] / "src" / "backend"))

from core.esp32_command_device import Esp32CommandDevice
from core.message import Message, MessageType


def test_esp32_command_device_exposes_input_and_output_ports() -> None:
    device = Esp32CommandDevice()

    assert device.command_input_port.name == "cmd_in"
    assert device.state_output_port.name == "state_out"


def test_esp32_command_device_handle_message_is_a_no_op() -> None:
    device = Esp32CommandDevice()
    message = Message(type=MessageType.COMMAND, name="identify")

    result = asyncio.run(device.handle_message(device.command_input_port, message))

    assert result == []
