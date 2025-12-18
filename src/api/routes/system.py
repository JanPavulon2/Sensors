"""
System endpoints - Task introspection, health, and monitoring
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from datetime import datetime, timezone
from lifecycle.task_registry import TaskRegistry
from utils.logger import get_logger, LogCategory
from api.dependencies import get_service_container
from api.schemas.animation import AnimationResponse, AnimationListResponse

log = get_logger().for_category(LogCategory.API)

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/tasks/summary")
async def get_task_summary() -> Dict[str, Any]:
    """
    Get high-level task summary.

    Returns:
        - summary: Human-readable summary string
        - total: Total tasks tracked (all time)
        - active: Currently running tasks
        - failed: Tasks that ended with exceptions
        - cancelled: Tasks that were cancelled
    """
    registry = TaskRegistry.instance()
    return {
        "summary": registry.summary(),
        "total": len(registry.list_all()),
        "active": len(registry.active()),
        "failed": len(registry.failed()),
        "cancelled": len(registry.cancelled())
    }


@router.get("/tasks")
async def get_all_tasks() -> Dict[str, Any]:
    """
    Get detailed information about all tracked tasks.

    Returns:
        - count: Total number of tasks
        - tasks: List of task details including ID, category, description, status, etc.
    """
    registry = TaskRegistry.instance()
    records = registry.list_all()

    tasks = []
    for r in records:
        # Determine task status
        if r.task.done():
            if r.cancelled:
                status = "cancelled"
            elif r.finished_with_error:
                status = "failed"
            else:
                status = "completed"
        else:
            status = "running"

        tasks.append({
            "id": r.info.id,
            "category": r.info.category.name,
            "description": r.info.description,
            "created_at": r.info.created_at,
            "created_by": r.info.created_by,
            "status": status,
            "error": str(r.finished_with_error) if r.finished_with_error else None,
        })

    return {
        "count": len(tasks),
        "tasks": tasks
    }


@router.get("/tasks/active")
async def get_active_tasks() -> Dict[str, Any]:
    """
    Get only currently running tasks.

    Useful for debugging hangs or identifying what's blocking shutdown.

    Returns:
        - count: Number of running tasks
        - running_for_seconds: Time in seconds since app start to first running task
        - tasks: List of running task details
    """
    registry = TaskRegistry.instance()
    records = registry.active()

    tasks = []
    earliest_timestamp = None

    for r in records:
        running_seconds = datetime.now(timezone.utc).timestamp() - r.info.created_timestamp

        if earliest_timestamp is None or r.info.created_timestamp < earliest_timestamp:
            earliest_timestamp = r.info.created_timestamp

        tasks.append({
            "id": r.info.id,
            "category": r.info.category.name,
            "description": r.info.description,
            "created_at": r.info.created_at,
            "running_for_seconds": round(running_seconds, 2),
        })

    # Sort by creation time (oldest first)
    tasks.sort(key=lambda t: t["created_at"])

    return {
        "count": len(tasks),
        "tasks": tasks
    }


@router.get("/tasks/failed")
async def get_failed_tasks() -> Dict[str, Any]:
    """
    Get tasks that ended with exceptions.

    Useful for debugging task failures.

    Returns:
        - count: Number of failed tasks
        - tasks: List of failed task details with exception info
    """
    registry = TaskRegistry.instance()
    records = registry.failed()

    tasks = []
    for r in records:
        tasks.append({
            "id": r.info.id,
            "category": r.info.category.name,
            "description": r.info.description,
            "created_at": r.info.created_at,
            "error": str(r.finished_with_error),
            "error_type": type(r.finished_with_error).__name__ if r.finished_with_error else None,
        })

    return {
        "count": len(tasks),
        "tasks": tasks
    }


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns app health status and task statistics.

    Returns:
        - status: "healthy" or "degraded"
        - reason: Reason if not healthy
        - tasks: Task summary statistics
        - timestamp: Current timestamp
    """
    registry = TaskRegistry.instance()

    active = registry.active()
    failed = registry.failed()

    # Determine health status
    status = "healthy"
    reason = None

    if len(failed) > 0:
        status = "degraded"
        reason = f"{len(failed)} background task(s) have failed"

    return {
        "status": status,
        "reason": reason,
        "tasks": {
            "total": len(registry.list_all()),
            "active": len(active),
            "failed": len(failed),
            "cancelled": len(registry.cancelled()),
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================================
# ANIMATION ENDPOINTS
# ============================================================================

@router.get(
    "/animations",
    response_model=AnimationListResponse,
    summary="List all animations",
    description="Get all available animation definitions"
)
async def list_animations(
    services = Depends(get_service_container)
) -> AnimationListResponse:
    """
    Get all available animations.

    Returns all animation definitions from animations.yaml with their
    parameters and descriptions.

    **Returns:**
    - animations: List of animation definitions
    - count: Total number of animations
    """
    animation_service = services.animation_service
    animations = animation_service.get_all()

    animation_responses = [
        AnimationResponse(
            id=anim.id.name,
            display_name=anim.display_name,
            description=anim.description,
            parameters=[p.name for p in anim.parameters]
        )
        for anim in animations
    ]

    return AnimationListResponse(
        animations=animation_responses,
        count=len(animation_responses)
    )


@router.get(
    "/animations/{animation_id}",
    response_model=AnimationResponse,
    summary="Get animation details",
    description="Get detailed information about a specific animation"
)
async def get_animation(
    animation_id: str,
    services = Depends(get_service_container)
) -> AnimationResponse:
    """
    Get details for a specific animation.

    **Parameters:**
    - `animation_id`: Animation ID (e.g., "BREATHE", "SNAKE", "COLOR_CYCLE")

    **Returns:** Animation definition including:
    - id: Animation ID
    - display_name: Human-readable name
    - description: What the animation does
    - parameters: List of supported parameter names

    **Errors:**
    - 404: Animation not found
    """
    animation_service = services.animation_service

    try:
        anim = animation_service.get_animation(animation_id)
        return AnimationResponse(
            id=anim.id.name,
            display_name=anim.display_name,
            description=anim.description,
            parameters=[p.name for p in anim.parameters]
        )
    except KeyError:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Animation '{animation_id}' not found"
        )
