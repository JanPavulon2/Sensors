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
from typing import Annotated

from api.schemas.zone import (
    ZoneListResponse, ZoneResponse, ZoneColorUpdateRequest,
    ZoneBrightnessUpdateRequest, ZoneRenderModeUpdateRequest
)
from api.services.zone_service import ZoneAPIService
from api.middleware.auth import User, get_current_user, require_scope
from utils.logger import get_logger
from models.enums import LogCategory

log = get_logger().for_category(LogCategory.SYSTEM)

# Create router for zone endpoints
# The router is included in the main app with prefix="/api/v1"
router = APIRouter(
    prefix="/zones",
    tags=["Zones"],
    dependencies=[Depends(get_current_user)]  # All zone endpoints require auth
)


def get_zone_service() -> ZoneAPIService:
    """Dependency to get zone service instance

    MOCK FOR PHASE 8.1: Returns stub that won't crash.
    Phase 8.2 will replace with actual Phase 6 services via DI container.
    """
    from api.schemas.zone import ZoneListResponse
    from api.middleware.error_handler import ZoneNotFoundError

    class MockZoneService:
        """Stub that returns empty list (real data comes in Phase 8.2)"""

        def get_all_zones(self) -> ZoneListResponse:
            """Return empty zones (Phase 8.2 will integrate real zones)"""
            return ZoneListResponse(zones=[], count=0)

        def get_zone(self, zone_id: str):
            """Stub - not implemented yet"""
            raise ZoneNotFoundError(zone_id)

        def update_zone_color(self, zone_id: str, color_request):
            """Stub - not implemented yet"""
            raise ZoneNotFoundError(zone_id)

        def update_zone_brightness(self, zone_id: str, brightness: int):
            """Stub - not implemented yet"""
            raise ZoneNotFoundError(zone_id)

        def reset_zone(self, zone_id: str):
            """Stub - not implemented yet"""
            raise ZoneNotFoundError(zone_id)

    return MockZoneService()


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
    zone_service: ZoneAPIService = Depends(get_zone_service),
    user: User = Depends(get_current_user)
) -> ZoneListResponse:
    """
    List all LED zones.

    Returns all zones configured in the system with their current state.
    Zones show: color (any mode), brightness, enabled state, render mode.

    **Authentication:** Required (any user)

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
    log.info(f"User {user.user_id} listing zones")
    return zone_service.get_all_zones()


@router.get(
    "/{zone_id}",
    response_model=ZoneResponse,
    summary="Get zone details",
    description="Get a single zone's configuration and current state"
)
async def get_zone(
    zone_id: str,
    zone_service: ZoneAPIService = Depends(get_zone_service),
    user: User = Depends(get_current_user)
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
    log.info(f"User {user.user_id} getting zone {zone_id}")
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
    zone_service: ZoneAPIService = Depends(get_zone_service),
    user: User = Depends(require_scope("zones:write"))
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
    log.info(f"User {user.user_id} updating color for zone {zone_id}")
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
    zone_service: ZoneAPIService = Depends(get_zone_service),
    user: User = Depends(require_scope("zones:write"))
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
    log.info(f"User {user.user_id} updating brightness for zone {zone_id}")
    return zone_service.update_zone_brightness(zone_id, brightness_request.brightness)


@router.put(
    "/{zone_id}/enabled",
    response_model=ZoneResponse,
    status_code=status.HTTP_200_OK,
    summary="Enable/disable zone",
    description="Turn zone on or off"
)
async def toggle_zone_enabled(
    zone_id: str,
    enabled_request: dict,  # {"enabled": true/false}
    zone_service: ZoneAPIService = Depends(get_zone_service),
    user: User = Depends(require_scope("zones:write"))
) -> ZoneResponse:
    """
    Enable or disable a zone.

    **Parameters:**
    - `zone_id`: Zone ID

    **Request Body:**
    ```json
    {
      "enabled": true
    }
    ```

    **Effect:**
    - `enabled: true` - Zone displays color/animation normally
    - `enabled: false` - Zone is powered off (renders black)

    **Returns:** Updated zone state
    """
    log.info(f"User {user.user_id} setting zone {zone_id} enabled={enabled_request.get('enabled')}")
    # TODO: Implement once domain service supports this
    raise NotImplementedError("Zone enable/disable coming in Phase 8.2")


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
    zone_service: ZoneAPIService = Depends(get_zone_service),
    user: User = Depends(require_scope("zones:write"))
) -> ZoneResponse:
    """
    Change what a zone is displaying.

    **Parameters:**
    - `zone_id`: Zone ID

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
    """
    log.info(f"User {user.user_id} changing zone {zone_id} render mode to {mode_request.render_mode}")
    # TODO: Implement once animation service is available
    raise NotImplementedError("Zone render mode coming in Phase 8.3")


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
    zone_service: ZoneAPIService = Depends(get_zone_service),
    user: User = Depends(require_scope("zones:write"))
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
    log.info(f"User {user.user_id} resetting zone {zone_id}")
    return zone_service.reset_zone(zone_id)
