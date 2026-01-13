---
Last Updated: 2025-11-26
Version: 1.0.0
Status: Architectural Design Phase
Document Type: Migration & Architecture Plan
---

# Diuna LED System - FluentAPI Migration & Backend API Architecture

## Executive Summary

This document outlines the comprehensive architectural plan for evolving the Diuna LED System backend to support full-featured REST/WebSocket APIs while maintaining the mature, type-safe rendering engine. The plan covers:

1. **FastAPI-based REST API design** - Clean, fluent, RESTful interface to all backend capabilities
2. **Real-time communication strategy** - Hybrid WebSocket/REST for optimal UX
3. **State synchronization patterns** - Bidirectional state sync with reconciliation
4. **Implementation roadmap** - Phased migration minimizing disruption
5. **Integration with existing architecture** - Leveraging Phase 6's solid foundation

---

## 🎯 Strategic Goals

### Primary Objectives
- ✅ **Expose backend capabilities** through a professional, well-designed API
- ✅ **Enable real-time control** with <50ms latency (currently achieved by architecture)
- ✅ **Maintain type safety** across frontend-backend boundary
- ✅ **Support multiple clients** (React app, mobile apps, external tools, CLI)
- ✅ **Future-proof design** - ready for mobile, embedded, and third-party integrations
- ✅ **Zero breaking changes** to core rendering engine

### Phase Timeline
- **Phase 8 (Current):** Backend refinement & API layer foundation
- **Phase 9 (Next):** Frontend MVP with full API integration
- **Phase 10+:** Advanced features, ecosystem expansion

---

## 📐 Architecture Overview

### Layered API Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENTS                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ React App   │  │ Mobile App  │  │ External Tools   │   │
│  │ (WebSocket) │  │ (REST+WS)   │  │ (REST/CLI)       │   │
│  └─────────────┘  └─────────────┘  └──────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                   API GATEWAY LAYER                         │
│  ┌────────────────┐      ┌──────────────────────────────┐  │
│  │ REST API       │      │ WebSocket Server             │  │
│  │ (FastAPI)      │      │ (Socket.IO with fallback)   │  │
│  │ - Fluent URLs  │      │ - Real-time events          │  │
│  │ - Validation   │      │ - State streaming           │  │
│  │ - Auth/RBAC    │      │ - Frame delivery (60 FPS)   │  │
│  └────────────────┘      └──────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                   API SERVICE LAYER                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Service Facade                                       │  │
│  │ - ZoneService        - AnimationService             │  │
│  │ - ColorService       - TransitionService            │  │
│  │ - SystemService      - PresetService                │  │
│  │ - ConfigService      - DiagnosticsService           │  │
│  └──────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│               DOMAIN / BUSINESS LOGIC LAYER                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Controllers (Existing Phase 6 Architecture)         │  │
│  │ - LEDController      - AnimationEngine              │  │
│  │ - StaticModeController  - TransitionService         │  │
│  │ - PowerToggleController - EventBus                  │  │
│  │ - ManualModeController  - FrameManager              │  │
│  └──────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│              HARDWARE ABSTRACTION LAYER                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - ZoneStrip / WS281xStrip                           │  │
│  │ - GPIO Infrastructure                               │  │
│  │ - Hardware Frame Rendering                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **FastAPI over Flask/Django** | Clean, modern, native async support, type hints, minimal overhead | Better than traditional frameworks for real-time systems |
| **WebSocket Primary, REST Secondary** | Real-time updates critical for 60 FPS rendering; REST for CRUD & commands | Low latency (~10ms vs 50ms HTTP round trip) |
| **Socket.IO over raw WebSocket** | Auto-reconnection, fallbacks (polling), better browser compat, binary support | Production-grade stability |
| **Hybrid command/stream pattern** | Commands go via REST (atomic, transactional); streams via WebSocket (real-time) | Clear separation of concerns |
| **No API-to-rendering coupling** | API layer is facade only; core rendering untouched | Maintains Phase 6 architecture integrity |
| **Type-safe serialization** | Enums as strings in JSON, custom serializers for Color objects | Frontend ↔ Backend type safety |

---

## 🏗️ REST API Design (FastAPI Pattern)

### Architecture Philosophy

The REST API follows **fluent resource hierarchies** with clear separation:
- **Resource endpoints** for state querying & CRUD
- **Action endpoints** for commands and triggers
- **Stream endpoints** for real-time data
- **Query parameters** for filtering, pagination, control

### API Endpoint Structure

#### **Base URL Pattern**
```
/api/v1/{resource}/{id}/{sub-resource}/{action}
```

#### **Zone Management**

```
GET    /api/v1/zones
       → List all zones with current state

GET    /api/v1/zones/{zone_id}
       → Get single zone details

PUT    /api/v1/zones/{zone_id}
       → Update zone (color, brightness, enabled)
       Body: { "color": {...}, "brightness": 200 }

PUT    /api/v1/zones/{zone_id}/color
       → Update zone color (fluent interface)
       Body: { "color": {...} }

PUT    /api/v1/zones/{zone_id}/brightness
       → Update zone brightness
       Body: { "brightness": 150 }

POST   /api/v1/zones/{zone_id}/reset
       → Reset zone to default state

PUT    /api/v1/zones/{zone_id}/enabled
       → Toggle zone on/off
       Body: { "enabled": true }
```

**Response Format:**
```json
{
  "id": "FLOOR",
  "name": "Floor Strip",
  "pixel_count": 45,
  "state": {
    "color": {
      "mode": "HUE",
      "hue": 240,
      "brightness": 200
    },
    "enabled": true,
    "animation_active": false
  },
  "gpio": 18,
  "layout": null
}
```

#### **Animation Control**

```
GET    /api/v1/animations
       → List all available animations
       Query: ?active=true (filter active only)

GET    /api/v1/animations/{animation_id}
       → Get animation definition & schema

POST   /api/v1/animations/{animation_id}/start
       → Start animation
       Body: { "zones": ["FLOOR", "LAMP"], "params": {...} }

POST   /api/v1/animations/{animation_id}/stop
       → Stop animation

PUT    /api/v1/animations/{animation_id}/parameters
       → Update running animation parameters
       Body: { "speed": 2.0, "color_primary": {...} }

GET    /api/v1/animations/active
       → List currently running animations
```

**Response Format:**
```json
{
  "id": "BREATHE",
  "name": "Breathe",
  "description": "Gentle fade in/out effect",
  "parameters": {
    "speed": {
      "type": "float",
      "min": 0.1,
      "max": 10.0,
      "default": 1.0
    },
    "color_primary": {
      "type": "color",
      "default": { "mode": "RGB", "rgb": [255, 0, 0] }
    }
  },
  "zones": ["FLOOR", "LAMP"],
  "running": false
}
```

#### **Color Management**

```
GET    /api/v1/colors/presets
       → List color presets (RED, BLUE, etc.)

POST   /api/v1/colors/convert
       → Convert between color modes
       Body: { "from_color": {...}, "to_mode": "HSV" }

GET    /api/v1/colors/palettes
       → List color palettes

GET    /api/v1/colors/palettes/{palette_id}
       → Get palette details

POST   /api/v1/colors/palettes
       → Create custom palette

GET    /api/v1/colors/harmonies/{base_color}
       → Get color harmonies (complementary, etc.)
```

#### **System Control & Status**

```
GET    /api/v1/system/status
       → Get system health & metrics

GET    /api/v1/system/performance
       → Performance metrics (FPS, frame time, power)

POST   /api/v1/system/power/on
       → Turn on system

POST   /api/v1/system/power/off
       → Turn off system
       Body: { "transition": "FADE", "duration": 2.0 }

GET    /api/v1/system/modes
       → List available main modes

PUT    /api/v1/system/mode
       → Switch main mode
       Body: { "mode": "ANIMATION", "transition": "FADE" }

GET    /api/v1/system/brightness
       → Get global brightness

PUT    /api/v1/system/brightness
       → Set global brightness
       Body: { "brightness": 200 }
```

### HTTP Status Codes & Error Handling

```
200 OK              - Request successful
201 Created         - Resource created (presets, etc.)
204 No Content      - Request successful, no response body
400 Bad Request     - Validation error
401 Unauthorized    - Auth required
404 Not Found       - Resource not found
409 Conflict        - Invalid state transition
422 Unprocessable   - Semantic error
500 Server Error    - Unexpected error
503 Unavailable     - Hardware error
```

**Error Response Format:**
```json
{
  "error": {
    "code": "INVALID_COLOR_MODE",
    "message": "Color mode 'XYZ' is not supported",
    "details": {
      "field": "color.mode",
      "supported": ["RGB", "HSV", "HUE", "PRESET"]
    },
    "timestamp": "2025-11-26T10:30:00Z"
  }
}
```

---

## 🔌 WebSocket Real-Time Communication

### Connection & Protocol

**Connection Establishment:**
```typescript
// Client side
const socket = io('ws://localhost:8000', {
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  auth: {
    token: localStorage.getItem('auth_token')
  }
});
```

### Message Types & Patterns

#### **1. State Streaming Events** (Server → Client, 60 FPS)

**Frame Update** - Complete pixel state for canvas rendering
```json
{
  "event": "frame:update",
  "data": {
    "timestamp": 1732596600.123,
    "frame_number": 12345,
    "zones": {
      "FLOOR": [[255, 0, 0], [255, 10, 0], [255, 20, 0]],
      "LAMP": [[0, 255, 0], [0, 250, 0]]
    },
    "performance": {
      "fps": 60,
      "frame_time_ms": 16.7
    }
  }
}
```

**Zone State Change**
```json
{
  "event": "zone:state_changed",
  "data": {
    "zone_id": "FLOOR",
    "state": {
      "color": { "mode": "HUE", "hue": 240 },
      "brightness": 200,
      "enabled": true
    },
    "timestamp": "2025-11-26T10:30:00Z"
  }
}
```

#### **2. Commands** (Client → Server)

**Zone Update Command**
```json
{
  "event": "zone:set_color",
  "data": {
    "zone_id": "FLOOR",
    "color": { "mode": "HUE", "hue": 240 }
  }
}
```

**Animation Control**
```json
{
  "event": "animation:start",
  "data": {
    "animation_id": "BREATHE",
    "zones": ["FLOOR", "LAMP"],
    "parameters": {
      "speed": 1.5,
      "color_primary": { "mode": "RGB", "rgb": [255, 0, 0] }
    }
  }
}
```

---

## 🔄 State Synchronization Strategy

### Synchronization Model

**Hybrid approach:**
1. **Authoritative Server** - Backend is single source of truth
2. **Optimistic Updates** - Frontend updates UI immediately
3. **Eventual Consistency** - WebSocket brings frontend in sync
4. **Reconciliation** - Conflict detection & resolution

### Flow Diagram

```
User Action (Frontend)
    ↓
[Optimistic Update] - Update UI immediately
[Fire Command] - Send via WebSocket (no await)
    ↓ (parallel)
[WebSocket Command] → Backend processes
    ↓
Backend validates & applies
    ↓
[Broadcast Event] → All clients receive true state
    ↓
[Reconcile State] - Compare with optimistic, apply deltas
```

---

## 📦 API Service Layer Design

### Service Facade Pattern

```python
# services/zone_service.py
class ZoneService:
    def __init__(
        self,
        zone_controller: ZoneStripController,
        event_bus: EventBus,
        config: ConfigManager
    ):
        self.zone_controller = zone_controller
        self.event_bus = event_bus
        self.config = config

    async def get_all_zones(self) -> List[ZoneDTO]:
        """Get all zones with current state"""
        zones = self.config.zones
        return [self._zone_to_dto(z) for z in zones]

    async def update_zone_color(
        self,
        zone_id: ZoneID,
        color: Color
    ) -> ZoneDTO:
        """Update zone color"""
        await self.zone_controller.set_zone_color(zone_id, color)

        self.event_bus.publish(
            ZoneColorChangedEvent(zone_id=zone_id, color=color)
        )

        zone = self.config.get_zone(zone_id)
        return self._zone_to_dto(zone)
```

---

## 📁 Project Structure (API Layer)

```
src/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app setup
│   ├── routes/
│   │   ├── zones.py         # Zone endpoints
│   │   ├── animations.py    # Animation endpoints
│   │   ├── colors.py        # Color endpoints
│   │   ├── system.py        # System endpoints
│   │   └── presets.py       # Preset endpoints
│   ├── models/
│   │   ├── request.py       # Request DTOs
│   │   ├── response.py      # Response DTOs
│   │   └── websocket.py     # WebSocket message models
│   ├── middleware/
│   │   ├── auth.py          # Authentication middleware
│   │   └── error_handler.py # Global error handling
│   └── websocket/
│       ├── server.py        # WebSocket server setup
│       ├── handlers.py      # Event handlers
│       └── broadcaster.py   # State broadcasting
├── services/
│   ├── zone_service.py      # Zone business logic
│   ├── animation_service.py # Animation business logic
│   ├── color_service.py     # Color utilities
│   ├── system_service.py    # System control
│   └── preset_service.py    # Preset management
└── main_asyncio.py          # Application entry point (MODIFIED)
```

---

## 🚀 Implementation Roadmap

### Phase 8.1: Foundation (Week 1-2)
**Goal:** API server framework & basic endpoints

- [ ] FastAPI project setup with proper structure
- [ ] Basic authentication (JWT tokens)
- [ ] Zone management endpoints (GET, PUT)
- [ ] Error handling middleware
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Dependency injection setup

**Deliverable:** Working REST API for zone control

### Phase 8.2: WebSocket Layer (Week 3)
**Goal:** Real-time communication infrastructure

- [ ] Socket.IO server setup
- [ ] Connection/authentication handlers
- [ ] Command handlers (zone, animation, system)
- [ ] State broadcasting system
- [ ] Subscription management
- [ ] Connection resilience (reconnect, fallback)

**Deliverable:** Real-time WebSocket communication

### Phase 8.3: Complete API Coverage (Week 4-5)
**Goal:** All endpoints implemented

- [ ] Animation endpoints (list, start, stop, parameters)
- [ ] Color endpoints (convert, presets, harmonies)
- [ ] System endpoints (status, mode, brightness, power)
- [ ] Preset management (save, load, export, import)
- [ ] Configuration endpoints (zones, hardware)
- [ ] Diagnostics endpoints (logs, tests)

**Deliverable:** Full API coverage for all backend features

### Phase 8.4: Testing & Polish (Week 6)
**Goal:** Robust, production-ready API

- [ ] Integration tests (API + backend)
- [ ] WebSocket reliability tests
- [ ] Error scenario handling
- [ ] Performance optimization
- [ ] Rate limiting & security hardening
- [ ] Documentation completion

**Deliverable:** Production-ready API server

### Phase 9: Frontend Integration (Parallel)
**Goal:** React app uses API

- [ ] WebSocket integration (React)
- [ ] REST API calls (Axios)
- [ ] State synchronization (Zustand)
- [ ] Real-time canvas updates
- [ ] Error handling & retry logic
- [ ] Loading states & skeleton screens

**Deliverable:** Fully functional Diuna App

---

## 🔄 Migration Path from Current System

### Breaking Changes: NONE
All API layer is **additive only**. Existing Phase 6 architecture remains untouched.

### Integration Points

```python
# main_asyncio.py - Modified to include API

async def main():
    # Existing Phase 6 setup
    config_manager = ConfigManager()
    event_bus = EventBus()
    frame_manager = FrameManager(event_bus)
    led_controller = LEDController(config_manager, event_bus, frame_manager)
    animation_engine = AnimationEngine(frame_manager, event_bus)

    # NEW: API layer
    api_server = FastAPIServer(
        port=8000,
        led_controller=led_controller,
        event_bus=event_bus,
        frame_manager=frame_manager
    )

    # NEW: WebSocket broadcaster
    broadcaster = StateBroadcaster(sio, event_bus)

    # Run all together
    await asyncio.gather(
        led_controller.start(),      # Existing
        animation_engine.start(),    # Existing
        frame_manager.render_loop(), # Existing
        api_server.start(),          # NEW
        broadcaster.start()          # NEW
    )
```

---

## 📊 Performance Metrics & Optimization

### Target Performance

| Metric | Target | Notes |
|--------|--------|-------|
| **Frame Rate** | 60 FPS | No degradation expected |
| **Command Latency** | <50ms | WebSocket excellent |
| **WebSocket FPS** | 60 FPS | Monitor throughput |
| **Memory Overhead** | <50MB | API + WebSocket conn cost |
| **CPU Impact** | <5% additional | Measure with profiler |

### Optimization Strategies

**1. Frame Transmission Optimization**
- Use MessagePack for binary encoding (~70% smaller than JSON)
- Compress frame data before transmission
- Implement subscription filtering (only send relevant updates)

**2. Rate Limiting**
- Frame updates: 60 FPS (can be throttled per client if needed)
- Status updates: 1 Hz
- Event updates: Immediate (but debounced)

---

## 🛡️ Error Handling & Recovery

### Error Categories

**1. Validation Errors** (4xx) - Invalid parameters, out-of-range values
**2. State Errors** (409 Conflict) - Start already-running animation, invalid transitions
**3. Hardware Errors** (503 Service Unavailable) - GPIO failure, LED disconnected
**4. Server Errors** (5xx) - Unexpected exceptions

### Recovery Mechanisms

**Connection Drop:** Queue commands locally, replay on reconnect
**Partial State Loss:** Request full state snapshot
**Hardware Failure:** Broadcast error, attempt recovery

---

## ✅ Success Criteria

**API is ready for production when:**

✅ All endpoints tested and documented
✅ WebSocket connection stable (99.9% uptime in testing)
✅ <50ms command latency verified
✅ Error handling comprehensive
✅ Security review passed
✅ Performance benchmarks met
✅ Frontend successfully integrated
✅ Documentation complete
✅ No breaking changes to core system

---

## 🔗 Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Project overview & code style
- [architecture/rendering-system.md](../architecture/rendering-system.md) - Core rendering architecture
- [frontend/FRONTEND_AGENT_GUIDE.md](./FRONTEND_AGENT_GUIDE.md) - Frontend specifications

---

**Document Status:** ✅ Ready for Implementation Review
**Next Step:** Architecture review with team → Begin Phase 8.1
