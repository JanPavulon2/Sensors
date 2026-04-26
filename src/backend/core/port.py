# =========================================================
# core/port.py
# =========================================================

from dataclasses import dataclass
from enum import auto

from core.primitives import AutoSnakeStrEnum, DeviceInstanceId, PortId


class PortDirection(AutoSnakeStrEnum):
    INPUT = auto()
    OUTPUT = auto()


@dataclass
class Port:
    id: PortId
    name: str
    direction: PortDirection
    device_id: DeviceInstanceId

