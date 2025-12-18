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
- Request body must match ColorUpdateRequest schema
- Return ZoneResponse which becomes JSON
"""

from fastapi import APIRouter, Depends, status

from api.schemas.zone import (
    ZoneListResponse, ZoneResponse, ZoneColorUpdateRequest,
    ZoneBrightnessUpdateRequest, ZoneRenderModeUpdateRequest, ZoneIsOnUpdateRequest
)
from api.schemas.animation import (
    AnimationStartRequest, AnimationStopRequest, AnimationParameterUpdateRequest
)
from api.services.zone_service import ZoneAPIService
from api.dependencies import get_service_container

# Create router for zone endpoints
# The router is included in the main app with prefix="/api/v1"
router = APIRouter(
    prefix="/zones",
    tags=["Zones"],
    # NOTE: All endpoints are public (no authentication required)
    # Add back dependencies=[Depends(get_current_user)] when implementing auth
)


async def get_zone_service(
    services = Depends(get_service_container)
) -> ZoneAPIService:
    """Dependency to get zone service instance from the service container.

    Uses the ServiceContainer initialized by main_asyncio.py, which contains
    the real Phase 6 ZoneService and ColorManager.
    """
    return ZoneAPIService(
        zone_service=services.zone_service,
        color_manager=services.color_manager
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
    "/{zone_id}/color",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Update zone color",
    description="Set zone to a new color (any mode: RGB, HUE, PRESET)"
)
async def update_zone_color(
    zone_id: str,
    color_request: ZoneColorUpdateRequest,
    zone_service: ZoneAPIService = Depends(get_zone_service)
) -> ZoneResponse:
    """
    Update a zone's color.

    **Parameters:**
    - `zone_id`: Zone ID (e.g., "FLOOR")

    **Request Body:** Color specification
    ```json
    {
      "color": {
        "mode": "HUE",
        "hue": 240
      }
    }
    ```

    **Supported Color Modes:**
    - `HUE`: Hue value 0-360 (e.g., 240 = blue, 0 = red)
    - `RGB`: [r, g, b] values 0-255 (e.g., [255, 0, 0] = red)
    - `PRESET`: Named color like "RED", "WARM_WHITE" (e.g., "WARM_WHITE")

    **Returns:** Updated zone with new color applied

    **Side Effects:**
    - Changes persisted immediately
    - Broadcasts update to all clients (WebSocket)
    - Triggers on-screen update if in live preview mode
    """
    return zone_service.update_zone_color(zone_id, color_request.color)


@router.put(
    "/{zone_id}/brightness",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Update zone brightness",
    description="Adjust zone brightness without changing color"
)
async def update_zone_brightness(
    zone_id: str,
    brightness_request: ZoneBrightnessUpdateRequest,
    zone_service: ZoneAPIService = Depends(get_zone_service)
) -> ZoneResponse:
    """
    Update a zone's brightness.

    **Parameters:**
    - `zone_id`: Zone ID (e.g., "LAMP")

    **Request Body:**
    ```json
    {
      "brightness": 150
    }
    ```

    **Brightness:** 0-255 where:
    - 0 = off (black)
    - 128 = half brightness
    - 255 = full brightness

    **Returns:** Updated zone with new brightness

    **Note:** This adjusts brightness independently from color.
    The color hue is preserved - only intensity changes.
    """
    return zone_service.update_zone_brightness(zone_id, brightness_request.brightness)


@router.put(
    "/{zone_id}/is-on",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle zone power",
    description="Power zone on or off"
)
async def toggle_zone_is_on(
    zone_id: str,
    is_on_request: ZoneIsOnUpdateRequest,
    zone_service: ZoneAPIService = Depends(get_zone_service)
) -> ZoneResponse:
    """
    Power a zone on or off.

    **Parameters:**
    - `zone_id`: Zone ID (e.g., "FLOOR", "LAMP")

    **Request Body:**
    ```json
    {
      "is_on": true
    }
    ```

    **Effect:**
    - `is_on: true` - Zone displays color/animation normally
    - `is_on: false` - Zone is powered off (renders black)

    **Returns:** Updated zone with new power state

    **Side Effects:**
    - Changes persisted immediately
    - Broadcasts update to all clients (WebSocket)
    - Triggers hardware update if zone is on
    """
    return zone_service.update_zone_is_on(zone_id, is_on_request.is_on)


@router.put(
    "/{zone_id}/render-mode",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Change zone render mode",
    description="Switch zone between static color, animation, or off"
)
async def update_zone_render_mode(
    zone_id: str,
    mode_request: ZoneRenderModeUpdateRequest,
    zone_service: ZoneAPIService = Depends(get_zone_service)
) -> ZoneResponse:
    """
    Change what a zone is displaying.

    **Parameters:**
    - `zone_id`: Zone ID (e.g., "FLOOR", "LAMP")

    **Request Body:**
    ```json
    {
      "render_mode": "STATIC",
      "animation_id": null
    }
    ```

    **Render Modes:**
    - `STATIC`: Display static color (no animation)
    - `ANIMATION`: Run animation (requires animation_id)
    - `OFF`: Zone powered off (black)

    **Returns:** Updated zone with new render mode

    **Examples:**
    ```json
    // Switch to static color
    {"render_mode": "STATIC"}

    // Start animation
    {"render_mode": "ANIMATION", "animation_id": "BREATHE"}

    // Turn off
    {"render_mode": "OFF"}
    ```

    **Side Effects:**
    - Changes persisted immediately
    - Broadcasts update to all clients (WebSocket)
    - Stops any running animation if switching away from ANIMATION mode
    - Starts animation if switching to ANIMATION mode with valid animation_id
    """
    return zone_service.update_zone_render_mode(
        zone_id,
        mode_request.render_mode.value,
        mode_request.animation_id
    )


# ============================================================================
# POST ENDPOINTS - Actions (non-idempotent operations)
# ============================================================================

@router.post(
    "/{zone_id}/reset",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset zone to defaults",
    description="Reset zone to default color and brightness"
)
async def reset_zone(
    zone_id: str,
    zone_service: ZoneAPIService = Depends(get_zone_service)
) -> ZoneResponse:
    """
    Reset a zone to its default state.

    Resets:
    - Color: Black (hue 0)
    - Brightness: 100%
    - Mode: STATIC

    **Parameters:**
    - `zone_id`: Zone ID

    **Returns:** Reset zone

    **Use Case:** Quick reset button in UI
    """
    return zone_service.reset_zone(zone_id)


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
