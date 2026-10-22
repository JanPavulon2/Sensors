"""Remote zone domain models - LED zones rendered on ESP32 nodes rather than on
the RPi's own GPIO strips, so they intentionally do not go through
ZoneID/ZoneService/FrameManager.

A zone is a logical grouping of device instances that share one state. A single
diode is not itself a zone - it is a DeviceInstance that a zone may contain
alone, which is what "single-LED zone" means. See
docs/architecture-vnext/03-led-taxonomy.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from models.color import Color


@dataclass
class RemoteZoneState:
    """Desired state for a remote zone, persisted in rig.json and mirrored to
    the owning ESP32 by RemoteZoneStateService."""

    color: Color
    brightness: int = 100
    is_on: bool = True
    render_mode: str = "STATIC"  # "STATIC" or "BREATHE" - matches the firmware's animations


@dataclass
class RemoteZone:
    """Logical grouping of device instances on one node that share a state.

    zone_id is a free-form string, unlike the local ZoneID enum - that is what
    makes remote zones creatable at runtime from the UI.
    """

    zone_id: str
    display_name: str
    node_id: str
    device_instance_ids: List[str] = field(default_factory=list)
    sync_group: Optional[str] = None
