from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure imports like `from core...` resolve for backend-core modules
sys.path.append(str(Path(__file__).resolve().parents[3] / "src" / "backend"))

from core.basic_io_devices import ButtonDevice, RelayDevice, WhiteLedDevice
from core.message import Message, MessageType


def test_white_led_switches_on_and_emits_state_event() -> None:
    white_led_device = WhiteLedDevice()

    output_messages = asyncio.run(
        white_led_device.handle_message(
            white_led_device.input_port,
            Message(type=MessageType.COMMAND, name="led.on", payload={}),
        )
    )

    assert white_led_device.is_on is True
    assert len(output_messages) == 1
    output_port_id, output_message = output_messages[0]
    assert output_port_id == white_led_device.state_port.id
    assert output_message.name == "led.state_changed"
    assert output_message.payload["is_on"] is True


def test_relay_switches_off_via_set_command() -> None:
    relay_device = RelayDevice()
    relay_device.is_on = True

    output_messages = asyncio.run(
        relay_device.handle_message(
            relay_device.input_port,
            Message(type=MessageType.COMMAND, name="relay.set", payload={"is_on": False}),
        )
    )

    assert relay_device.is_on is False
    assert output_messages[0][1].name == "relay.state_changed"
    assert output_messages[0][1].payload["is_on"] is False


def test_button_press_emits_pressed_event() -> None:
    button_device = ButtonDevice()

    output_messages = asyncio.run(
        button_device.handle_message(
            button_device.command_port,
            Message(type=MessageType.COMMAND, name="button.press", payload={}),
        )
    )

    assert len(output_messages) == 1
    assert output_messages[0][0] == button_device.event_port.id
    assert output_messages[0][1].name == "button.pressed"
