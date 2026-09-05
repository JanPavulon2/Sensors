"""
Node endpoints - Basic connectivity POC for remote nodes (e.g. ESP32 executors)

This is a standalone, in-memory registry. It is deliberately NOT wired into
ServiceContainer/src/backend/core yet - see the RPi5<->ESP32
connectivity POC plan for why. It does publish to the shared EventBus
singleton (`EventBus.instance()`), the same one main_asyncio.py wires up,
so the staleness watchdog below can emit real events without needing full
service-container wiring.
"""
import asyncio
import hmac
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from models.events import NodeCameOnlineEvent, NodeWentOfflineEvent
from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.API)

router = APIRouter(prefix="/nodes", tags=["Nodes"])

ONLINE_THRESHOLD_SECONDS = 15.0
WATCHDOG_POLL_INTERVAL_SECONDS = 5.0

DEFAULT_NODE_SHARED_SECRET = "diuna-dev-secret"
NODE_SHARED_SECRET = os.environ.get("DIUNA_NODE_SHARED_SECRET", DEFAULT_NODE_SHARED_SECRET)
if NODE_SHARED_SECRET == DEFAULT_NODE_SHARED_SECRET:
    log.warn(
        "DIUNA_NODE_SHARED_SECRET not set in environment - using the insecure default shared "
        "secret. Set it before exposing this API to a real LAN, and match it in firmware secrets.h."
    )

_known_nodes: Dict[str, Dict[str, Any]] = {}

# Tracks each node's online/offline state as last observed by the watchdog or
# a heartbeat, so transitions (not just point-in-time reads) can be detected.
_node_is_online: Dict[str, bool] = {}

_watchdog_task: Optional[asyncio.Task] = None


class NodeHeartbeat(BaseModel):
    node_id: str
    node_type: str
    address: str
    firmware: str


def _authenticate_node(x_node_secret: Optional[str]) -> bool:
    return bool(x_node_secret) and hmac.compare_digest(x_node_secret, NODE_SHARED_SECRET)


def _is_stale(node: Dict[str, Any], now: datetime) -> bool:
    return (now - node["last_seen"]).total_seconds() > ONLINE_THRESHOLD_SECONDS


@router.post("/heartbeat")
async def receive_heartbeat(
    heartbeat: NodeHeartbeat,
    x_node_secret: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """
    Receive a heartbeat from a remote node and update the in-memory registry.
    """
    if not _authenticate_node(x_node_secret):
        log.warn(f"Rejected heartbeat from node '{heartbeat.node_id}': invalid or missing shared secret")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing node secret")

    received_at = datetime.now(timezone.utc)

    _known_nodes[heartbeat.node_id] = {
        "node_id": heartbeat.node_id,
        "node_type": heartbeat.node_type,
        "address": heartbeat.address,
        "firmware": heartbeat.firmware,
        "last_seen": received_at,
    }

    log.info(
        f"Heartbeat from node '{heartbeat.node_id}' "
        f"({heartbeat.node_type} @ {heartbeat.address}, firmware={heartbeat.firmware})"
    )

    if not _node_is_online.get(heartbeat.node_id, False):
        _node_is_online[heartbeat.node_id] = True
        log.info(f"Node '{heartbeat.node_id}' came online")
        await EventBus.instance().publish(
            NodeCameOnlineEvent(
                node_id=heartbeat.node_id,
                node_type=heartbeat.node_type,
                address=heartbeat.address,
            )
        )

    return {
        "status": "ok",
        "host_time": received_at.isoformat(),
    }


@router.get("")
async def list_nodes() -> Dict[str, Any]:
    """
    List all known nodes with a computed 'online' flag based on last heartbeat.
    """
    now = datetime.now(timezone.utc)

    nodes = []
    for node in _known_nodes.values():
        nodes.append({
            **{key: value for key, value in node.items() if key != "last_seen"},
            "last_seen": node["last_seen"].isoformat(),
            "online": not _is_stale(node, now),
        })

    return {
        "count": len(nodes),
        "nodes": nodes,
    }


async def _run_watchdog() -> None:
    """
    Periodically scan known nodes for staleness and emit NodeWentOfflineEvent
    on the shared EventBus the moment a node crosses ONLINE_THRESHOLD_SECONDS,
    instead of only ever computing the 'online' flag on demand in list_nodes().
    """
    event_bus = EventBus.instance()

    while True:
        await asyncio.sleep(WATCHDOG_POLL_INTERVAL_SECONDS)
        now = datetime.now(timezone.utc)

        for node in list(_known_nodes.values()):
            node_id = node["node_id"]
            if _node_is_online.get(node_id, False) and _is_stale(node, now):
                _node_is_online[node_id] = False
                log.warn(f"Node '{node_id}' went offline (no heartbeat for over {ONLINE_THRESHOLD_SECONDS:.0f}s)")
                await event_bus.publish(
                    NodeWentOfflineEvent(
                        node_id=node_id,
                        node_type=node["node_type"],
                        address=node["address"],
                    )
                )


def start_node_watchdog() -> None:
    """Start the background staleness watchdog. Call once from app startup."""
    global _watchdog_task
    if _watchdog_task is None:
        _watchdog_task = asyncio.create_task(_run_watchdog())
        log.info("Node watchdog started")


async def stop_node_watchdog() -> None:
    """Cancel the background staleness watchdog. Call from app shutdown."""
    global _watchdog_task
    if _watchdog_task is None:
        return

    _watchdog_task.cancel()
    try:
        await _watchdog_task
    except asyncio.CancelledError:
        pass
    _watchdog_task = None
    log.info("Node watchdog stopped")
