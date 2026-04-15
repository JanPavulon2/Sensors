# =========================================================
# core/port.py
# =========================================================

from dataclasses import dataclass
from enum import Enum


class PortDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


@dataclass
class Port:
    id: str
    name: str
    direction: PortDirection
    device_id: str

