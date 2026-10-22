"""Node schemas - Pydantic models for node-related requests"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from api.schemas.zone import ColorRequest


class AppliedZoneStateReport(BaseModel):
    """One zone's state as a node reports it is actually applying it.

    Sent back in the heartbeat so the host can reconcile against desired state -
    command delivery itself is fire-and-forget (see RemoteZoneStateService).
    """
    zone_id: str
    is_on: bool = True
    brightness: int = 100
    color: Dict[str, int] = Field(default_factory=dict)
    render_mode: str = "STATIC"


class NodeHeartbeatRequest(BaseModel):
    """Heartbeat payload sent by a remote node (e.g. an ESP32) every few seconds."""
    node_id: str = Field(description="Stable node identifier, e.g. the ESP32's MAC address")
    node_type: str = Field(description="Node type, e.g. 'ESP32'")
    address: str = Field(description="Node's current IP address")
    command_port: int = Field(default=8080, description="Port the node's command HTTP server listens on")
    firmware: str = Field(description="Firmware identifier/version string")
    capabilities: List[str] = Field(default_factory=list, description="Node capability strings, e.g. 'render_output'")
    applied_state: List[AppliedZoneStateReport] = Field(
        default_factory=list,
        description="What the node is actually rendering right now, per zone. Empty from "
                    "older firmware, which simply means no reconciliation happens.",
    )
    config_version: Optional[str] = Field(
        default=None,
        description="Version of the rig config the node currently has applied, so the host "
                    "can tell when a node needs re-configuring.",
    )


class SendNodeCommandRequest(BaseModel):
    """Request to send an arbitrary named command to a node."""
    name: str = Field(description="Command name, e.g. 'identify' or 'zone.state'")
    payload: Dict[str, Any] = Field(default_factory=dict)


class SetRemoteZoneColorRequest(BaseModel):
    color: ColorRequest


class SetRemoteZoneBrightnessRequest(BaseModel):
    brightness: int = Field(ge=0, le=100)


class SetRemoteZoneIsOnRequest(BaseModel):
    is_on: bool


class SetRemoteZoneRenderModeRequest(BaseModel):
    render_mode: str = Field(description="'STATIC' or 'BREATHE'")


# === Rig editing ===


class ChannelBindingRequest(BaseModel):
    module_instance_id: str
    channel_name: str
    role: str = Field(description="SINGLE / RED / GREEN / BLUE / WHITE / DATA")


class UpsertDriverInstanceRequest(BaseModel):
    """A deployed driver module - the physical MOSFET board or data output."""
    id: str
    definition_id: str = Field(description="Driver definition slug, e.g. 'mosfet_driver_1ch'")
    node_id: str
    label: str
    channel_pins: Dict[str, int] = Field(
        default_factory=dict, description="Channel name -> GPIO pin on the node"
    )


class UpsertFixtureInstanceRequest(BaseModel):
    """A deployed light fixture, plus the properties only the user can know."""
    id: str
    definition_id: str = Field(description="Fixture definition slug, e.g. 'single_diode'")
    node_id: str
    label: str
    nominal_color: Optional[List[int]] = Field(
        default=None,
        description="The physical colour of the fitted diode/strip as [r,g,b]. User-declared: "
                    "no software can discover what was actually wired in.",
    )
    white_profile: Optional[str] = Field(default=None, description="COLD / WARM / NEUTRAL / TUNABLE")
    bindings: List[ChannelBindingRequest] = Field(default_factory=list)


class UpsertRemoteZoneRequest(BaseModel):
    zone_id: str
    display_name: str
    node_id: str
    device_instance_ids: List[str] = Field(default_factory=list)
    sync_group: Optional[str] = None
