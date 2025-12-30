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
- Request body must match ZoneSetColorRequest schema
- Return ZoneResponse which becomes JSON
"""

from fastapi import APIRouter, Depends, status

from api.schemas.zone import (
    ZoneListResponse, ZoneResponse, ZoneSetColorRequest,
    ZoneSetAnimationParamRequest, ZoneSetAnimationRequest, 
    ZoneSetBrightnessRequest, ZoneSetIsOnRequest, ZoneSetRenderModeRequest, ZoneStateResponse
)
from api.schemas.animation import (
    AnimationStartRequest, AnimationStopRequest, AnimationParameterUpdateRequest
)
from api.services.zone_service import ZoneAPIService
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



async def get_zone_service(
    services: ServiceContainer = Depends(get_service_container)
) -> ZoneAPIService:
    """Dependency to get zone service instance from the service container.

    Uses the ServiceContainer initialized by main_asyncio.py, which contains
    the real Phase 6 ZoneService and ColorManager.
    """
    return ZoneAPIService(
        zone_service=services.zone_service,
        color_manager=services.color_manager
    )


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

@router.get(
    "",
    response_model=ZoneListResponse,
    summary="List all zones",
    description="Get all zones with their current state (color, brightness, mode)"
)
async def list_zones(
    zone_service: ZoneAPIService = Depends(get_zone_service)
) -> ZoneListResponse:
    """
    List all LED zones.

    Returns all zones configured in the system with their current state.
    Zones show: color (any mode), brightness, enabled state, render mode.

    **Authentication:** Not required (public endpoint)

    **Example Response:**
    ```json
    {
      "zones": [
        {
          "id": "FLOOR",
          "name": "Floor Strip",
          "pixel_count": 45,
          "state": {
            "color": {"mode": "HUE", "hue": 240, "rgb": [0, 0, 255]},
            "brightness": 200,
            "enabled": true,
            "render_mode": "STATIC",
            "animation_id": null
          },
          "gpio": 18,
          "layout": null
        }
      ],
      "count": 6
    }
    ```
    """
    return zone_service.get_all_zones()


@router.get(
    "/{zone_id}",
    response_model=ZoneResponse,
    summary="Get zone details",
    description="Get a single zone's configuration and current state"
)
async def get_zone(
    zone_id: str,
    zone_service: ZoneAPIService = Depends(get_zone_service)
) -> ZoneResponse:
    """
    Get details for a single zone.

    **Parameters:**
    - `zone_id`: Zone ID like "FLOOR", "LAMP", "LEFT" (case-insensitive)

    **Returns:** Complete zone information including:
    - Configuration (pixels, GPIO, enabled state)
    - Current state (color, brightness, render mode)
    - Layout info (if configured)

    **Errors:**
    - 404: Zone not found
    """
    return zone_service.get_zone(zone_id)


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
    request: ZoneSetIsOnRequest,
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
    request: ZoneSetBrightnessRequest,
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
    req: ZoneSetColorRequest,
    services: ServiceContainer = Depends(get_service_container)
) -> None:
    color_req = req.color
    if color_req.mode == "PRESET" and color_req.preset_name is not None:
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
    req: ZoneSetRenderModeRequest,
    services: ServiceContainer = Depends(get_service_container)
) -> None:
    """
    Change zone render mode between STATIC and ANIMATION.

    - STATIC: Zone displays solid color. If animation was running, it's stopped but preserved in state.
    - ANIMATION: Zone displays animation. Uses saved animation from state if available, otherwise uses default.
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
    req: ZoneSetAnimationRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> None:
    services.zone_service.set_animation(
        zone_id, req.animation_id
    )
    

@router.put(
    "/{zone_id}/animation/params/{param_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set zone animation param value"
)
async def set_zone_animation_param(
    zone_id: ZoneID,
    param_id: AnimationParamID,
    req: ZoneSetAnimationParamRequest,
    services: ServiceContainer = Depends(get_service_container)
) -> None:
    services.zone_service.set_animation_param(
        zone_id, param_id, req.value
    )

# ============================================================================
# POST ENDPOINTS - Actions (non-idempotent operations)
# ============================================================================

# @router.post(
#     "/{zone_id}/reset",
#     response_model=ZoneResponse,
#     status_code=status.HTTP_200_OK,
#     summary="Reset zone to defaults",
#     description="Reset zone to default color and brightness"
# )

# async def reset_zone(
#     zone_id: str,
#     zone_service: ZoneAPIService = Depends(get_zone_service)
# ) -> ZoneResponse:
#     """
#     Reset a zone to its default state.

#     Resets:
#     - Color: Black (hue 0)
#     - Brightness: 100%
#     - Mode: STATIC

#     **Parameters:**
#     - `zone_id`: Zone ID

#     **Returns:** Reset zone

#     **Use Case:** Quick reset button in UI
#     """
#     return zone_service.reset_zone(zone_id)


# ============================================================================
# ANIMATION CONTROL ENDPOINTS
# ============================================================================

@router.post(
    "/{zone_id}/animation/start",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Start animation on zone",
    description="Start a specific animation on a zone with optional parameters"
)
async def start_zone_animation(
    zone_id: str,
    animation_request: AnimationStartRequest,
    zone_service: ZoneAPIService = Depends(get_zone_service)
) -> ZoneResponse:
    """
    Start an animation on a specific zone.

    Switches zone to ANIMATION mode and starts the specified animation.
    Optionally includes animation parameters.

    **Parameters:**
    - `zone_id`: Zone ID (e.g., "FLOOR", "LAMP")

    **Request Body:**
    ```json
    {
      "animation_id": "BREATHE",
      "parameters": {"ANIM_INTENSITY": 75}
    }
    ```

    **Supported Animations:**
    - BREATHE: Smooth breathing effect
    - SNAKE: Sequential zone chase
    - COLOR_CYCLE: Color cycling through presets
    - And more (see GET /system/animations)

    **Returns:** Updated zone with animation now running

    **Side Effects:**
    - Switches zone to ANIMATION mode
    - Stops any previous animation
    - Broadcasts update to WebSocket clients
    - Changes persisted to state.json

    **Errors:**
    - 404: Zone not found or animation not found
    - 400: Invalid animation parameters
    """
    return zone_service.start_zone_animation(
        zone_id,
        animation_request.animation_id,
        animation_request.parameters
    )


@router.post(
    "/{zone_id}/animation/stop",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop animation on zone",
    description="Stop animation and switch zone to static color mode"
)
async def stop_zone_animation(
    zone_id: str,
    zone_service: ZoneAPIService = Depends(get_zone_service)
) -> ZoneResponse:
    """
    Stop animation on a zone and switch to static color.

    Switches zone from ANIMATION mode to STATIC mode, returning to
    displaying the current color instead of animating.

    **Parameters:**
    - `zone_id`: Zone ID

    **Returns:** Updated zone with animation stopped

    **Side Effects:**
    - Switches zone from ANIMATION to STATIC mode
    - Broadcasts update to WebSocket clients
    - Changes persisted to state.json

    **Note:** Zone retains its color for static display after animation stops
    """
    return zone_service.stop_zone_animation(zone_id)


@router.put(
    "/{zone_id}/animation/parameters",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Update animation parameters",
    description="Update animation parameters while animation is running"
)
async def update_animation_parameters(
    zone_id: str,
    param_request: AnimationParameterUpdateRequest,
    zone_service: ZoneAPIService = Depends(get_zone_service)
) -> ZoneResponse:
    """
    Update parameters for a running animation.

    Only works if zone is currently in ANIMATION mode. Parameters are
    applied immediately to the running animation without stopping it.

    **Parameters:**
    - `zone_id`: Zone ID

    **Request Body:**
    ```json
    {
      "parameters": {
        "ANIM_INTENSITY": 50,
        "ANIM_LENGTH": 5
      }
    }
    ```

    **Example Parameters:**
    - ANIM_INTENSITY: Animation intensity (0-100)
    - ANIM_LENGTH: Animation length/size (varies by animation)
    - ANIM_HUE_OFFSET: Hue offset for color animations (0-360)

    **Returns:** Updated zone with new animation parameters

    **Side Effects:**
    - Updates animation parameters in real-time
    - Broadcasts update to WebSocket clients
    - Changes persisted to state.json

    **Errors:**
    - 404: Zone not found
    - 400: Zone not in ANIMATION mode or invalid parameters
    """
    return zone_service.update_zone_animation_parameters(
        zone_id,
        param_request.parameters
    )
