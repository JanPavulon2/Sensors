# Diuna Project - Claude Configuration

## Project Overview

**Diuna** is a Raspberry Pi-based LED control system featuring real-time animation rendering, zone-based LED management, and a web interface for control.

| Aspect | Details |
|--------|---------|
| Platform | Raspberry Pi 4 (Linux) |
| Backend | Python 3.9+ with asyncio |
| Frontend | React 18 + TypeScript + Vite |
| API | FastAPI + Socket.IO (port 8000) |
| Target FPS | 60 Hz rendering |

---

## Directory Structure

```
diuna/
├── src/                          # Python backend
│   ├── main_asyncio.py           # Entry point
│   ├── api/                      # FastAPI + Socket.IO
│   │   ├── routes/               # REST endpoints
│   │   ├── socketio/             # WebSocket handlers
│   │   ├── schemas/              # Pydantic DTOs
│   │   └── middleware/           # Auth, error handling
│   ├── animations/               # Animation implementations
│   │   ├── engine.py             # Animation task manager
│   │   ├── base.py               # BaseAnimation class
│   │   ├── breathe.py            # Breathe animation
│   │   ├── color_snake.py        # Color snake animation
│   │   └── ...
│   ├── controllers/              # Business logic
│   │   └── led_controller/       # Main orchestrator
│   │       ├── lighting_controller.py
│   │       ├── static_mode_controller.py
│   │       └── animation_mode_controller.py
│   ├── engine/                   # Rendering engine
│   │   ├── frame_manager.py      # Priority queue rendering
│   │   └── zone_render_state.py  # Per-zone render buffers
│   ├── services/                 # Core services
│   │   ├── event_bus.py          # Pub-sub events
│   │   ├── zone_service.py       # Zone state management
│   │   ├── animation_service.py  # Animation metadata
│   │   ├── transition_service.py # LED transitions
│   │   └── service_container.py  # DI container
│   ├── models/                   # Data models
│   │   ├── enums.py              # All enums
│   │   ├── frame.py              # Frame types
│   │   ├── color.py              # Color model
│   │   ├── domain/               # Zone, Animation, Application
│   │   └── animation_params/     # Parameter classes
│   ├── managers/                 # Configuration managers
│   │   ├── config_manager.py     # YAML loading
│   │   ├── color_manager.py      # Color presets
│   │   └── hardware_manager.py   # Hardware config
│   ├── hardware/                 # Hardware abstraction
│   │   ├── gpio/                 # GPIO management
│   │   ├── led/                  # WS281x strip driver
│   │   └── input/                # Encoders, buttons, keyboard
│   ├── config/                   # YAML configuration
│   └── state/                    # Persistent state (state.json)
│
└── frontend/                     # React frontend
    └── src/
        ├── main.tsx              # Entry point
        ├── App.tsx               # Router setup
        ├── pages/                # Dashboard, Settings, Debug
        ├── features/             # Feature modules
        │   ├── zones/            # Zone management (main feature)
        │   ├── animations/       # Animation controls
        │   └── logger/           # System logging
        ├── shared/
        │   ├── api/client.ts     # Axios HTTP client
        │   ├── websocket/        # Socket.IO client
        │   ├── types/domain/     # TypeScript interfaces
        │   └── ui/               # Radix UI components
        └── realtime/socket.ts    # Socket.IO initialization
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  Socket.IO Client ←→ REST API Client (Axios)                   │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    API LAYER (FastAPI + Socket.IO)              │
│  /api/v1/zones/*  │  zones:snapshot  │  zone:snapshot          │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                              │
│  ZoneService │ AnimationService │ EventBus │ TransitionService │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                     CONTROLLER LAYER                            │
│  LightingController → StaticModeController                      │
│                     → AnimationModeController                   │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                     ENGINE LAYER                                │
│  FrameManager (priority queues) → AnimationEngine (per-zone)   │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    HARDWARE LAYER                               │
│  LedChannel → WS281xStrip → GPIO (18: 12V, 19: 5V)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Enums (src/models/enums.py)

```python
# Zone identifiers
ZoneID: FLOOR, CIRCLE, LAMP, GATE, PIXEL, PIXEL2, MATRIX

# Render modes
ZoneRenderMode: STATIC, ANIMATION

# Animation types
AnimationID: BREATHE, COLOR_FADE, SNAKE, COLOR_SNAKE

# Frame priorities (higher = wins)
FramePriority: IDLE=0, MANUAL=10, ANIMATION=20, PULSE=30, TRANSITION=40, DEBUG=50

# Color modes
ColorMode: HUE, PRESET, RGB

# Hardware
LEDStripID: MAIN_12V (GPIO 18), AUX_5V (GPIO 19)
```

---

## Core Components

### FrameManager (`src/engine/frame_manager.py`)
Central rendering engine with priority-based frame queue.

**Key methods:**
- `push_frame(frame)` - Submit SingleZoneFrame, MultiZoneFrame, or PixelFrame
- `_drain_frames()` - Merge frames by priority (ANIMATION base + overlays)
- `_render_to_all_led_channels()` - Write to hardware

**Frame flow:**
```
Animation/Static/Transition → push_frame() → Priority Queues →
_drain_frames() → _render_frame() → LED Hardware (60 FPS)
```

### EventBus (`src/services/event_bus.py`)
Pub-sub event system with middleware support.

**Usage:**
```python
bus.subscribe(EventType.ZONE_SNAPSHOT_UPDATED, handler, priority=10)
await bus.publish(ZoneSnapshotUpdatedEvent(snapshot))
```

### AnimationEngine (`src/animations/engine.py`)
Manages per-zone animation tasks.

**Pattern:** One animation instance = one zone = one asyncio.Task

```python
await engine.start_for_zone(zone_id, animation_id)  # Spawn task
await engine.stop_for_zone(zone_id)                 # Cancel task
```

### ServiceContainer (`src/services/service_container.py`)
Dependency injection container passed to controllers.

```python
@dataclass
class ServiceContainer:
    event_bus: EventBus
    zone_service: ZoneService
    animation_service: AnimationService
    frame_manager: FrameManager
    color_manager: ColorManager
    # ...
```

---

## API Endpoints

### REST (prefix: `/api/v1`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| PUT | `/zones/{id}/brightness` | Set brightness (0-100) |
| PUT | `/zones/{id}/color` | Set color (HUE/PRESET/RGB) |
| PUT | `/zones/{id}/is-on` | Set power state |
| PUT | `/zones/{id}/render-mode` | Switch STATIC/ANIMATION |
| PUT | `/zones/{id}/animation` | Set animation ID |
| PUT | `/zones/{id}/animation/parameters` | Update animation params |
| GET | `/animations` | List all animations |
| GET | `/system/health` | Health check |

### Socket.IO Events

**Server → Client:**
- `zones:snapshot` - All zones (on connect)
- `zone:snapshot` - Single zone update
- `tasks:all` - All background tasks
- `logs:history` - Recent log entries

**Client → Server:**
- `task_get_all` - Request all tasks
- `logs_request_history` - Request log history

---

## Frontend Architecture

### State Management (Hybrid)

1. **Zones** - `useSyncExternalStore` + Socket.IO
   - Real-time updates via `zones:snapshot` events
   - File: `features/zones/realtime/zones.store.ts`

2. **Initial Fetch** - React Query
   - REST API for initial data load
   - File: `features/zones/api/queries.ts`

3. **Design System** - Zustand (experimental)
   - Theme, color control state
   - File: `future-design/store/designStore.ts`

### Key Frontend Files

| File | Purpose |
|------|---------|
| `shared/api/client.ts` | Axios instance with auth interceptor |
| `realtime/socket.ts` | Socket.IO connection |
| `features/zones/` | Zone management feature |
| `pages/Dashboard.tsx` | Main dashboard |

---

## Configuration Files (src/config/)

| File | Purpose |
|------|---------|
| `zones.yaml` | Zone definitions (pixel counts, GPIO mapping) |
| `hardware.yaml` | LED strip configs (WS2811/WS2812, color order) |
| `zone_mapping.yaml` | Zone → Hardware strip mapping |
| `colors.yaml` | Color presets and cycling order |
| `animations.yaml` | Animation metadata |

---

## Code Style Rules

### 1. All Rendering Through FrameManager
```python
# WRONG - never call strip.show() directly
strip.show()

# CORRECT - submit frame to FrameManager
frame_manager.push_frame(SingleZoneFrame(zone_id=ZoneID.FLOOR, color=color))
```

### 2. Constructor Injection Only
```python
# WRONG
service.frame_manager = frame_manager

# CORRECT
def __init__(self, frame_manager: FrameManager):
    self.frame_manager = frame_manager
```

### 3. Imports at Top of File
```python
# WRONG
def func():
    from models.enums import ZoneID  # inline import

# CORRECT
from models.enums import ZoneID

def func():
    ...
```

### 4. Type Hints Required
```python
async def set_color(self, zone_id: ZoneID, color: Color) -> None:
    ...
```

### 5. Async-First Patterns
- Use `async def` for I/O operations
- Always `await` async calls
- Cancel tasks in cleanup
- Use `asyncio.create_task()` for fire-and-forget

---

## Common Tasks

### Start the application
```bash
cd src && python main_asyncio.py
```

### Run frontend dev server
```bash
cd frontend && npm run dev
```

### Add a new animation
1. Create class in `src/animations/` extending `BaseAnimation`
2. Add to `ANIMATIONS` dict in `src/animations/engine.py`
3. Add entry in `src/config/animations.yaml`

### Add a new zone
1. Add to `src/config/zones.yaml`
2. Add to `src/config/zone_mapping.yaml`
3. Add enum value to `ZoneID` in `src/models/enums.py`

### Modify zone state
```python
# Via ZoneService
zone_service.set_color(ZoneID.FLOOR, Color.from_hue(180))
zone_service.set_brightness(ZoneID.FLOOR, 80)
zone_service.set_render_mode(ZoneID.FLOOR, ZoneRenderMode.ANIMATION)
```

---

## Data Models Quick Reference

### Color (`src/models/color.py`)
```python
Color.from_hue(180)                    # HUE mode (0-360)
Color.from_preset("warm_white", cm)    # PRESET mode
Color.from_rgb(255, 100, 0)            # RGB mode
color.to_rgb()                         # Always returns (r, g, b)
color.with_brightness(80)              # Apply brightness (0-100)
```

### Frame Types (`src/models/frame.py`)
```python
SingleZoneFrame(zone_id, color, priority, source)      # One zone, one color
MultiZoneFrame(zone_colors={...}, priority, source)    # Many zones, one color each
PixelFrame(zone_pixels={...}, priority, source)        # Many zones, pixel arrays
```

### Zone State (`src/models/domain/zone.py`)
```python
@dataclass
class ZoneState:
    id: ZoneID
    color: Color
    brightness: int        # 0-100
    is_on: bool
    mode: ZoneRenderMode   # STATIC or ANIMATION
    animation: Optional[AnimationState]
```

---

## Persistence

- **State file:** `src/state/state.json`
- **Pattern:** Debounced saves (500ms) via `ApplicationStateService`
- **On startup:** `DataAssembler` loads state and builds domain objects
