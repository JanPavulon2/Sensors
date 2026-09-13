from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3] / "src" / "backend"))

from core.hardware_control_interface import HardwareControlInterface
from core.module import Module
from core.peripheral import Peripheral
from core.peripheral_type import PeripheralType


def _mosfet_board(channel_count: int) -> Module:
    return Module(
        id="mosfet_driver",
        name="MOSFET driver",
        control_interface=HardwareControlInterface.ANALOG_PWM,
        peripherals=tuple(
            Peripheral(id=f"ch{i}", name=f"ch{i}", peripheral_type=PeripheralType.MOSFET_CHANNEL)
            for i in range(channel_count)
        ),
    )


def test_single_channel_dimmer_board() -> None:
    board = _mosfet_board(1)

    assert board.channel_count == 1
    assert board.channel_names() == ("ch0",)
    assert board.control_interface is HardwareControlInterface.ANALOG_PWM


def test_three_channel_board_exposes_every_channel() -> None:
    board = _mosfet_board(3)

    assert board.channel_count == 3
    assert board.channel_names() == ("ch0", "ch1", "ch2")


def test_find_channel_returns_the_peripheral() -> None:
    board = _mosfet_board(3)

    channel = board.find_channel("ch1")

    assert channel is not None
    assert channel.peripheral_type is PeripheralType.MOSFET_CHANNEL


def test_unknown_channel_is_reported_missing() -> None:
    board = _mosfet_board(1)

    assert board.has_channel("ch0") is True
    assert board.has_channel("ch9") is False
    assert board.find_channel("ch9") is None
