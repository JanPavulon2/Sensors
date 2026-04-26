"""Frame streaming API routes."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from services.service_container import ServiceContainer
from api.dependencies import get_service_container
from utils.logger import get_logger
from models.enums import LogCategory

log = get_logger().for_category(LogCategory.API)

router = APIRouter(prefix="/frames", tags=["frames"])


class SetFpsRequest(BaseModel):
    """Request model for updating stream FPS."""
    target_fps: int = Field(..., ge=5, le=60, description="Target streaming FPS (5-60)")


@router.put("/fps")
async def update_stream_fps(
    request: SetFpsRequest,
    services: ServiceContainer = Depends(get_service_container)
) -> dict:
    """
    Update the frame streaming target FPS.

    Args:
        request: FPS update request with target_fps
        services: Service container with frame_streamer

    Returns:
        Success response with updated FPS
    """
    try:
        old_fps = services.frame_streamer.target_fps

        # Update target FPS
        services.frame_streamer.target_fps = request.target_fps

        # Recalculate emit interval (60 fps render / target fps)
        services.frame_streamer._emit_interval = 60 // request.target_fps

        # Reset frame counter to apply change immediately
        services.frame_streamer._frame_counter = 0

        log.info(
            f"Stream FPS updated: {old_fps} → {request.target_fps} fps "
            f"(emit every {services.frame_streamer._emit_interval} frames)"
        )

        return {
            "success": True,
            "old_fps": old_fps,
            "new_fps": request.target_fps,
            "emit_interval": services.frame_streamer._emit_interval
        }

    except Exception as e:
        log.error(f"Failed to update stream FPS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fps")
async def get_stream_fps(
    services: ServiceContainer = Depends(get_service_container)
) -> dict:
    """
    Get current frame streaming FPS.

    Args:
        services: Service container with frame_streamer

    Returns:
        Current FPS configuration
    """
    return {
        "target_fps": services.frame_streamer.target_fps,
        "emit_interval": services.frame_streamer._emit_interval,
        "frame_counter": services.frame_streamer._frame_counter
    }
