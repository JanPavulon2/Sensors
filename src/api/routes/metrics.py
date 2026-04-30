"""Render metrics API routes — one-shot snapshots and control endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from services.service_container import ServiceContainer
from api.dependencies import get_service_container
from utils.logger import get_logger
from models.enums import LogCategory

log = get_logger().for_category(LogCategory.API)

router = APIRouter(prefix="/metrics", tags=["metrics"])


class SetMetricsIntervalRequest(BaseModel):
    interval: float = Field(..., ge=0.25, le=5.0, description="Metrics emission interval in seconds")


class SetRenderFpsRequest(BaseModel):
    fps: int = Field(..., ge=1, le=240, description="Target render FPS")


@router.get("/snapshot")
async def get_metrics_snapshot(
    services: ServiceContainer = Depends(get_service_container),
) -> dict:
    """Get a one-shot render metrics snapshot (no streaming required)."""
    if not services.metrics_streamer:
        return {"error": "MetricsStreamer not configured"}
    return services.metrics_streamer.collector.get_snapshot()


@router.post("/enable")
async def enable_metrics(
    services: ServiceContainer = Depends(get_service_container),
) -> dict:
    """Enable metrics collection without requiring a Socket.IO connection."""
    if not services.metrics_streamer:
        return {"error": "MetricsStreamer not configured"}
    services.metrics_streamer.collector.enabled = True
    return {"enabled": True}


@router.post("/disable")
async def disable_metrics(
    services: ServiceContainer = Depends(get_service_container),
) -> dict:
    """Disable metrics collection."""
    if not services.metrics_streamer:
        return {"error": "MetricsStreamer not configured"}
    services.metrics_streamer.collector.enabled = False
    return {"enabled": False}


@router.post("/reset")
async def reset_metrics(
    services: ServiceContainer = Depends(get_service_container),
) -> dict:
    """Reset all metrics counters and ring buffers."""
    if not services.metrics_streamer:
        return {"error": "MetricsStreamer not configured"}
    services.metrics_streamer.collector.reset()
    log.info("Render metrics reset via REST API")
    return {"reset": True}


@router.put("/interval")
async def set_metrics_interval(
    request: SetMetricsIntervalRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> dict:
    """Set the metrics streaming emission interval."""
    if not services.metrics_streamer:
        return {"error": "MetricsStreamer not configured"}
    old_interval = services.metrics_streamer.interval
    services.metrics_streamer.interval = request.interval
    log.info(f"Metrics interval updated: {old_interval}s → {services.metrics_streamer.interval}s")
    return {"old_interval": old_interval, "new_interval": services.metrics_streamer.interval}


@router.put("/render-fps")
async def set_render_fps(
    request: SetRenderFpsRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> dict:
    """Set the FrameManager render FPS."""
    old_fps = services.frame_manager.fps
    services.frame_manager.set_fps(request.fps)
    log.info(f"Render FPS updated: {old_fps} → {services.frame_manager.fps}")
    return {"old_fps": old_fps, "new_fps": services.frame_manager.fps}
