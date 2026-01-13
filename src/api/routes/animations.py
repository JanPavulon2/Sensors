"""
Animation endpoints - Animation definitions and metadata

Provides read-only access to animation definitions and their parameters.
For zone-specific animation operations (start, stop, parameters), see zones.py.
"""

from fastapi import APIRouter, Depends, HTTPException
from api.schemas.animation import AnimationResponse, AnimationListResponse
from api.dependencies import get_service_container
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.API)

router = APIRouter(prefix="/animations", tags=["Animations"])


@router.get(
    "",
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
    "/{animation_id}",
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
        raise HTTPException(
            status_code=404,
            detail=f"Animation '{animation_id}' not found"
        )
