# =========================================================
# core/port.py
# =========================================================

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class PortDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


@dataclass
class Port:
    id: UUID
    name: str
    direction: PortDirection
    device_id: UUID
