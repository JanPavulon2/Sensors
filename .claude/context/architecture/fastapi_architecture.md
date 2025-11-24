---
Last Updated: 2025-11-17
Updated By: @architecture-expert-sonnet
Changes: Complete Phase 9 API Layer architecture design and implementation plan
---

# Phase 9: Backend API Layer - FastAPI Architecture

## Executive Summary

This document provides a detailed, production-ready design for Phase 9 of the Diuna LED Control System: implementing a REST + WebSocket API layer using FastAPI. The design is **non-invasive** (zero changes to existing services/controllers) and leverages the existing `ServiceContainer` dependency injection pattern.

**Effort Estimate**: 28-32 hours (3.5-4 days)
**Complexity**: Medium
**Risk**: Low (additive change, easy to rollback)

---

## 1. Architecture Overview

### Current System Flow
```
Hardware Input (Encoder, Button)
    ↓
EventBus (pub-sub)
    ↓
Controllers (StaticMode, AnimationMode, etc.)
    ↓
Services (Zone, Animation, AppState)
    ↓
State Persistence (DataAssembler → state.json)
    ↓
FrameManager (60 FPS rendering)
    ↓
Hardware Output (WS2811 LEDs)
```

### Phase 9 Addition: API Layer
```
┌──────────────────────────────────────────────────────┐
│           Frontend (React - Phase 10)                 │
│  - Web UI on desktop, mobile, tablet                  │
│  - WebSocket real-time sync                           │
│  - REST API calls for CRUD operations                 │
└─────────────────┬──────────────────────────────────────┘
                  │ HTTP + WebSocket
┌─────────────────▼──────────────────────────────────────┐
│  NEW: API Layer (FastAPI + Uvicorn)                    │
│  ├─ REST endpoints (/api/zones, /api/animations, etc) │
│  ├─ WebSocket server (/ws/events)                     │
│  ├─ OpenAPI documentation (auto-generated)            │
│  ├─ Error handling + CORS middleware                  │
│  └─ Pydantic request/response validation              │
└─────────────────┬──────────────────────────────────────┘
                  │ ServiceContainer
┌─────────────────▼──────────────────────────────────────┐
│  EXISTING: Core Backend (NO CHANGES)                   │
│  ├─ Services (Zone, Animation, AppState)              │
│  ├─ Controllers (LED, Static, Animation, Lamp, Power) │
│  ├─ FrameManager (60 FPS rendering)                   │
│  ├─ EventBus (pub-sub event routing)                  │
│  ├─ Hardware Layer (GPIO, WS2811, encoders, buttons)  │
│  └─ State Management (DataAssembler, state.json)      │
└──────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**1. FastAPI Over Alternatives**
- Async-native (matches existing asyncio architecture)
- Automatic OpenAPI/Swagger documentation
- Pydantic validation with clear error messages
- WebSocket support built-in
- Excellent documentation and community support
- Type hints drive documentation

**2. ServiceContainer Integration**
- API layer receives same `ServiceContainer` as controllers
- No tight coupling to specific services
- Easy to test and extend
- Services remain pure (no HTTP concerns)

**3. Non-Invasive Design**
- Zero changes to existing services/controllers
- New code in `src/api/` directory
- Runs as background asyncio task
- Can be disabled/removed without affecting core functionality

**4. EventBus Bidirectional Integration**
- API can publish `WEB_COMMAND` events to EventBus
- API can subscribe to `ZONE_STATE_CHANGED`, `ANIMATION_STARTED`, etc.
- Existing handlers process API commands
- WebSocket broadcasts system state changes to clients

**5. Serialization Strategy**
- Leverage existing `Serializer` class from Phase 8C
- API models (Pydantic) separate from domain models
- Enum serialization centralized: `ZoneID.FLOOR` ↔ `"FLOOR"`
- Type-safe conversion with clear error messages

---

## 2. File Structure

### New Files

```
src/api/                              # NEW: API layer (all files)
├── __init__.py
├── app.py                           # FastAPI app factory + configuration
├── dependencies.py                  # FastAPI dependency injection helpers
├── routes/
│   ├── __init__.py
│   ├── zones.py                    # Zone CRUD endpoints
│   ├── animations.py               # Animation control endpoints
│   ├── colors.py                   # Color preset endpoints
│   ├── system.py                   # System info/metrics endpoints
│   └── websocket.py                # WebSocket real-time endpoint
├── models/                          # Pydantic API models (request/response)
│   ├── __init__.py
│   ├── zone.py                     # ZoneResponse, ZoneUpdateRequest
│   ├── animation.py                # AnimationResponse, AnimationStartRequest
│   ├── color.py                    # ColorModel, ColorConvertRequest
│   ├── system.py                   # SystemInfo, MetricsResponse, ModeChangeRequest
│   └── websocket.py                # WebSocketMessage, ClientCommand
└── middleware/
    ├── __init__.py
    └── error_handlers.py           # HTTP exception handlers

src/config/
└── api.yaml                         # NEW: API configuration

tests/integration/
└── test_api.py                      # NEW: API integration tests (optional)
```

### Modified Files

```
src/main_asyncio.py                 # MODIFIED: Start FastAPI server as background task
src/config/config.yaml              # MODIFIED: Include api.yaml
requirements.txt                    # MODIFIED: Add fastapi, uvicorn, pydantic
```

---

## 3. API Specification

### 3.1 REST Endpoints

#### Zones API

```
GET /api/zones
  Description: Get all zones with current state and configuration
  Response: List[ZoneResponse]
  Example:
  {
    "zones": [
      {
        "id": "FLOOR",
        "display_name": "Floor Strip",
        "pixel_count": 45,
        "enabled": true,
        "state": {
          "color": {"mode": "HUE", "hue": 240},
          "brightness": 200
        }
      }
    ]
  }

GET /api/zones/{zone_id}
  Description: Get single zone by ID
  Parameters: zone_id (string, e.g. "FLOOR")
  Response: ZoneResponse
  Errors: 404 if zone not found

PUT /api/zones/{zone_id}/color
  Description: Update zone color
  Request: {
    "color": {
      "mode": "HUE" | "RGB" | "PRESET" | "WHITE",
      "hue": 0-360,              # if mode=HUE
      "rgb": [0-255, 0-255, 0-255],  # if mode=RGB
      "preset_name": "warm_white",   # if mode=PRESET
      "temperature_k": 2700          # if mode=WHITE
    }
  }
  Response: {"status": "ok", "zone_id": "FLOOR"}
  Errors: 400 if invalid color, 404 if zone not found

PUT /api/zones/{zone_id}/brightness
  Description: Update zone brightness
  Request: {"brightness": 0-255}
  Response: {"status": "ok", "brightness": 200}
  Errors: 400 if brightness out of range

POST /api/zones/{zone_id}/adjust
  Description: Adjust parameter by delta (for smooth encoder-like control)
  Request: {
    "parameter_id": "ZONE_BRIGHTNESS",
    "delta": 10  # Positive or negative
  }
  Response: {"status": "ok", "new_value": 210}
  Errors: 400 if parameter invalid
```

#### Animations API

```
GET /api/animations
  Description: List all available animations with metadata
  Response: List[AnimationResponse]
  Example:
  {
    "animations": [
      {
        "id": "COLOR_CYCLE",
        "display_name": "Color Cycle",
        "description": "Rainbow cycle through all hues",
        "enabled": true,
        "parameters": [
          {
            "id": "ANIM_SPEED",
            "name": "Speed",
            "min": 0,
            "max": 100,
            "current": 50
          }
        ]
      }
    ]
  }

GET /api/animations/{animation_id}
  Description: Get animation details
  Response: AnimationResponse
  Errors: 404 if animation not found

POST /api/animations/{animation_id}/start
  Description: Start animation with parameters
  Request: {
    "zones": ["FLOOR", "LAMP"],  # Optional: limit to zones
    "parameters": {
      "ANIM_SPEED": 75,
      "ANIM_INTENSITY": 100
    }
  }
  Response: {"status": "ok", "animation_id": "COLOR_CYCLE"}
  Errors: 400 if invalid parameters

POST /api/animations/{animation_id}/stop
  Description: Stop current animation
  Response: {"status": "ok"}

PUT /api/animations/{animation_id}/parameters
  Description: Update animation parameters in real-time
  Request: {
    "ANIM_SPEED": 80,
    "ANIM_INTENSITY": 90
  }
  Response: {"status": "ok", "parameters": {...}}
  Errors: 400 if animation not running or invalid params
```

#### Colors API

```
GET /api/colors/presets
  Description: List all named color presets
  Response: {
    "presets": [
      {
        "name": "warm_white",
        "color": {"mode": "WHITE", "temperature_k": 2700}
      },
      {
        "name": "cool_blue",
        "color": {"mode": "RGB", "rgb": [0, 100, 255]}
      }
    ]
  }

POST /api/colors/convert
  Description: Convert color between modes
  Request: {
    "from": {"mode": "HSV", "h": 240, "s": 100, "v": 100},
    "to": "RGB"
  }
  Response: {
    "from": {...},
    "to": {"mode": "RGB", "rgb": [0, 0, 255]}
  }
  Errors: 400 if conversion invalid
```

#### System API

```
GET /api/system/info
  Description: Get system metadata and configuration
  Response: {
    "system": {
      "version": "1.0.0",
      "uptime_seconds": 3600,
      "zones_count": 8,
      "total_pixels": 90,
      "animations_count": 6,
      "python_version": "3.11.2",
      "platform": "raspberrypi"
    }
  }

GET /api/system/metrics
  Description: Get performance metrics from FrameManager
  Response: {
    "metrics": {
      "fps_target": 60,
      "fps_actual": 59.8,
      "frames_rendered": 358234,
      "dropped_frames": 2,
      "memory_mb": 145,
      "cpu_percent": 28,
      "uptime_seconds": 3600
    }
  }

GET /api/system/state
  Description: Get current application state
  Response: {
    "state": {
      "main_mode": "STATIC",
      "current_animation": null,
      "edit_mode": false,
      "lamp_white_mode": false,
      "current_zone_index": 0,
      "frame_by_frame": false
    }
  }

PUT /api/system/mode
  Description: Change main mode (STATIC ↔ ANIMATION)
  Request: {"main_mode": "ANIMATION"}
  Response: {"status": "ok", "main_mode": "ANIMATION"}
  Errors: 400 if invalid mode

POST /api/system/power
  Description: Power on/off with smooth transitions
  Request: {"power": true}  # true=on, false=off
  Response: {"status": "ok", "power": true}
```

---

### 3.2 WebSocket Protocol

**Endpoint**: `ws://host:8000/ws/events`

#### Server → Client Messages (State Updates)

```json
{
  "type": "ZONE_STATE_CHANGED",
  "timestamp": "2025-11-17T12:34:56.123Z",
  "data": {
    "zone_id": "FLOOR",
    "color": {"mode": "HUE", "hue": 180},
    "brightness": 200
  }
}
```

**Event Types**:
- `ZONE_STATE_CHANGED`: Zone color or brightness changed
- `ANIMATION_STARTED`: Animation started
- `ANIMATION_STOPPED`: Animation stopped
- `ANIMATION_PARAMETER_CHANGED`: Animation parameter updated
- `MODE_CHANGED`: Main mode switched (STATIC ↔ ANIMATION)
- `POWER_STATE_CHANGED`: Power state changed
- `SYSTEM_METRICS`: Performance metrics (periodic, e.g., every 5 seconds)

#### Client → Server Commands

```json
{
  "action": "set_zone_color",
  "zone_id": "FLOOR",
  "color": {"mode": "HUE", "hue": 240}
}
```

**Supported Actions**:
- `set_zone_color`: Update zone color
- `set_zone_brightness`: Update zone brightness
- `start_animation`: Start animation with parameters
- `stop_animation`: Stop animation
- `set_animation_parameter`: Update animation parameter
- `change_mode`: Switch STATIC/ANIMATION
- `power_on` / `power_off`: Power control

#### Connection Lifecycle

```
Client connects to /ws/events
    ↓
Server accepts connection, adds to connected_clients set
    ↓
Server subscribes client to EventBus events
    ↓
Server sends initial state snapshot
    ↓
Server forwards all subsequent events to client
    ↓
Client can send commands at any time
    ↓
Client disconnects
    ↓
Server removes from connected_clients, cleans up
```

---

## 4. Pydantic Models

### Zone Models

```python
# api/models/zone.py

from pydantic import BaseModel, Field
from typing import Optional

class ColorModel(BaseModel):
    """Color representation in API"""
    mode: str  # "HUE", "RGB", "PRESET", "WHITE"
    hue: Optional[int] = Field(None, ge=0, le=360)
    rgb: Optional[tuple[int, int, int]] = None
    preset_name: Optional[str] = None
    temperature_k: Optional[int] = Field(None, ge=1000, le=10000)

class ZoneStateModel(BaseModel):
    """Current zone state"""
    color: ColorModel
    brightness: int = Field(ge=0, le=255)

class ZoneResponse(BaseModel):
    """Zone data returned by GET /api/zones"""
    id: str
    display_name: str
    pixel_count: int
    enabled: bool
    state: ZoneStateModel

class ZoneUpdateRequest(BaseModel):
    """Request body for PUT /api/zones/{zone_id}/color"""
    color: Optional[ColorModel] = None
    brightness: Optional[int] = Field(None, ge=0, le=255)

class ZoneAdjustRequest(BaseModel):
    """Request body for POST /api/zones/{zone_id}/adjust"""
    parameter_id: str
    delta: int  # Positive or negative adjustment
```

### Animation Models

```python
# api/models/animation.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class ParameterModel(BaseModel):
    """Animation parameter metadata"""
    id: str
    name: str
    min: int
    max: int
    step: int
    current: int

class AnimationResponse(BaseModel):
    """Animation data returned by GET /api/animations"""
    id: str
    display_name: str
    description: str
    enabled: bool
    parameters: List[ParameterModel]

class AnimationStartRequest(BaseModel):
    """Request body for POST /api/animations/{animation_id}/start"""
    zones: Optional[List[str]] = None
    parameters: Optional[Dict[str, int]] = None

class AnimationParameterRequest(BaseModel):
    """Request body for PUT /api/animations/{animation_id}/parameters"""
    parameters: Dict[str, int]
```

### System Models

```python
# api/models/system.py

from pydantic import BaseModel
from typing import Optional

class SystemInfoResponse(BaseModel):
    """System information"""
    version: str
    uptime_seconds: int
    zones_count: int
    total_pixels: int
    animations_count: int
    python_version: str
    platform: str

class MetricsResponse(BaseModel):
    """Performance metrics from FrameManager"""
    fps_target: int
    fps_actual: float
    frames_rendered: int
    dropped_frames: int
    memory_mb: int
    cpu_percent: float
    uptime_seconds: int

class ModeChangeRequest(BaseModel):
    """Request body for PUT /api/system/mode"""
    main_mode: str  # "STATIC" or "ANIMATION"

class PowerRequest(BaseModel):
    """Request body for POST /api/system/power"""
    power: bool  # True = on, False = off
```

### WebSocket Models

```python
# api/models/websocket.py

from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime

class WebSocketMessage(BaseModel):
    """Message from server to client"""
    type: str  # "ZONE_STATE_CHANGED", "ANIMATION_STARTED", etc.
    timestamp: datetime
    data: dict[str, Any]

class ClientCommand(BaseModel):
    """Message from client to server"""
    action: str
    zone_id: Optional[str] = None
    color: Optional[dict] = None
    animation_id: Optional[str] = None
    parameters: Optional[dict] = None
```

---

## 5. Implementation Details

### 5.1 FastAPI App Factory

```python
# src/api/app.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from services.service_container import ServiceContainer
from api.routes import zones, animations, colors, system, websocket
from api.middleware.error_handlers import setup_exception_handlers

def create_app(services: ServiceContainer) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        services: ServiceContainer with all backend services

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Diuna LED Control API",
        description="REST + WebSocket API for Diuna LED control system",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    # Store services in app state for routes to access
    app.state.services = services

    # Middleware: CORS (allow frontend to access API)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:3000",  # Alternative frontend
            "http://raspberrypi.local",
            "http://*"  # Local network IPs (configure in production)
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware: Response compression
    app.add_middleware(GZIPMiddleware, minimum_size=1000)

    # Setup exception handlers
    setup_exception_handlers(app)

    # Register routers
    app.include_router(zones.router, prefix="/api/zones", tags=["zones"])
    app.include_router(animations.router, prefix="/api/animations", tags=["animations"])
    app.include_router(colors.router, prefix="/api/colors", tags=["colors"])
    app.include_router(system.router, prefix="/api/system", tags=["system"])
    app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

    # Health check endpoint
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
```

### 5.2 Dependency Injection

```python
# src/api/dependencies.py

from fastapi import Depends, Request
from services.service_container import ServiceContainer
from services.zone_service import ZoneService
from services.animation_service import AnimationService
from services.application_state_service import ApplicationStateService
from engine.frame_manager import FrameManager
from services.event_bus import EventBus

def get_services(request: Request) -> ServiceContainer:
    """Get ServiceContainer from app state.

    Used by FastAPI dependency injection to provide services to routes.
    """
    return request.app.state.services

def get_zone_service(services = Depends(get_services)) -> ZoneService:
    return services.zone_service

def get_animation_service(services = Depends(get_services)) -> AnimationService:
    return services.animation_service

def get_app_state_service(services = Depends(get_services)) -> ApplicationStateService:
    return services.app_state_service

def get_frame_manager(services = Depends(get_services)) -> FrameManager:
    return services.frame_manager

def get_event_bus(services = Depends(get_services)) -> EventBus:
    return services.event_bus
```

### 5.3 Zone Endpoints

```python
# src/api/routes/zones.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from api.models.zone import ZoneResponse, ZoneUpdateRequest, ZoneAdjustRequest
from api.dependencies import get_zone_service
from services.zone_service import ZoneService
from utils.serialization import Serializer
from models.enums import ZoneID, ParamID
from models.color import Color

router = APIRouter()

@router.get("/", response_model=List[ZoneResponse])
async def list_zones(zone_service: ZoneService = Depends(get_zone_service)):
    """Get all zones with current state and configuration."""
    try:
        zones = zone_service.get_all()
        return [Serializer.zone_to_dict(zone) for zone in zones]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: str,
    zone_service: ZoneService = Depends(get_zone_service)
):
    """Get single zone by ID."""
    try:
        zone_enum = Serializer.str_to_enum(zone_id, ZoneID)
        zone = zone_service.get_zone(zone_enum)
        return Serializer.zone_to_dict(zone)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Zone not found: {zone_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{zone_id}/color")
async def update_zone_color(
    zone_id: str,
    request: ZoneUpdateRequest,
    zone_service: ZoneService = Depends(get_zone_service)
):
    """Update zone color."""
    try:
        zone_enum = Serializer.str_to_enum(zone_id, ZoneID)

        if request.color:
            color = Serializer.dict_to_color(request.color)
            zone_service.set_color(zone_enum, color)

        if request.brightness is not None:
            zone_service.set_brightness(zone_enum, request.brightness)

        return {"status": "ok", "zone_id": zone_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{zone_id}/adjust")
async def adjust_zone_parameter(
    zone_id: str,
    request: ZoneAdjustRequest,
    zone_service: ZoneService = Depends(get_zone_service)
):
    """Adjust zone parameter by delta (for encoder-like control)."""
    try:
        zone_enum = Serializer.str_to_enum(zone_id, ZoneID)
        param_enum = Serializer.str_to_enum(request.parameter_id, ParamID)

        zone_service.adjust_parameter(zone_enum, param_enum, request.delta)

        # Get updated value
        zone = zone_service.get_zone(zone_enum)
        new_value = zone.parameters[param_enum].state.value

        return {"status": "ok", "parameter_id": request.parameter_id, "new_value": new_value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 5.4 WebSocket Implementation

```python
# src/api/routes/websocket.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from api.dependencies import get_services, get_event_bus
from services.service_container import ServiceContainer
from services.event_bus import EventBus
from models.events import EventType, Event
from api.models.websocket import WebSocketMessage, ClientCommand
import json
from datetime import datetime
import logging

log = logging.getLogger(__name__)
router = APIRouter()

# Track connected clients
connected_clients: set[WebSocket] = set()

@router.websocket("/events")
async def websocket_endpoint(
    websocket: WebSocket,
    services: ServiceContainer = Depends(get_services)
):
    """WebSocket endpoint for real-time state updates and remote commands.

    Clients connect here to receive real-time updates from the LED system
    and send remote commands (set color, start animation, etc.).
    """
    await websocket.accept()
    connected_clients.add(websocket)
    log.info(f"WebSocket client connected. Total clients: {len(connected_clients)}")

    event_bus = services.event_bus
    zone_service = services.zone_service
    animation_service = services.animation_service
    app_state_service = services.app_state_service

    # Subscribe to system events and forward to this client
    async def forward_event(event: Event):
        """Forward system event to WebSocket client."""
        try:
            message = WebSocketMessage(
                type=event.type.name,
                timestamp=datetime.now(),
                data=event.__dict__
            )
            await websocket.send_json(json.loads(message.model_dump_json()))
        except Exception as e:
            log.error(f"Error forwarding event to client: {e}")

    # Subscribe to relevant events
    subscriptions = [
        event_bus.subscribe(EventType.ZONE_STATE_CHANGED, forward_event),
        event_bus.subscribe(EventType.ANIMATION_STARTED, forward_event),
        event_bus.subscribe(EventType.ANIMATION_STOPPED, forward_event),
        event_bus.subscribe(EventType.MODE_CHANGED, forward_event),
    ]

    try:
        # Main message loop
        while True:
            data = await websocket.receive_json()
            command = ClientCommand(**data)

            # Process client commands
            try:
                if command.action == "set_zone_color":
                    # ... handle command ...
                    pass
                elif command.action == "start_animation":
                    # ... handle command ...
                    pass
                # ... other commands ...
            except Exception as e:
                await websocket.send_json({
                    "type": "ERROR",
                    "detail": str(e)
                })

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        log.info(f"WebSocket client disconnected. Total clients: {len(connected_clients)}")
    except Exception as e:
        log.error(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)

async def broadcast_event(event: Event):
    """Broadcast system event to all connected WebSocket clients."""
    message = WebSocketMessage(
        type=event.type.name,
        timestamp=datetime.now(),
        data=event.__dict__
    )

    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_json(json.loads(message.model_dump_json()))
        except Exception:
            disconnected.add(client)

    # Clean up disconnected clients
    for client in disconnected:
        connected_clients.discard(client)
```

### 5.5 Integration with main_asyncio.py

```python
# In src/main_asyncio.py (add around line 200)

from api.app import create_app
import uvicorn

async def main():
    # ... existing setup code (lines 100-200) ...

    # Create ServiceContainer
    services = ServiceContainer(
        zone_service=zone_service,
        animation_service=animation_service,
        app_state_service=app_state_service,
        frame_manager=frame_manager,
        event_bus=event_bus,
        color_manager=color_manager
    )

    # ... existing controller creation (lines 201-250) ...

    # Create FastAPI application
    log.info("Creating FastAPI application...")
    api_app = create_app(services)

    # Start FastAPI server as background asyncio task
    log.info("Starting API server on 0.0.0.0:8000...")
    config = uvicorn.Config(
        api_app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=False  # Use our logger instead
    )
    server = uvicorn.Server(config)
    api_task = asyncio.create_task(server.serve())

    # Main event loop with API server
    try:
        await asyncio.gather(
            keyboard_task,        # Existing: keyboard input
            polling_task,         # Existing: hardware polling
            api_task              # NEW: FastAPI server
        )
    finally:
        log.info("Shutting down API server...")
        server.should_exit = True
        await api_task

        # ... existing cleanup (lines 300+) ...
```

---

## 6. Error Handling

### 5xx Server Errors

```python
# api/middleware/error_handlers.py

from fastapi import FastAPI
from fastapi.responses import JSONResponse

def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers."""

    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
```

### Common Errors

- **400 Bad Request**: Invalid color values, out-of-range brightness, invalid enum
- **404 Not Found**: Zone/animation doesn't exist
- **500 Internal Server Error**: Unhandled exception in service layer
- **WebSocket**: Close codes 1000 (normal), 1006 (abnormal close)

---

## 7. Configuration

### api.yaml

```yaml
# src/config/api.yaml

api:
  # Server configuration
  host: "0.0.0.0"
  port: 8000
  workers: 1  # Single worker for asyncio compatibility

  # CORS configuration
  cors:
    enabled: true
    origins:
      - "http://localhost:5173"      # Vite dev server
      - "http://localhost:3000"      # Alternative frontend
      - "http://raspberrypi.local"
      - "http://*"  # Allow all local network IPs (configure in production)
    allow_credentials: true
    allow_methods: ["*"]
    allow_headers: ["*"]

  # Rate limiting (optional)
  rate_limiting:
    enabled: false
    requests_per_minute: 60

  # WebSocket configuration
  websocket:
    heartbeat_interval: 30           # Ping clients every 30 seconds
    max_connections: 50              # Maximum concurrent clients
    connection_timeout: 300          # Disconnect after 5 minutes idle

  # Logging
  logging:
    level: "INFO"
    access_log: false  # Use Diuna's structured logger instead
```

---

## 8. Testing Strategy

### Unit Tests

```python
# tests/integration/test_api_zones.py

from fastapi.testclient import TestClient
from api.app import create_app
from services.service_container import ServiceContainer

def test_list_zones():
    client = TestClient(create_app(test_services))
    response = client.get("/api/zones")
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_update_zone_color():
    client = TestClient(create_app(test_services))
    response = client.put(
        "/api/zones/FLOOR/color",
        json={"color": {"mode": "HUE", "hue": 180}}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_invalid_zone():
    client = TestClient(create_app(test_services))
    response = client.get("/api/zones/INVALID")
    assert response.status_code == 404
```

### Manual Testing (curl)

```bash
# List all zones
curl http://localhost:8000/api/zones

# Get single zone
curl http://localhost:8000/api/zones/FLOOR

# Update zone color
curl -X PUT http://localhost:8000/api/zones/FLOOR/color \
  -H "Content-Type: application/json" \
  -d '{"color": {"mode": "HUE", "hue": 240}}'

# Get animation list
curl http://localhost:8000/api/animations

# Start animation
curl -X POST http://localhost:8000/api/animations/COLOR_CYCLE/start \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"ANIM_SPEED": 75}}'

# Check metrics
curl http://localhost:8000/api/system/metrics

# View API documentation
open http://localhost:8000/api/docs
```

### Performance Testing

- **Latency Target**: <50ms for REST endpoints
- **WebSocket Throughput**: 100+ events/second to multiple clients
- **Concurrent Clients**: Support 10+ simultaneous WebSocket connections
- **Load Testing**: Apache JMeter or wrk for HTTP load testing

---

## 9. Dependencies

### requirements.txt

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
python-multipart==0.0.6
websockets==12.0
```

**Note**: Existing dependencies (PyYAML, asyncio, RPi.GPIO, etc.) remain unchanged.

---

## 10. Security Considerations

### For Production Deployment

1. **CORS**: Configure specific origins, not `*`
2. **HTTPS**: Use Let's Encrypt with Nginx reverse proxy
3. **Rate Limiting**: Enable to prevent API abuse
4. **Authentication**: Add JWT tokens if exposing beyond local network
5. **WebSocket Security**: Validate client commands, prevent injection attacks
6. **Logging**: Log all API access for debugging and audit trails

### Current Implementation (Development)

- CORS allows all origins (unsafe for production)
- No authentication (safe if behind firewall)
- No rate limiting
- WebSocket commands validated against known actions

---

## 11. Implementation Checklist

### Phase 9A: API Foundation (1-2 days)
- [ ] Create `src/api/` directory structure
- [ ] Implement FastAPI app factory (`app.py`)
- [ ] Create Pydantic models (`models/`)
- [ ] Implement dependency injection (`dependencies.py`)

### Phase 9B: REST Endpoints (2-3 days)
- [ ] Implement zone endpoints (`routes/zones.py`)
- [ ] Implement animation endpoints (`routes/animations.py`)
- [ ] Implement color endpoints (`routes/colors.py`)
- [ ] Implement system endpoints (`routes/system.py`)
- [ ] Add error handling middleware

### Phase 9C: WebSocket Real-Time (2 days)
- [ ] Implement WebSocket endpoint (`routes/websocket.py`)
- [ ] EventBus integration for broadcasting
- [ ] Client command handling
- [ ] Multi-client support

### Phase 9D: Integration & Testing (1 day)
- [ ] Modify `main_asyncio.py` to start FastAPI server
- [ ] Update `requirements.txt`
- [ ] Manual testing with curl/Postman
- [ ] WebSocket client testing
- [ ] OpenAPI documentation verification

### Total Effort: 28-32 hours (3.5-4 days)

---

## 12. Success Criteria

✅ FastAPI server starts successfully alongside existing asyncio loop
✅ All REST endpoints functional and tested
✅ WebSocket real-time updates working (hardware change → all clients notified instantly)
✅ OpenAPI documentation accessible at `/api/docs`
✅ Zero changes to existing services/controllers
✅ Error handling robust (validation, 404s, 500s handled gracefully)
✅ API latency <50ms for all endpoints
✅ Support concurrent WebSocket clients (10+)
✅ Graceful shutdown (cleanups pending saves, closes connections)

---

## 13. Future Integration Points

### Phase 10: Frontend (React)
- Consume REST API for initial data load
- WebSocket for real-time state synchronization
- Use OpenAPI spec to generate TypeScript types

### Phase 11: Advanced Features
- Color palettes/themes API endpoints
- Scene save/load API
- Animation preview generation
- Performance dashboard

### Future: External Integrations
- MQTT bridge (publish state changes, receive commands)
- Home Assistant integration
- Google Home / Alexa voice control
- Mobile app support

---

## 14. Technical Notes

### Why Uvicorn Inside Asyncio Loop?
The main Diuna application runs on asyncio event loop. Uvicorn also uses asyncio. Running Uvicorn as a background task (`await server.serve()`) keeps them on the same event loop, avoiding thread/process complexity.

### ServiceContainer Pattern Benefits
By injecting `ServiceContainer` into the FastAPI app, we:
1. Keep API layer decoupled from specific services
2. Enable easy testing (mock entire container)
3. Maintain single source of truth for dependencies
4. Support future API variations without service changes

### Serialization Strategy
The `Serializer` class from Phase 8C is reused:
- `zone_to_dict()` converts domain models to API responses
- `dict_to_color()` converts API requests to domain models
- All enum conversions in one place (no duplication)

### EventBus Integration
API can publish `WEB_COMMAND` events (already defined but unused):
- Existing handlers process API commands
- No coupling between API and services
- Maintains event-driven architecture pattern

---

## Appendix: Full Example Flow

### User Changes Color via REST API

```
1. Frontend (React) sends:
   PUT /api/zones/FLOOR/color
   {"color": {"mode": "HUE", "hue": 240}}

2. API Route Handler (zones.py):
   - Deserializes to ZoneUpdateRequest (Pydantic validation)
   - Converts "FLOOR" string → ZoneID.FLOOR enum
   - Converts color dict → Color object (Serializer.dict_to_color)

3. ZoneService:
   - Updates zone.state.color
   - Calls DataAssembler.save() (debounced)

4. FrameManager (next render cycle):
   - Reads updated zone color
   - Renders pixel data
   - Outputs to WS2811 LEDs

5. Middleware:
   - EventBus publishes ZONE_STATE_CHANGED event
   - WebSocket route broadcasts to all connected clients

6. Frontend (React):
   - Receives WebSocket update
   - Updates UI state
   - Re-renders color picker
```

### User Starts Animation via WebSocket

```
1. Frontend (React) sends via WebSocket:
   {"action": "start_animation", "animation_id": "COLOR_CYCLE"}

2. WebSocket Handler:
   - Validates command type and parameters
   - Publishes WEB_COMMAND event to EventBus

3. LEDController (subscribes to WEB_COMMAND):
   - Routes to animation_mode_controller.start_animation()

4. AnimationModeController:
   - Calls AnimationService.set_current()
   - Calls AnimationEngine.start()

5. AnimationEngine:
   - Captures old frame
   - Starts new animation
   - Submits PixelFrames to FrameManager
   - Renders to LEDs

6. EventBus:
   - Publishes ANIMATION_STARTED event

7. WebSocket:
   - Broadcasts to all clients
   - All frontends see animation running
```

---

**Document Status**: Ready for implementation
**Last Review**: 2025-11-17
**Next Phase**: Phase 10 (Frontend Application)
