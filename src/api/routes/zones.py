"""
Zone Endpoints - HTTP routes for zone control

EXPLANATION OF FastAPI ROUTES:
A route is a function decorated with @app.get(), @app.put(), etc.
FastAPI automatically:
1. Parses the URL and extracts parameters
2. Validates request body against Pydantic models
3. Calls your function with validated data
4. Converts return value to JSON
5. Auto-generates OpenAPI docs

Example: @app.put("/zones/{zone_id}/color")
- {zone_id} becomes a function parameter
- FastAPI validates it and passes the value
- Request body must match SetZoneColorRequest schema
- Return ZoneResponse which becomes JSON
"""

from fastapi import APIRouter, Depends, status

from api.schemas.zone import (
    SetZoneColorRequest, SetZoneAnimationParamsRequest, SetZoneAnimationRequest,
    SetZoneBrightnessRequest, SetZoneIsOnRequest, SetZoneRenderModeRequest
)
from api.schemas.animation import (
    AnimationStartRequest, AnimationStopRequest, AnimationParameterUpdateRequest
)

from models.animation_params.animation_param_id import AnimationParamID
from models.color import Color
from models.domain.animation import AnimationState
from models.domain.zone import ZoneCombined
from models.enums import LogCategory, ZoneID, ZoneRenderMode
from services.service_container import ServiceContainer
from services.zone_service import ZoneService
from api.dependencies import get_service_container
from utils.logger import get_logger
from utils.serialization import Serializer

log = get_logger().for_category(LogCategory.API)

# Create router for zone endpoints
# The router is included in the main app with prefix="/api/v1"
router = APIRouter(
    prefix="/zones",
    tags=["Zones"],
    # NOTE: All endpoints are public (no authentication required)
    # Add back dependencies=[Depends(get_current_user)] when implementing auth
)



# async def get_zone_service(
#     services: ServiceContainer = Depends(get_service_container)
# ) -> ZoneService:
#     """Dependency to get zone service instance from the service container.

#     Uses the ServiceContainer initialized by main_asyncio.py, which contains
#     the real Phase 6 ZoneService and ColorManager.
#     """
#     return ZoneService(
#         zone_service=services.zone_service,
#         color_manager=services.color_manager
#     )


async def get_old_zone_service(
    services = Depends(get_service_container)
) -> ZoneService:
    """Dependency to get zone service instance from the service container.

    Uses the ServiceContainer initialized by main_asyncio.py, which contains
    the real Phase 6 ZoneService and ColorManager.
    """
    return ZoneService(
        assembler=services.data_assembler,
        app_state_service=services.app_state_service,
        event_bus=services.event_bus
    )

# ============================================================================
# GET ENDPOINTS - Retrieve zone data (read-only, safe)
# ============================================================================

# @router.get(
#     "",
#     response_model=ZoneListResponse,
#     summary="List all zones",
#     description="Get all zones with their current state (color, brightness, mode)"
# )
# async def list_zones(
#     zone_service: ZoneAPIService = Depends(get_zone_service)
# ) -> ZoneListResponse:

#     return zone_service.get_all_zones()


# @router.get(
#     "/{zone_id}",
#     response_model=ZoneResponse,
#     summary="Get zone details",
#     description="Get a single zone's configuration and current state"
# )
# async def get_zone(
#     zone_id: str,
#     zone_service: ZoneAPIService = Depends(get_zone_service)
# ) -> ZoneResponse:
    
#     return zone_service.get_zone(zone_id)


# ============================================================================
# PUT ENDPOINTS - Modify zone state (write operations)
# ============================================================================

@router.put(
    "/{zone_id}/is-on",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set zone is on"
)
async def set_zone_is_on(
    zone_id: ZoneID,
    request: SetZoneIsOnRequest,
    services: ServiceContainer = Depends(get_service_container)
) -> None:
    """
    Sets a zone's power on/power off state.
    """
    services.zone_service.set_is_on(zone_id, request.is_on)
    
@router.put(
    "/{zone_id}/brightness",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set zone brightness (0-100%)"
)
async def set_zone_brightness(
    zone_id: ZoneID,
    request: SetZoneBrightnessRequest,
    services: ServiceContainer = Depends(get_service_container)
) -> None:
    """
    Sets zone brightness.
    """
    services.zone_service.set_brightness(zone_id, request.brightness)

    
@router.put(
    "/{zone_id}/color",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set zone color"
)
async def set_zone_color(
    zone_id: ZoneID,
    req: SetZoneColorRequest,
    services: ServiceContainer = Depends(get_service_container)
) -> None:
    color_req = req.color
    if color_req.mode == "PRESET" and color_req.preset_name:
        color = Color.from_preset(color_req.preset_name, services.color_manager)
        services.zone_service.set_color(zone_id, color)
    else:
        color = Color.from_request(color_req)
        services.zone_service.set_color(zone_id, color)
    

@router.put(
    "/{zone_id}/render-mode",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set zone render mode"
)
async def set_zone_render_mode(
    zone_id: ZoneID,
    req: SetZoneRenderModeRequest,
    services: ServiceContainer = Depends(get_service_container)
) -> None:
    """
    Change zone render mode between STATIC and ANIMATION.
    """
    services.zone_service.set_render_mode(
        zone_id=zone_id, 
        render_mode=ZoneRenderMode[req.render_mode]
    )
    
    
        
@router.put(
    "/{zone_id}/animation",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set zone animation"
)
async def set_zone_animation(
    zone_id: ZoneID,
    req: SetZoneAnimationRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    services.zone_service.set_animation(
        zone_id, 
        req.animation_id
    )
    

@router.put(
    "/{zone_id}/animation/parameters",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update zone animation parameters"
)
async def set_zone_animation_params(
    zone_id: ZoneID,
    req: SetZoneAnimationParamsRequest,
    services: ServiceContainer = Depends(get_service_container)
) -> None:
    """Update one or more animation parameters.

    Request body format:
    {
        "parameters": {
            "speed": 800,
            "intensity": 75
        }
    }
    """
    # Update each parameter in the request
    for param_id, value in req.parameters.items():
        services.zone_service.set_animation_param(
            zone_id,
            param_id,
            value
        )


# ============================================================================
# ANIMATION CONTROL ENDPOINTS
# ============================================================================

# @router.post(
#     "/{zone_id}/animation/start",
#     response_model=ZoneResponse,
#     status_code=status.HTTP_200_OK,
#     summary="Start animation on zone",
#     description="Start a specific animation on a zone with optional parameters"
# )
# async def start_zone_animation(
#     zone_id: str,
#     animation_request: AnimationStartRequest,
#     zone_service: ZoneAPIService = Depends(get_zone_service)
# ) -> ZoneResponse:
#     """
#     Start an animation on a specific zone.

#     Switches zone to ANIMATION mode and starts the specified animation.
#     Optionally includes animation parameters.

#     **Parameters:**
#     - `zone_id`: Zone ID (e.g., "FLOOR", "LAMP")

#     **Request Body:**
#     ```json
#     {
#       "animation_id": "BREATHE",
#       "parameters": {"ANIM_INTENSITY": 75}
#     }
#     ```
#     """
#     return zone_service.start_zone_animation(
#         zone_id,
#         animation_request.animation_id,
#         animation_request.parameters
#     )


@router.post(
    "/{zone_id}/animation/stop",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop animation on zone",
    description="Stop animation and switch zone to static color mode"
)
async def stop_zone_animation(
    zone_id: ZoneID,
    services: ServiceContainer = Depends(get_service_container)
) -> None:
    """
    Stop animation on a zone and switch to static color.

    Switches zone from ANIMATION mode to STATIC mode, returning to
    displaying the current color instead of animating.
    """
    services.zone_service.set_render_mode(zone_id, ZoneRenderMode.STATIC)


