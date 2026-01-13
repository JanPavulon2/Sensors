# WebAPI Endpoints Reference

Complete documentation of all REST API endpoints in the Diuna LED Control system.

**Last Updated:** 2025-12-28
**Base URL:** `/api/v1`

---

## Table of Contents

1. [System Endpoints](#system-endpoints)
2. [Animations Endpoints](#animations-endpoints)
3. [Zone Endpoints](#zone-endpoints)
4. [Logger Endpoints](#logger-endpoints)
5. [WebSocket Endpoints](#websocket-endpoints)
6. [Endpoint Usage Map](#endpoint-usage-map)

---

## System Endpoints

**Prefix:** `/api/v1/system`
**Route File:** `src/api/routes/system.py`

### GET /tasks/summary

Get high-level task summary.

**Response:**
```json
{
  "summary": "string",
  "total": 10,
  "active": 2,
  "failed": 0,
  "cancelled": 0
}
```

**Status:** Implemented | **Frontend Usage:** None

---

### GET /tasks

Get detailed information about all tracked tasks.

**Response:**
```json
{
  "count": 10,
  "tasks": [
    {
      "id": "uuid",
      "category": "LED_CONTROL",
      "description": "Animation frame rendering",
      "created_at": "2025-12-28T00:00:00Z",
      "created_by": "animation_engine",
      "status": "running",
      "error": null
    }
  ]
}
```

**Status:** Implemented | **Frontend Usage:** None

---

### GET /tasks/active

Get only currently running tasks.

**Response:**
```json
{
  "count": 2,
  "tasks": [
    {
      "id": "uuid",
      "category": "LED_CONTROL",
      "description": "Animation frame rendering",
      "created_at": "2025-12-28T00:00:00Z",
      "running_for_seconds": 12.34
    }
  ]
}
```

**Status:** Implemented | **Frontend Usage:** None

---

### GET /tasks/failed

Get tasks that ended with exceptions.

**Response:**
```json
{
  "count": 0,
  "tasks": [
    {
      "id": "uuid",
      "category": "LED_CONTROL",
      "description": "Animation frame rendering",
      "created_at": "2025-12-28T00:00:00Z",
      "error": "RuntimeError: Invalid animation",
      "error_type": "RuntimeError"
    }
  ]
}
```

**Status:** Implemented | **Frontend Usage:** None

---

### GET /health

Health check endpoint - Returns app health and task statistics.

**Response:**
```json
{
  "status": "healthy",
  "reason": null,
  "tasks": {
    "total": 10,
    "active": 2,
    "failed": 0,
    "cancelled": 0
  },
  "timestamp": "2025-12-28T00:00:00Z"
}
```

**Status:** Implemented | **Frontend Usage:** `useCheckBackendConnection()`, alternative to `/api/health`

---

## Animations Endpoints

**Prefix:** `/api/v1/animations`
**Route File:** `src/api/routes/animations.py`

### GET /

List all available animation definitions.

**Response:**
```json
{
  "animations": [
    {
      "id": "BREATHE",
      "display_name": "Breathe",
      "description": "Gradual color breathing effect",
      "parameters": ["ANIM_INTENSITY", "ANIM_HUE_OFFSET"]
    }
  ],
  "count": 9
}
```

**Status:** Implemented | **Frontend Usage:** `useAnimationsQuery()` → `GET /v1/system/animations`

**⚠️ Note:** Frontend still calls `/system/animations` - should update to `/animations` after migration

---

### GET /{animation_id}

Get detailed information about a specific animation.

**Parameters:**
- `animation_id` (path): Animation ID (e.g., "BREATHE", "SNAKE", "COLOR_CYCLE")

**Response:**
```json
{
  "id": "BREATHE",
  "display_name": "Breathe",
  "description": "Gradual color breathing effect",
  "parameters": ["ANIM_INTENSITY", "ANIM_HUE_OFFSET"]
}
```

**Errors:**
- `404`: Animation not found

**Status:** Implemented | **Frontend Usage:** None (direct calls)

---

## Zone Endpoints

**Prefix:** `/api/v1/zones`
**Route File:** `src/api/routes/zones.py`

### GET /

Get all zones with current state.

**Response:**
```json
{
  "zones": [
    {
      "id": "FLOOR",
      "name": "Floor LEDs",
      "pixel_count": 120,
      "state": {
        "color": { "mode": "HUE", "rgb": [255, 0, 0] },
        "brightness": 255,
        "is_on": true,
        "render_mode": "STATIC",
        "animation_id": null
      },
      "gpio": { "pin": 17 },
      "layout": null
    }
  ],
  "count": 1
}
```

**Status:** Implemented | **Frontend Usage:** `useZonesQuery()`

---

### GET /{zone_id}

Get single zone by ID.

**Parameters:**
- `zone_id` (path): Zone ID (e.g., "FLOOR", "WALL")

**Response:**
```json
{
  "id": "FLOOR",
  "name": "Floor LEDs",
  "pixel_count": 120,
  "state": { /* zone state */ },
  "gpio": { "pin": 17 },
  "layout": null
}
```

**Errors:**
- `404`: Zone not found

**Status:** Implemented | **Frontend Usage:** `useZoneQuery()`

---

### PUT /{zone_id}/color

Update zone color.

**Parameters:**
- `zone_id` (path): Zone ID

**Request Body:**
```json
{
  "mode": "HUE",
  "hue": 180,
  "rgb": null,
  "preset": null,
  "saturation": null,
  "brightness": null
}
```

**Response:** Updated zone with new color

**Status:** Implemented | **Frontend Usage:** `useUpdateZoneColorMutation()`

---

### PUT /{zone_id}/brightness

Update zone brightness.

**Parameters:**
- `zone_id` (path): Zone ID
- `brightness` (query/body): Brightness 0-255

**Response:** Updated zone with new brightness

**Status:** Implemented | **Frontend Usage:** `useUpdateZoneBrightnessMutation()`

---

### PUT /{zone_id}/is-on

Toggle zone power on/off.

**Parameters:**
- `zone_id` (path): Zone ID

**Request Body:**
```json
{
  "is_on": true
}
```

**Response:** Updated zone with new power state

**Status:** Implemented | **Frontend Usage:** `useToggleZonePowerMutation()`

---

### PUT /{zone_id}/render-mode

Switch zone between static color or animation.

**Parameters:**
- `zone_id` (path): Zone ID

**Request Body:**
```json
{
  "render_mode": "STATIC|ANIMATION",
  "animation_id": "BREATHE|SNAKE|COLOR_CYCLE|..."
}
```

**Valid Modes:**
- `STATIC`: Display static color (no animation)
- `ANIMATION`: Run animation (requires animation_id)

**Response:** Updated zone with new render mode

**Status:** Implemented | **Frontend Usage:** `useUpdateZoneAnimationMutation()`

**Note:** Replaces `/animation/start` and `/animation/stop` calls

---

### POST /{zone_id}/reset

Reset zone to default state.

**Parameters:**
- `zone_id` (path): Zone ID

**Response:** Updated zone reset to defaults

**Status:** Implemented | **Frontend Usage:** `useResetZoneMutation()`

---

### POST /{zone_id}/animation/start

Start animation on zone.

**Parameters:**
- `zone_id` (path): Zone ID

**Request Body:**
```json
{
  "animation_id": "BREATHE",
  "parameters": {
    "ANIM_INTENSITY": 50
  }
}
```

**Response:** Updated zone with animation running

**Status:** Implemented | **Frontend Usage:** Called via `useUpdateZoneAnimationMutation()` (indirect)

**⚠️ Note:** Consider using `PUT /render-mode` instead for consistency

---

### POST /{zone_id}/animation/stop

Stop animation on zone and switch to static color.

**Parameters:**
- `zone_id` (path): Zone ID

**Response:** Updated zone with animation stopped

**Status:** Implemented | **Frontend Usage:** Not directly used (uses render-mode instead)

**⚠️ Note:** Not currently called by frontend; use `PUT /render-mode` with STATIC instead

---

### PUT /{zone_id}/animation/parameters

Update animation parameters while running.

**Parameters:**
- `zone_id` (path): Zone ID

**Request Body:**
```json
{
  "parameters": {
    "ANIM_INTENSITY": 75,
    "ANIM_HUE_OFFSET": 180
  }
}
```

**Response:** Updated zone with new animation parameters

**Status:** Implemented | **Frontend Usage:** `useUpdateZoneAnimationParametersMutation()`

**⚠️ Path Mismatch:** Frontend calls `/animation-parameters` but backend defines `/animation/parameters`

---

## Logger Endpoints

**Prefix:** `/api/v1/logger`
**Route File:** `src/api/routes/logger.py`

### GET /levels

Get available log levels.

**Response:**
```json
{
  "levels": ["DEBUG", "INFO", "WARN", "ERROR"]
}
```

**Status:** Implemented | **Frontend Usage:** None

---

### GET /categories

Get available log categories.

**Response:**
```json
{
  "categories": [
    "SYSTEM", "API", "LED_CONTROL", "ANIMATION", "HARDWARE", ...
  ]
}
```

**Status:** Implemented | **Frontend Usage:** `useLogCategories()`

---

### GET /recent

Get recent logs (placeholder).

**Status:** Implemented (placeholder) | **Frontend Usage:** None

---

## WebSocket Endpoints

### WS /ws/logs

Stream real-time logs.

**Messages from server:**
```json
{
  "type": "connection:ready",
  "message": "Logger WebSocket ready for commands"
}
```

```json
{
  "type": "log:entry",
  "timestamp": "2025-12-28T00:00:00Z",
  "level": "INFO",
  "category": "SYSTEM",
  "message": "System started"
}
```

**Status:** Implemented | **Frontend Usage:** `useLoggerWebSocket()`

---

### WS /ws/tasks

Monitor real-time task status.

**Messages from server:**
```json
{
  "type": "connection:ready",
  "message": "Task WebSocket ready for commands"
}
```

```json
{
  "type": "task:created",
  "task": { /* task object */ }
}
```

**Status:** Implemented | **Frontend Usage:** `useTaskWebSocket()`

---

## Endpoint Usage Map

### By Frontend Feature

| Feature | Endpoints Used |
|---------|-----------------|
| Dashboard | `GET /zones` |
| Zone Control | `GET /zones`, `PUT /zones/{id}/color`, `PUT /zones/{id}/brightness`, `PUT /zones/{id}/is-on`, `PUT /zones/{id}/render-mode`, `POST /zones/{id}/reset` |
| Animation Selection | `GET /animations` or `GET /system/animations` |
| Animation Parameters | `PUT /zones/{id}/animation/parameters` |
| Debug Page | `GET /system/tasks`, WebSocket connections |
| Logger | `GET /logger/categories`, WebSocket `/ws/logs` |
| Task Monitor | WebSocket `/ws/tasks` |
| System Health | `GET /health` or `GET /system/health` |

---

## Critical Issues & TODO

### Issue 1: Animation Parameters Path Mismatch ⚠️
- **Backend:** `/api/v1/zones/{zone_id}/animation/parameters`
- **Frontend:** `/api/v1/zones/{zone_id}/animation-parameters`
- **Impact:** 404 errors when updating animation parameters
- **Fix:** Update frontend to use `/animation/parameters`

### Issue 2: Animation Endpoint Location Change
- **Old Location:** `GET /system/animations`
- **New Location:** `GET /animations`
- **Status:** Both work (old still in system.py, new in animations.py)
- **Action:** Update frontend to use `/animations` and remove old endpoint

### Issue 3: System Status Endpoint Missing
- **Frontend Hook:** `useSystemStatusQuery()` exists
- **Backend Endpoint:** `GET /system/status` NOT implemented
- **Impact:** Call will fail if used
- **Fix:** Either implement `/system/status` or remove unused hook

### Issue 4: Animation Stop Not Used
- **Endpoint:** `POST /zones/{id}/animation/stop` exists
- **Usage:** Not called by frontend
- **Impact:** Zone switching uses render-mode instead
- **Recommendation:** Either promote to primary method or deprecate

---

## Statistics

- **Total REST Endpoints:** 23
- **Total WebSocket Endpoints:** 2
- **Fully Used:** 15
- **Partially Used:** 3
- **Unused:** 5
- **Missing Implementation:** 1

**Coverage:** 87% of implemented endpoints are actively used
