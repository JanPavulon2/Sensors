# Diuna LED Control System — Project Overview

**Date:** 2026-02-23
**Purpose:** Real-time multi-zone LED animation system for Raspberry Pi with web interface

---

## What It Does

Diuna controls up to 140+ individually addressable WS2811/WS2812 LEDs organized into **independent zones** (Floor, Circle, Pixel strips, LED matrices). Each zone can:

- Display **static colors** (HUE wheel, RGB, or named presets like "warm_white")
- Run **procedural animations** (breathe, color fade, snake, rainbow, color snake)
- Adjust **brightness** (0-100%) independently
- Be powered **on/off** with smooth fade transitions
- Switch between **STATIC** and **ANIMATION** render modes dynamically

The system renders at **60 FPS** with priority-based frame compositing, streams live pixel data to a web interface at **30 FPS**, and persists all zone states across reboots.

**Current Active Zones:**
- FLOOR: 18 pixels (WS2811 12V strip, GPIO 18)
- CIRCLE: 14 pixels (WS2811 12V strip, GPIO 18)
- PIXEL: 30 pixels (WS2812 5V strip, GPIO 19)
- PIXEL2: 30 pixels (WS2812 5V strip, GPIO 19)
- MATRIX: 48 pixels (WS2812 5V strip, GPIO 19)

---

## Architecture Overview

### Core Design Principles

1. **Event-Driven:** EventBus decouples all components (pub-sub pattern with priority handlers)
2. **Priority-Based Rendering:** FrameManager merges frames from multiple sources using priority queues
3. **One Animation Per Zone:** Each animation runs as an independent asyncio.Task
4. **No Optimistic Updates:** Backend is always source of truth; frontend reflects actual hardware state
5. **Dependency Injection:** ServiceContainer holds all services; passed to controllers/API

### System Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + TypeScript)                │
│  - Dashboard: Zone grid, edit panel, frame visualizer          │
│  - Real-time: Socket.IO → useSyncExternalStore                 │
│  - Commands: REST API (PUT /zones/{id}/color, /brightness...)  │
└─────────────────────────────────────────────────────────────────┘
                              ↕ HTTP + Socket.IO
┌─────────────────────────────────────────────────────────────────┐
│                   API LAYER (FastAPI + Socket.IO)               │
│  - REST: Zone updates (color, brightness, power, render mode)  │
│  - Socket.IO Events:                                            │
│    • Server→Client: zones:snapshot, zone:snapshot,             │
│                     output_frame, log:entry, tasks:all          │
│    • Client→Server: task_get_all, logs_request_history         │
└─────────────────────────────────────────────────────────────────┘
                              ↕ EventBus (pub-sub)
┌─────────────────────────────────────────────────────────────────┐
│                        DOMAIN SERVICES                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐      │
│  │ ZoneService │  │ AnimService  │  │ AppStateService  │      │
│  │ (state CRUD)│  │ (anim state) │  │ (state.json I/O) │      │
│  └─────────────┘  └──────────────┘  └──────────────────┘      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ EventBus: pub-sub with priority + middleware            │  │
│  │  - Subscribers: 50+ handlers across all layers          │  │
│  │  - Middleware: logging, filtering                       │  │
│  │  - History: circular buffer (last 100 events)           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ SnapshotPublisher: domain events → Socket.IO            │  │
│  │  - Listens: ZONE_STATIC_STATE_CHANGED,                  │  │
│  │             ZONE_RENDER_MODE_CHANGED,                    │  │
│  │             ZONE_ANIMATION_CHANGED, etc.                 │  │
│  │  - Emits: ZoneSnapshotUpdatedEvent                      │  │
│  │  - Broadcasted via Socket.IO to all connected clients   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↕ push_frame()
┌─────────────────────────────────────────────────────────────────┐
│                      RENDERING PIPELINE                         │
│                                                                  │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐            │
│  │   Static   │  │  Animation  │  │  Transition  │            │
│  │   Mode     │  │   Engine    │  │   Service    │            │
│  │ Controller │  │  (per-zone  │  │   (fades)    │            │
│  └──────┬─────┘  │   tasks)    │  └──────┬───────┘            │
│         │        └──────┬──────┘         │                     │
│         └───────────────┼────────────────┘                     │
│                         │ push_frame(priority, source)         │
│                  ┌──────▼───────┐                               │
│                  │ FrameManager │                               │
│                  │  60fps loop  │                               │
│                  └──────┬───────┘                               │
│                         │                                        │
│         Priority Queues (per-zone):                             │
│         IDLE(0) < MANUAL(10) < ANIMATION(20) < PULSE(30)       │
│                < TRANSITION(40) < DEBUG(50)                     │
│                         │                                        │
│         _drain_frames() → merge by priority → render            │
│                         │                                        │
│              ┌──────────┼──────────┐                            │
│              ↓                     ↓                             │
│       ┌────────────┐        ┌────────────┐                     │
│       │ LedChannel │        │ LedChannel │                     │
│       │ MAIN_12V   │        │ AUX_5V     │                     │
│       │ GPIO 18    │        │ GPIO 19    │                     │
│       └────────────┘        └────────────┘                     │
│              │                     │                             │
│              └──────────┬──────────┘                            │
│                         │ WS281x DMA transfer (2.75ms)          │
│                         ↓                                        │
│              ┌─────────────────────┐                            │
│              │ Physical LED Strips │                            │
│              │ 140+ total pixels   │                            │
│              └─────────────────────┘                            │
│                         │                                        │
│                         │ OutputFrame (t, zones→pixels)         │
│                         ↓                                        │
│                  ┌──────────────┐                               │
│                  │FrameStreamer │                               │
│                  │ → Socket.IO  │                               │
│                  │ /frames ns   │                               │
│                  │ @30fps       │                               │
│                  └──────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Systems Explained

### 1. Rendering Pipeline (60 FPS Priority System)

**Problem:** Multiple systems want to control LEDs simultaneously (animations, transitions, static colors, debug overlays).

**Solution:** `FrameManager` maintains per-zone priority queues. Every frame source submits frames with a priority:

- **IDLE (0):** Black screen / no source
- **MANUAL (10):** User-set static colors
- **ANIMATION (20):** Running animations (breathe, snake, rainbow)
- **PULSE (30):** Edit mode indicator (pulsing selected zone)
- **TRANSITION (40):** Smooth fades (startup/shutdown/mode switches)
- **DEBUG (50):** Debug overlays (highest priority)

**Render Loop (60 FPS):**
1. `_drain_frames()`: Merge all queued frames by priority (highest wins)
2. Build `OutputFrame` with final pixel data
3. Write to hardware via `led_channel.show()` (DMA transfer, 2.75ms)
4. Push `OutputFrame` to `FrameStreamer` for Socket.IO broadcast

**Why priority queues?**
- Animations submit frames continuously
- Transitions temporarily override with high-priority fades
- When transition ends, rendering automatically falls back to animation
- No explicit handoff needed — priority determines what renders

**Frame expiration:** Frames have TTL (time-to-live) and expire if not refreshed, preventing stale data from rendering.

---

### 2. Animation Engine (Per-Zone Task Management)

**Architecture:** One animation instance = one zone = one `asyncio.Task`

**How it works:**
1. User sets zone to ANIMATION mode and selects animation (e.g., "BREATHE")
2. `AnimationEngine.start_for_zone(zone_id, animation_id)`:
   - Instantiates animation class (e.g., `BreatheAnimation`)
   - Spawns `asyncio.Task` running `animation.run()`
   - Stores task reference in `self.running_animations[zone_id]`
3. Animation's `run()` loop:
   ```python
   async def run(self) -> AsyncIterator[BaseFrame]:
       self.running = True
       while self.running:
           frame = await self.step()  # Compute next frame
           if frame:
               yield frame
   ```
4. AnimationEngine feeds frames to FrameManager:
   ```python
   async for frame in animation.run():
       frame_manager.push_frame(frame)
   ```
5. Stopping: `animation.stop()` sets `self.running = False`, task exits cleanly

**Why asyncio.Tasks?**
- Each zone animates independently
- Easy cancellation on mode switch
- Automatic cleanup via `TaskRegistry`
- No threading complexity

**Animations:**
- `BreatheAnimation`: Sine wave brightness pulsing
- `ColorFadeAnimation`: Smooth hue cycling (0→360°)
- `SnakeAnimation`: Moving pixel segment
- `ColorSnakeAnimation`: Rainbow-colored moving segment
- `RainbowAnimation`: Full spectrum across strip

---

### 3. Event Bus (Decoupled Pub-Sub)

**Why it exists:** Decouple components so ZoneService doesn't need to know about Socket.IO, animations don't need to know about state persistence, etc.

**How it works:**
```python
# Subscriber (e.g., SnapshotPublisher)
event_bus.subscribe(
    EventType.ZONE_STATIC_STATE_CHANGED,
    self._on_zone_changed,
    priority=10
)

# Publisher (e.g., ZoneService.set_color())
await event_bus.publish(
    ZoneStaticStateChangedEvent(zone_id=ZoneID.FLOOR, color=new_color)
)
```

**Features:**
- **Priority-based execution:** High-priority handlers run first
- **Filtering:** Per-handler filter functions (e.g., only handle encoder events from "selector" source)
- **Middleware:** Logging middleware logs all events
- **Fault tolerance:** One handler crash doesn't stop others
- **History:** Circular buffer (last 100 events) for debugging

**Event Flow Example (user sets zone color):**
1. API endpoint calls `zone_service.set_color(zone_id, color)`
2. ZoneService updates internal state
3. Publishes `ZoneStaticStateChangedEvent`
4. **3 subscribers react:**
   - `ApplicationStateService`: Debounced save to `state.json`
   - `SnapshotPublisher`: Builds `ZoneSnapshotDTO`, publishes `ZoneSnapshotUpdatedEvent`
   - `StaticModeController`: Pushes new color frame to FrameManager
5. `ZoneSnapshotUpdatedEvent` triggers:
   - `ZoneBroadcaster`: Emits `zone:snapshot` via Socket.IO
6. Frontend receives `zone:snapshot`, updates `zones.store.ts`, UI re-renders

---

### 4. Real-Time Frontend Updates (Socket.IO → useSyncExternalStore)

**Goal:** Reflect hardware state changes in UI with zero manual polling.

**How it works:**

**Backend (Python):**
```python
# SnapshotPublisher listens to domain events
await event_bus.subscribe(EventType.ZONE_STATIC_STATE_CHANGED, on_zone_changed)

async def on_zone_changed(event):
    snapshot = ZoneSnapshotDTO.from_zone(zone)
    await event_bus.publish(ZoneSnapshotUpdatedEvent(snapshot))

# ZoneBroadcaster listens to snapshot events
await sio.emit("zone:snapshot", asdict(snapshot))
```

**Frontend (TypeScript):**
```typescript
// zones.socket.ts: Listen to Socket.IO events
socket.on('zone:snapshot', (data: ZoneSnapshot) => {
  updateZoneSnapshot(data);  // Update store
});

// zones.store.ts: useSyncExternalStore
let zones: Record<string, ZoneSnapshot> = {};
const listeners = new Set<() => void>();

export function updateZoneSnapshot(zone: ZoneSnapshot) {
  zones = { ...zones, [zone.id]: zone };
  listeners.forEach(l => l());  // Notify all subscribers
}

export function useZones(): ZoneSnapshot[] {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

// Dashboard.tsx: Automatic re-render on updates
const zones = useZones();  // Re-renders when Socket.IO updates arrive
```

**Why `useSyncExternalStore`?**
- React 18 built-in primitive for external state
- Zero dependencies (no Zustand/Redux overhead for zone state)
- Tearing-safe (SSR-ready)
- Minimal re-renders (subscribers only re-render on actual changes)

**No optimistic updates:**
- User clicks "Set brightness to 80%"
- API call sent, UI shows loading state
- Backend updates state, emits `zone:snapshot`
- Socket.IO update triggers re-render with **actual hardware state**
- UI reflects what LEDs are actually showing

---

### 5. State Persistence (Debounced JSON)

**File:** `src/state/state.json`

**How it works:**
```python
# ApplicationStateService
def __init__(self):
    self._save_debouncer = Debouncer(delay_ms=500)  # 500ms debounce

async def _on_zone_changed(self, event):
    # Don't save on every event — debounce rapid changes
    self._save_debouncer.trigger(self._save_state)

async def _save_state(self):
    state = build_application_state()
    with open('state/state.json', 'w') as f:
        json.dump(serialize(state), f, indent=2)
```

**What gets saved:**
- Zone colors (HUE/PRESET/RGB with values)
- Brightness levels (0-100)
- Power states (is_on: true/false)
- Render modes (STATIC/ANIMATION)
- Active animations (animation_id + parameters)

**On startup:**
1. `DataAssembler` loads `state.json`
2. Merges with `factory_defaults.yaml` (fill missing fields)
3. Builds domain objects (`ZoneCombined`, `AnimationState`)
4. `LightingController` restores states:
   - Applies static colors for STATIC zones
   - Starts animations for ANIMATION zones
   - Runs fade-in transition from black

---

### 6. Transition System (Smooth Fades)

**Why it exists:** Instant LED changes are jarring. Transitions provide smooth visual feedback.

**Presets:**
- `STARTUP`: 2-second fade from black to saved state
- `SHUTDOWN`: 600ms fade to black
- `MODE_SWITCH`: 400ms fade when switching STATIC↔ANIMATION
- `POWER_TOGGLE`: 400ms fade for on/off

**How it works:**
```python
async def fade_to_new_state(self, new_state_setter, config: TransitionConfig):
    # 1. Capture current LED state
    start_pixels = led_channel.get_all_pixels()

    # 2. Apply new state (static color / start animation)
    await new_state_setter()

    # 3. Capture target state
    await asyncio.sleep(0.05)  # Let animation produce first frame
    end_pixels = led_channel.get_all_pixels()

    # 4. Interpolate with HIGH PRIORITY frames
    for step in range(config.steps):
        progress = step / config.steps
        interpolated = lerp(start_pixels, end_pixels, progress)
        frame_manager.push_frame(
            PixelFrame(zones=interpolated, priority=FramePriority.TRANSITION)
        )
        await asyncio.sleep(config.duration_ms / config.steps / 1000)
```

**Why high priority?**
- Transition frames override animations during fade
- Once fade completes, animation frames render normally
- No manual cleanup needed — priority system handles it

---

## User Features (Frontend)

### Dashboard Page

**Zone Grid:**
- Live zone cards with:
  - Power switch (on/off with fade)
  - Pixel count badge
  - Render mode indicator (STATIC/ANIMATION)
  - Compact LED preview (shows live colors)
  - Edit button → opens edit panel

**Frame Visualizer:**
- Real-time pixel stream (@30fps)
- All zones displayed simultaneously
- FPS control slider (adjust streaming rate)
- Play/pause/stop controls
- Frame metadata (time, zone count, actual FPS)

### Zone Edit Panel (Modal)

**Appearance Section:**
- **Brightness slider** (0-100%) with live preview
- **Color mode tabs:**
  - **HUE:** 360° color wheel picker (saturation = 100%)
  - **PRESET:** Grid of named colors (warm_white, cool_white, red, blue, etc.)
  - **RGB:** Individual R/G/B sliders (future)

**Animation Section:**
- Animation selector dropdown
- **Dynamic parameter form** (changes based on selected animation):
  - Breathe: Speed (0.1-5.0x), Intensity (0-100%)
  - Color Fade: Speed, Saturation
  - Snake: Speed, Length (pixels), Primary Hue
  - Rainbow: Speed, Saturation
- Parameters update live via Socket.IO

**Navigation:**
- Prev/Next zone buttons (keyboard arrows supported)
- Zone counter (e.g., "2 of 5")
- Close button / ESC key

### Debug Page

**Tasks Tab:**
- All asyncio.Tasks with:
  - Category (ANIMATION, RENDERING, API, SYSTEM)
  - Status (RUNNING, COMPLETED, FAILED)
  - Duration, start time
- Filters: all / running / completed / failed
- Search by task name

**Logs Tab:**
- Streaming system logs via Socket.IO
- Filters by category (CONFIG, HARDWARE, ANIMATION, etc.) and level (DEBUG, INFO, WARN, ERROR)
- Circular buffer (1000 entries, localStorage-backed)
- Auto-scroll toggle

**State Tab:**
- JSON tree viewer of application state
- Collapsible nodes
- Live updates via Socket.IO

---

## Communication Protocols

### REST API (Mutations)

**All endpoints prefixed with `/api/v1`**

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| PUT | `/zones/{id}/brightness` | `{brightness: 0-100}` | `200 OK` |
| PUT | `/zones/{id}/color` | `{mode: "HUE", hue: 180}` | `200 OK` |
| PUT | `/zones/{id}/is-on` | `{is_on: true}` | `200 OK` |
| PUT | `/zones/{id}/render-mode` | `{mode: "ANIMATION"}` | `200 OK` |
| PUT | `/zones/{id}/animation` | `{animation_id: "BREATHE"}` | `200 OK` |
| PUT | `/zones/{id}/animation/parameters` | `{speed: 1.5, intensity: 80}` | `200 OK` |
| GET | `/animations` | - | `[{id, name, params}, ...]` |
| GET | `/system/health` | - | `{status: "healthy"}` |
| GET/PUT | `/frames/target-fps` | `{fps: 60}` | `{fps: 60}` |

**Pattern:** Frontend sends command → Backend updates state → EventBus publishes → Socket.IO broadcasts → UI updates

### Socket.IO Events (Real-Time)

**Server → Client (namespace: `/`):**
- `zones:snapshot` — Full zone list (sent on connect)
- `zone:snapshot` — Single zone update (sent on any zone change)
- `log:entry` — Single log line
- `logs:history` — Historical log batch (on request)
- `tasks:all` — All asyncio.Tasks (on request)

**Server → Client (namespace: `/frames`):**
- `output_frame` — Rendered frame data (30 FPS stream)
  ```json
  {
    "t": 123.456,  // Timestamp (app clock)
    "zones": {
      "FLOOR": [[255,0,0], [255,0,0], ...],  // 18 RGB triplets
      "CIRCLE": [[0,255,0], [0,255,0], ...]  // 14 RGB triplets
    }
  }
  ```

**Client → Server:**
- `task_get_all` — Request all tasks
- `logs_request_history` — Request log history

**Connection handling:**
- Auto-reconnect on disconnect
- Initial state sync on connect (`zones:snapshot`)
- Heartbeat/ping (Socket.IO default)

---

## Hardware Details

### LED Strips

**MAIN_12V (GPIO 18):**
- Type: WS2811 12V strip (external power supply)
- Zones: FLOOR (18px), CIRCLE (14px)
- Total: 32 pixels
- Color order: RGB
- Signal: 800kHz PWM via DMA

**AUX_5V (GPIO 19):**
- Type: WS2812B 5V strip (USB power)
- Zones: PIXEL (30px), PIXEL2 (30px), MATRIX (48px)
- Total: 108 pixels
- Color order: GRB
- Signal: 800kHz PWM via DMA

**DMA Transfer Timing:**
- 140 pixels × 24 bits/pixel = 3,360 bits
- @ 800kHz = 4.2ms transfer + 50µs reset = **4.25ms min frame time**
- Theoretical max FPS: ~235
- Target: **60 FPS** (16.67ms/frame, plenty of headroom)

### GPIO Configuration

- GPIO 18: PWM0, DMA channel 10
- GPIO 19: PWM1, DMA channel 10 (shared DMA controller)
- Pull resistors: None (external pull-down on data lines)
- Drive strength: 8mA (default)

---

## Configuration Files (src/config/)

| File | Purpose | Example |
|------|---------|---------|
| `zones.yaml` | Zone definitions | `FLOOR: {pixel_count: 18, order: 1}` |
| `hardware.yaml` | LED strip hardware | `MAIN_12V: {type: WS2811, gpio: 18, color_order: RGB}` |
| `zone_mapping.yaml` | Zone → strip mapping | `FLOOR: {strip: MAIN_12V, offset: 0}` |
| `colors.yaml` | Color presets | `warm_white: {rgb: [255,147,41], category: white}` |
| `animations.yaml` | Animation metadata | `BREATHE: {name: "Breathe", params: [speed, intensity]}` |
| `parameters.yaml` | Parameter schemas | `speed: {type: float, min: 0.1, max: 5.0, default: 1.0}` |
| `factory_defaults.yaml` | Default zone states | `default_brightness: 80, default_mode: STATIC` |

---

## Startup Sequence (main_asyncio.py)

1. **Logger init:** Configure category-based logger with LogLevel.DEBUG
2. **Load configs:** `ConfigManager` loads all YAML files from `src/config/`
3. **Create managers:** `ColorManager` (preset RGB cache), `HardwareManager` (LED strip configs), `AnimationManager`
4. **Platform detection:** `RuntimeInfo.is_raspberry_pi()` → real GPIO vs mock
5. **Hardware init:**
   - `create_gpio_manager()` → `GPIOManagerHardware` or `GPIOManagerMock`
   - `HardwareCoordinator.initialize()` → creates LED channels (GPIO 18 + 19)
6. **Service layer:**
   - `EventBus` with logging middleware
   - `ZoneService`, `AnimationService`, `ApplicationStateService`
   - `DataAssembler.load_state()` → builds domain objects from `state.json` + configs
7. **Rendering:**
   - `FrameManager` starts 60fps render loop
   - `AppClock` (monotonic time for animations)
   - `FrameStreamer` (30fps Socket.IO output)
8. **Dependency injection:** Build `ServiceContainer` with all services
9. **Controllers:**
   - `AnimationEngine`
   - `LightingController` → `StaticModeController` + `AnimationModeController`
   - `SnapshotPublisher` (domain events → Socket.IO)
10. **API server:**
    - `create_app()` → FastAPI with CORS
    - `create_socketio_server()` → AsyncServer
    - `register_socketio()` → wire event handlers
11. **Lifecycle:**
    - Register shutdown handlers (LEDs, animations, API, GPIO, tasks)
    - `TaskRegistry.create_tracked_task()` for all background tasks
12. **Start services:**
    - uvicorn server (port 8000)
    - Keyboard input adapter
    - Control panel (encoders + buttons, if hardware present)
13. **Restore state:**
    - For STATIC zones: `StaticModeController.apply_zone_color()`
    - For ANIMATION zones: `AnimationEngine.start_for_zone()`
14. **Startup transition:** 2-second fade from black to current state

---

## Tech Stack Summary

| Layer | Tech |
|-------|------|
| **Backend** | Python 3.11 + asyncio |
| **API** | FastAPI (REST) + python-socketio (WebSocket) |
| **Frontend** | React 18 + TypeScript + Vite |
| **State** | useSyncExternalStore (zones), Zustand (logs, tasks) |
| **UI** | Radix UI primitives + Tailwind CSS |
| **Hardware** | rpi_ws281x (DMA-driven PWM) |
| **Config** | YAML (zones, hardware, colors, animations) |
| **Persistence** | JSON (state.json, debounced writes) |
| **Logging** | Category-based Python logger → Socket.IO stream |
| **Deployment** | Systemd service on Raspberry Pi OS |

---

## Design Philosophy

1. **Hardware-first:** System is optimized for 60Hz LED rendering, not web performance
2. **No silent failures:** All errors propagate to UI (connection status, API errors)
3. **Observable:** Everything is logged (events, frame metrics, task lifecycle)
4. **Testable:** Mock GPIO/LED drivers for development on non-Pi hardware
5. **Extensible:** Adding animations = create class + register in `ANIMATIONS` dict
6. **Deterministic:** No race conditions via priority queues + single event bus
7. **Debuggable:** Frame visualizer, task monitor, log viewer, event history

---

## Known Constraints

- **DMA transfer time:** 4.25ms minimum (cannot exceed ~235 FPS)
- **Socket.IO bandwidth:** Frame streaming limited to 30 FPS (avoid saturating WebSocket)
- **Priority inversion:** Transition frames block animations (by design)
- **Single GPIO controller:** Both LED strips share DMA channel 10 (sequential writes)
- **No concurrent writes:** `led_channel.show()` is blocking (hardware constraint)
- **No SSR:** Frontend requires browser with WebSocket support
- **No authentication:** API is public (Raspberry Pi on local network)

