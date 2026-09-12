"""
Node endpoints - remote node (ESP32) registry and command dispatch.

Thin FastAPI layer over NodeRegistryService (src/services/node_registry_service.py),
which owns the actual HostEngine-based node/device/transport model in
src/backend/core. See docs/architecture-vnext/05-esp32-rpi-roadmap.md Phase 4.
"""
import hmac
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from api.dependencies import get_service_container
from api.dto.node_snapshot_dto import node_snapshot_to_dict
from api.schemas.node import (
    NodeHeartbeatRequest,
    SendNodeCommandRequest,
    SetRemoteZoneBrightnessRequest,
    SetRemoteZoneColorRequest,
    SetRemoteZoneIsOnRequest,
)
from core.capabilities import ESP32_LED_STRIP_DEVICE_CAPABILITIES
from models.color import Color
from services.service_container import ServiceContainer
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.API)

router = APIRouter(prefix="/nodes", tags=["Nodes"])

DEFAULT_NODE_SHARED_SECRET = "diuna-dev-secret"
NODE_SHARED_SECRET = os.environ.get("DIUNA_NODE_SHARED_SECRET", DEFAULT_NODE_SHARED_SECRET)
if NODE_SHARED_SECRET == DEFAULT_NODE_SHARED_SECRET:
    log.warn(
        "DIUNA_NODE_SHARED_SECRET not set in environment - using the insecure default shared "
        "secret. Set it before exposing this API to a real LAN, and match it in firmware secrets.h."
    )


def _authenticate_node(x_node_secret: Optional[str]) -> bool:
    return bool(x_node_secret) and hmac.compare_digest(x_node_secret, NODE_SHARED_SECRET)


def _remote_zone_state_to_dict(state) -> Dict[str, Any]:
    red, green, blue = state.color.to_rgb()
    return {
        "is_on": state.is_on,
        "brightness": state.brightness,
        "color": {"rgb": [red, green, blue]},
        "render_mode": state.render_mode,
    }


@router.post("/heartbeat")
async def receive_heartbeat(
    heartbeat: NodeHeartbeatRequest,
    x_node_secret: Optional[str] = Header(default=None),
    services: ServiceContainer = Depends(get_service_container),
) -> Dict[str, Any]:
    if not _authenticate_node(x_node_secret):
        log.warn(f"Rejected heartbeat from node '{heartbeat.node_id}': invalid or missing shared secret")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing node secret")

    snapshot = await services.node_registry_service.register_or_update_node(
        external_node_id=heartbeat.node_id,
        node_type=heartbeat.node_type,
        address=heartbeat.address,
        command_port=heartbeat.command_port,
        firmware=heartbeat.firmware,
        capabilities=heartbeat.capabilities,
    )

    log.info(
        f"Heartbeat from node '{heartbeat.node_id}' "
        f"({heartbeat.node_type} @ {heartbeat.address}:{heartbeat.command_port}, firmware={heartbeat.firmware})"
    )

    return {"status": "ok", "host_time": snapshot.last_seen.isoformat()}


@router.get("")
async def list_nodes(services: ServiceContainer = Depends(get_service_container)) -> Dict[str, Any]:
    nodes = [node_snapshot_to_dict(n) for n in services.node_registry_service.list_nodes()]
    return {"count": len(nodes), "nodes": nodes}


@router.get("/{node_id}")
async def get_node(
    node_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> Dict[str, Any]:
    snapshot = services.node_registry_service.get_node(node_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown node: {node_id}")

    node_dict = node_snapshot_to_dict(snapshot)
    node_dict["declared_device_capabilities"] = (
        ESP32_LED_STRIP_DEVICE_CAPABILITIES if snapshot.node_type == "ESP32" else []
    )
    return node_dict


@router.post("/{node_id}/command", status_code=status.HTTP_204_NO_CONTENT)
async def send_node_command(
    node_id: str,
    request: SendNodeCommandRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    try:
        await services.node_registry_service.send_command(node_id, request.name, request.payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.get("/{node_id}/zones")
async def list_remote_zones(
    node_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> Dict[str, Any]:
    zone_configs = services.remote_zone_render_bridge.get_zones_for_node(node_id)
    return {
        "zones": [
            {
                "node_id": zone_config.node_id,
                "zone_label": zone_config.zone_label,
                "display_name": zone_config.display_name,
                "pixel_count": zone_config.pixel_count,
                "sync_group": zone_config.sync_group,
                "state": _remote_zone_state_to_dict(
                    services.remote_zone_render_bridge.get_state(zone_config.zone_label)
                ),
            }
            for zone_config in zone_configs
        ]
    }


@router.put("/{node_id}/zones/{zone_label}/color", status_code=status.HTTP_204_NO_CONTENT)
async def set_remote_zone_color(
    node_id: str,
    zone_label: str,
    request: SetRemoteZoneColorRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    color_request = request.color
    if color_request.mode == "PRESET" and color_request.preset_name:
        color = Color.from_preset(color_request.preset_name, services.color_manager)
    else:
        color = Color.from_request(color_request)

    try:
        await services.remote_zone_render_bridge.set_color(zone_label, color)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.put("/{node_id}/zones/{zone_label}/brightness", status_code=status.HTTP_204_NO_CONTENT)
async def set_remote_zone_brightness(
    node_id: str,
    zone_label: str,
    request: SetRemoteZoneBrightnessRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    try:
        await services.remote_zone_render_bridge.set_brightness(zone_label, request.brightness)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.put("/{node_id}/zones/{zone_label}/is-on", status_code=status.HTTP_204_NO_CONTENT)
async def set_remote_zone_is_on(
    node_id: str,
    zone_label: str,
    request: SetRemoteZoneIsOnRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    try:
        await services.remote_zone_render_bridge.set_is_on(zone_label, request.is_on)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
