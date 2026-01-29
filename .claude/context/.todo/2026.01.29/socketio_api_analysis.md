# Socket.IO API Analysis

**Date:** 2026-01-29
**Author:** Claude Code Analysis
**Scope:** `src/api/socketio/` and `src/api/socketio_handler.py`

---

## 1. File Inventory

### Main Handler
| File | Lines | Status |
|------|-------|--------|
| `src/api/socketio_handler.py` | 225 | **Active** - Main orchestration |

### Modular Structure (`src/api/socketio/`)
| File | Lines | Status |
|------|-------|--------|
| `registry.py` | 15 | **Active** - Registration orchestrator |
| `server.py` | 15 | **Unused** - Duplicate of handler's factory |
| `lifecycle.py` | 2 | **Empty** - Placeholder |
| `__init__.py` | 2 | **Empty** |

### Zones Module (`zones/`)
| File | Lines | Status |
|------|-------|--------|
| `on_connect.py` | 10 | **Duplicate** - connect handler also in main |
| `dto.py` | 60 | **Active** - DTOs used by both handlers |
| `__init__.py` | 2 | **Empty** |

### Logs Module (`logs/`)
| File | Lines | Status |
|------|-------|--------|
| `broadcaster.py` | 35 | **Active** - Registers log streaming |
| `handlers.py` | 2 | **Empty** - Placeholder |
| `__init__.py` | 2 | **Empty** |

### Tasks Module (`tasks/`)
| File | Lines | Status |
|------|-------|--------|
| `broadcaster.py` | 39 | **Duplicate** - Same handlers as main |
| `handlers.py` | 2 | **Empty** - Placeholder |
| `__init__.py` | 2 | **Empty** |

### Frames Module (`frames/`)
| File | Lines | Status |
|------|-------|--------|
| `streamer.py` | 2 | **Empty** - Future feature |
| `__init__.py` | 2 | **Empty** |

---

## 2. What Each File Does

### `socketio_handler.py` (Main Handler)
**Purpose:** Central Socket.IO management

**Components:**
- `SocketIOHandler` class - Singleton managing server and event subscriptions
- `create_socketio_server()` - Factory function with CORS configuration
- `wrap_app_with_socketio()` - ASGI middleware wrapper

**Event Handlers Registered:**
- `connect` - Sends initial zone snapshots, logs client IP
- `disconnect` - Logs disconnection
- `task_get_all` - Returns all tasks
- `task_get_active` - Returns active tasks
- `task_get_stats` - Returns task statistics
- `task_get_tree` - Returns task hierarchy
- `logs_request_history` - Returns recent logs

**EventBus Integration:**
- Subscribes to `ZONE_SNAPSHOT_UPDATED`
- Broadcasts `zone:snapshot` on zone state changes

### `registry.py`
**Purpose:** Orchestrates registration of all Socket.IO modules

**Flow:**
```python
async def register_socketio(sio, services):
    await socketio_handler.setup(sio, services)  # Main handler
    register_zone_on_connect(sio, services)       # Duplicate connect!
    register_logs(sio)                            # Log broadcaster
    register_tasks(sio)                           # Duplicate task handlers!
```

### `zones/on_connect.py`
**Purpose:** Send zone snapshots on client connect

**Problem:** This registers a `connect` event handler, but `socketio_handler.py` already registers one (lines 69-86). The second registration **overwrites** the first, losing:
- Client IP logging
- Services availability check
- Disconnect logging

### `zones/dto.py`
**Purpose:** Data Transfer Objects for zone state

**Classes:**
- `AnimationStateSnapshotDTO` - Animation ID and parameters
- `ZoneSnapshotDTO` - Full zone state with color RGB values

**Status:** Properly used, well-designed.

### `logs/broadcaster.py`
**Purpose:** Connect LogBroadcaster to Socket.IO server

**What it does:**
1. Gets LogBroadcaster singleton
2. Sets Socket.IO server reference
3. Registers `logs_request_history` handler

**Problem:** The `logs_request_history` handler is ALSO registered in `socketio_handler.py` (lines 144-161). Duplicate registration.

### `tasks/broadcaster.py`
**Purpose:** Task inspection via Socket.IO

**Handlers:**
- `task_get_all`
- `task_get_active`
- `task_get_stats`

**Problem:** ALL THREE handlers are duplicated in `socketio_handler.py` (lines 93-141). The modular version also **misses** `task_get_tree` handler.

### `server.py`
**Purpose:** Factory for AsyncServer

**Problem:** This is a duplicate of `create_socketio_server()` in `socketio_handler.py`. The modular version lacks:
- CORS origin defaults
- Logging setup comments
- Log message on creation

**Status:** Never imported, completely unused.

---

## 3. Duplicate/Obsolete Code Identified

### Critical: Handler Overwrites

| Event | Defined In | Problem |
|-------|-----------|---------|
| `connect` | `socketio_handler.py:70` | Overwritten by `zones/on_connect.py:7` |
| `connect` | `zones/on_connect.py:7` | Simpler version, loses IP logging |
| `task_get_all` | `socketio_handler.py:94` | Overwritten by `tasks/broadcaster.py:15` |
| `task_get_active` | `socketio_handler.py:107` | Overwritten by `tasks/broadcaster.py:24` |
| `task_get_stats` | `socketio_handler.py:119` | Overwritten by `tasks/broadcaster.py:33` |
| `task_get_tree` | `socketio_handler.py:132` | **Missing** in modular version! |
| `logs_request_history` | `socketio_handler.py:145` | Overwritten by `logs/broadcaster.py:21` |

### Empty Placeholder Files (8 files)
```
src/api/socketio/__init__.py
src/api/socketio/lifecycle.py
src/api/socketio/zones/__init__.py
src/api/socketio/logs/__init__.py
src/api/socketio/logs/handlers.py
src/api/socketio/tasks/__init__.py
src/api/socketio/tasks/handlers.py
src/api/socketio/frames/__init__.py
src/api/socketio/frames/streamer.py
```

### Unused Files (1 file)
```
src/api/socketio/server.py  # Duplicate factory, never imported
```

---

## 4. Architecture Opinion

### What's Good

1. **Event-driven design** - Zone changes flow through EventBus, decoupled from transport
2. **DTO pattern** - Clean serialization with `ZoneSnapshotDTO`
3. **Async throughout** - Proper use of async/await
4. **Log streaming architecture** - Non-blocking queue in LogBroadcaster
5. **Single entry point** - `register_socketio()` provides clear initialization

### What's Wrong

1. **Incomplete modularization** - Started breaking apart `socketio_handler.py` into modules but didn't finish. Result: duplicate handlers everywhere.

2. **Handler overwrites** - Socket.IO's `@sio.event` decorator REPLACES previous handlers with same name. The registration order in `registry.py`:
   ```python
   await socketio_handler.setup(sio, services)  # Registers handlers
   register_zone_on_connect(sio, services)       # OVERWRITES connect
   register_logs(sio)                            # OVERWRITES logs_request_history
   register_tasks(sio)                           # OVERWRITES task handlers
   ```

3. **Lost functionality** - The modular `connect` handler loses:
   - Client IP logging
   - Services availability guard
   - Debug logging

4. **Inconsistent error handling** - Main handler sends `error` events on exceptions, modular versions just log and silently fail.

5. **Empty scaffolding** - 8 empty files suggest planned features never implemented (lifecycle hooks, frame streaming).

6. **Single Responsibility violation** - `socketio_handler.py` handles:
   - Server creation
   - App wrapping
   - Event bus subscription
   - Connection events
   - Task inspection
   - Log history

   This should be split properly.

### Severity Assessment

| Issue | Severity | Impact |
|-------|----------|--------|
| Duplicate handlers | **HIGH** | Unexpected behavior, lost features |
| Missing `task_get_tree` in modular | **MEDIUM** | Feature available via main, but inconsistent |
| Empty files | **LOW** | Code clutter, confusing |
| Unused `server.py` | **LOW** | Dead code |

---

## 5. Recommended Fixes

### Option A: Keep Monolithic (Quick Fix)

Remove the modular overwriting - keep all handlers in `socketio_handler.py`.

**Changes:**
1. Edit `registry.py` to only call `socketio_handler.setup()` and `broadcaster.set_socketio_server()`
2. Delete duplicate event registrations from modular files
3. Remove empty placeholder files
4. Delete unused `server.py`

**Pros:** Minimal changes, fast
**Cons:** `socketio_handler.py` stays bloated

### Option B: Complete Modularization (Recommended)

Properly split responsibilities, remove handlers from `socketio_handler.py`.

**New Structure:**
```
src/api/socketio/
├── __init__.py           # Exports register_socketio
├── registry.py           # Orchestration only
├── handler.py            # SocketIOHandler class (EventBus subscription only)
├── connection.py         # connect/disconnect handlers (MERGED)
├── zones/
│   ├── __init__.py
│   ├── dto.py            # Keep as-is
│   └── handlers.py       # Zone-related handlers (none currently)
├── logs/
│   ├── __init__.py
│   └── handlers.py       # logs_request_history (MOVED here)
├── tasks/
│   ├── __init__.py
│   └── handlers.py       # All task handlers (MOVED here, add task_get_tree)
└── server.py             # Factory functions (CONSOLIDATE from handler.py)
```

**Key Principle:** Each event should be registered in exactly ONE place.

### Detailed Plan for Option B

1. **Create `connection.py`** - Merge both connect handlers:
   - Client IP logging (from main)
   - Services guard (from main)
   - Zone snapshot emission (from modular)
   - Disconnect handler

2. **Move task handlers to `tasks/handlers.py`**:
   - Move all 4 handlers from `socketio_handler.py`
   - Delete duplicate handlers from `tasks/broadcaster.py`
   - Rename `broadcaster.py` or delete if empty

3. **Move log handlers to `logs/handlers.py`**:
   - Move `logs_request_history` from `socketio_handler.py`
   - Keep `register_logs()` for `set_socketio_server()` call
   - Delete duplicate handler from `logs/broadcaster.py`

4. **Slim down `socketio_handler.py`**:
   - Keep only `SocketIOHandler` class with EventBus subscription
   - Move `create_socketio_server()` to `server.py`
   - Move `wrap_app_with_socketio()` to `server.py`

5. **Update `registry.py`**:
   - Import from new locations
   - Registration order no longer matters (no duplicates)

6. **Delete empty/unused files**:
   - `lifecycle.py` - empty
   - `frames/streamer.py` - empty
   - `frames/__init__.py` - empty (delete whole frames/ directory)

---

## 6. Implementation Priority

| Priority | Task | Effort |
|----------|------|--------|
| P0 | Fix duplicate `connect` handler (losing IP logging) | 15 min |
| P1 | Remove duplicate task/log handlers | 30 min |
| P2 | Complete modularization (Option B) | 2 hours |
| P3 | Delete empty scaffolding | 5 min |

---

## 7. Files to Modify/Delete

### Modify
- `src/api/socketio/registry.py` - Update registration
- `src/api/socketio_handler.py` - Remove duplicate handlers
- `src/api/socketio/zones/on_connect.py` - Merge with main connect
- `src/api/socketio/tasks/broadcaster.py` - Add `task_get_tree` or delete
- `src/api/socketio/logs/broadcaster.py` - Remove duplicate handler

### Delete
- `src/api/socketio/server.py` - Unused duplicate
- `src/api/socketio/lifecycle.py` - Empty
- `src/api/socketio/logs/handlers.py` - Empty
- `src/api/socketio/tasks/handlers.py` - Empty
- `src/api/socketio/frames/` - Entire directory (empty)

---

## 8. Summary

The Socket.IO API shows signs of an incomplete refactoring. Someone started extracting handlers into a modular structure (`zones/`, `logs/`, `tasks/`) but left the original handlers in place. Due to how Socket.IO's `@sio.event` decorator works, the modular handlers **overwrite** the originals, causing lost functionality (IP logging, error events).

**Immediate action needed:** Either complete the modularization properly or remove the modular duplicates. The current state causes silent bugs.
