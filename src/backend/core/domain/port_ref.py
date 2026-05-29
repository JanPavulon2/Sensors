from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PortRef:
    device_id: UUID
    port_name: str

