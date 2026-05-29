# =========================================================
# core/port.py
# =========================================================

from dataclasses import dataclass
from uuid import UUID

from core.port_definition import PortDirection

@dataclass
class Port:
    id: UUID
    name: str
    direction: PortDirection
    device_id: UUID
