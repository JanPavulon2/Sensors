"""Node schemas - Pydantic models for node-related requests"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from api.schemas.zone import ColorRequest


class NodeHeartbeatRequest(BaseModel):
    """Heartbeat payload sent by a remote node (e.g. an ESP32) every few seconds."""
    node_id: str = Field(description="Stable node identifier, e.g. the ESP32's MAC address")
    node_type: str = Field(description="Node type, e.g. 'ESP32'")
    address: str = Field(description="Node's current IP address")
    command_port: int = Field(default=8080, description="Port the node's command HTTP server listens on")
    firmware: str = Field(description="Firmware identifier/version string")
    capabilities: List[str] = Field(default_factory=list, description="Node capability strings, e.g. 'render_output'")


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
