"""
Node endpoints - remote node (ESP32) registry and command dispatch.

Thin FastAPI layer over NodeRegistryService (src/services/node_registry_service.py),
which owns the actual HostEngine-based node/device/transport model in
src/backend/core. See docs/architecture-vnext/05-esp32-rpi-roadmap.md Phase 4.

Zone and fixture control lives in api/routes/rig.py: a zone is addressed by its
own id, not by the node it happens to be attached to.
"""
import hmac
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from api.dependencies import get_service_container
from api.dto.node_snapshot_dto import node_snapshot_to_dict
from api.schemas.node import NodeHeartbeatRequest, SendNodeCommandRequest
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
        applied_states=[report.model_dump() for report in heartbeat.applied_state],
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

    # Device capabilities are derived from what is actually wired to this node,
    # not assumed from its node type. A node with nothing attached reports none.
    rig = services.rig_service
    node_dict["device_capabilities"] = sorted(
        {
            capability
            for instance in rig.list_fixture_instances()
            if instance.node_id == node_id
            for capability in rig.get_fixture_instance_capabilities(instance.id)
        }
    )
    node_dict["zone_ids"] = [zone.zone_id for zone in rig.get_zones_for_node(node_id)]
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

    # Identify is host-initiated, so the host can mirror the blink in the live
    # preview without the node having to report anything back.
    if request.name == "identify":
        services.remote_fixture_animator.mark_identifying(node_id)
