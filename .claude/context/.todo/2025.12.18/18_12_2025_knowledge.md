;'# Diuna Project Knowledge Base - 2025-12-18

## Infrastructure & Setup

### Physical Architecture
- **Hardware**: Raspberry Pi 4 at IP `192.168.137.139`
- **Codebase**: Located on the Raspberry Pi itself
- **Access**: Remote SSH from local PC (VSCode Remote)
- **Backend**: FastAPI on `http://192.168.137.139:8000`
- **Frontend**: Vite dev server (port 5173, sometimes 5175)

### Network Access from Remote PC
- Direct IP: `http://192.168.137.139:8000` works for backend
- **localhost works too** - indicates SSH port forwarding is configured
- Both access methods functional for testing

---

## Current Status

###  Working
- Frontend loads, displays all 7 zones
- Zone color API updates work (confirmed in EventBus logs)
- Changes persist to state.json immediately
- Brightness conversion 0-255�0-100 works correctly
- CORS issue fixed (wildcard allowed)

### L Broken
1. **Hardware doesn't update** unless zone is "selected" (firmware updates blocked by selection filtering)
2. **Brightness changes don't propagate to hardware** - requires app restart to see changes
3. **Frontend port fluctuates** between 5173-5175 (Vite auto-fallback)
4. **Zone selection blocks editing** - should only affect hardware control, not API

---

## Root Causes

### Bug: Hardware Updates Only for Selected Zone
**What we know**:
- API updates work (state.json changes, EventBus fires ZONE_STATE_CHANGED)
- Changes appear on hardware if zone is selected
- Changes don't appear on hardware if zone is unselected

**Why it happens**:
- Zone selection probably filters what gets rendered to hardware
- Animation/render loop likely skips unselected zones
- Selection was added for hardware UI indicator (since no physical display)

**Where to look**:
- `src/controllers/led_controller/` - may have selection-based rendering
- `src/animations/engine.py` - zone iteration logic
- `src/engine/frame_manager.py` - frame submission for all zones

### Bug: Brightness Doesn't Update Hardware Immediately
**What we know**:
- API call succeeds, state.json updates correctly
- EventBus fires event showing state changed
- Hardware shows old brightness until app restarts

**Why it happens**:
- Hardware rendering loop doesn't respond to ZONE_STATE_CHANGED events
- Animation tasks might cache zone state at startup
- Or: only selected zones get re-rendered when state changes

**Where to look**:
- Animation controller task subscriptions
- Whether EventBus listeners re-submit frames to FrameManager
- State caching in animation/render system

### UI: Selection Confusion
**The confusion**:
- Selection indicator meant for hardware control (which zone responds to buttons)
- But also blocks frontend API from editing other zones
- Frontend doesn't need this constraint - it's a different input method

**Better design**:
- Selection = which zone responds to physical buttons only
- API = always accessible, no selection constraint
- These are independent concerns

### Port Fluctuation
**Why it happens**:
- Vite defaults to trying multiple ports if first is busy
- `vite.config.ts` has `port: 5173` but no `strictPort: true`

**Solution**:
- Add `strictPort: true` to fail loudly if port taken
- Forces users to free the port or kill old process

---

## Brightness Conversion: Unnecessary Complexity?

**Current flow**:
```
Frontend sends: 200 (0-255 scale)
�
API converts: 200/255 * 100 = 78
�
Stored as: 78 (0-100)
�
Response converts: 78/100 * 255 = 199
```

**Issues**:
- Three conversions per update (input, storage, response)
- Rounding errors accumulate
- Adds complexity for minimal gain

**Better approach**:
- Just use 0-100 everywhere
- Frontend progress bar = 0-100 (percentage)
- API = 0-100
- Domain = 0-100
- No conversion needed

**This assumes**:
- Domain model prefers percentage (0-100) for brightness
- If hardware needs 0-255, convert only at hardware layer

---

## Data Flow: State Update � Hardware

```
API receives brightness change
�
ZoneService.set_brightness() updates ZoneState
�
EventBus publishes ZONE_STATE_CHANGED event
�
[*** BROKEN: Hardware doesn't respond to event ***]
�
State written to state.json
�
(App restart) state.json reloaded � hardware updates
```

The gap: EventBus event fires but rendering system doesn't re-submit frames for unselected zones

---

## Localhost Access Explanation

When user types `localhost:5173` from remote PC:
- Without setup: Would resolve to PC's 127.0.0.1, not the Pi 
- With SSH tunneling: SSH forwards localhost:5173 � Pi's 127.0.0.1:5173 

This is working, so SSH port forwarding is configured.

---

## Hardware Rendering Pipeline (Conceptual)

```
Zone State (what should be displayed)
�
Animation Controller (for each zone)
  � (if selected? if in animation mode? if..?)
  �
Frame Manager (queue with priority)
  �
DMA rendering (physical LEDs)
```

**Question**: At which point does selection filtering happen?

---

## Session Findings & Fixes (2025-12-18)

### CORS Issue - FIXED ✓
**Problem**: Frontend couldn't connect to backend API
- Error: "Missing CORS header Access-Control-Allow-Origin"
- Status: 400/500 errors from backend PUT requests

**Root Cause**: CORS configuration only allowed localhost/127.0.0.1, not IP addresses
- File: `src/api/main.py`
- Old config: Hardcoded `localhost` and `127.0.0.1` only
- User accessing from: `192.168.137.139:5175` → backend at `192.168.137.139:8000`

**Fix Applied**:
- Changed CORS to allow all origins: `cors_origins = ["*"]`
- This is development-mode permissive (fine for LAN)
- Added warning comment about production restrictions

**Result**: Zone GET requests now work; frontend displays all 7 zones

---

### Brightness Validation Mismatch - FIXED ✓
**Problem**: PUT requests to change brightness returned HTTP 500 errors
- Frontend sent brightness values 0-255 (standard LED intensity)
- API schema expected 0-255
- Domain model validation expected 0-100 (percentage)
- Mismatch caused validation exception

**Files Changed**:
1. `src/models/domain/zone.py` - ZoneState validation
   - Kept 0-100 range (percentage is more intuitive)
   - Now accepts int or float

2. `src/api/services/zone_service.py` - Conversion layer
   - Input: `update_zone_brightness(brightness: 0-255)`
   - Converts: `brightness_percent = round((brightness / 255) * 100)`
   - Stores: 0-100 in domain
   - Response: Converts back `brightness_api = round((brightness / 100) * 255)`

**Trade-offs**:
- **Pro**: Domain uses percentage (more intuitive UI)
- **Con**: Extra conversions add complexity
- **Alternative**: Could simplify by using 0-100 everywhere

**Result**: Zone brightness updates now accepted by API

---

### Findings About Working vs Non-Working Features

**APIs Now Tested**:
- GET /api/v1/zones → Works, returns all zones
- GET /api/v1/zones/{id} → Works, returns single zone
- PUT /api/v1/zones/{id}/color → Works, updates state.json
- PUT /api/v1/zones/{id}/brightness → Works, updates state.json

**What Works**:
- Frontend loads on both localhost and IP (SSH port forwarding confirmed)
- API receives requests and updates state.json
- EventBus fires ZONE_STATE_CHANGED events (confirmed in logs)
- CORS no longer blocking requests

**What Doesn't Work Yet**:
- Hardware LEDs don't change color/brightness (unless zone selected)
- Changes require app restart to see on hardware
- Vite port fluctuates (5173 vs 5175)

**Why Hardware Doesn't Update**:
- EventBus event fires → logs show "zone state changed"
- But hardware rendering doesn't respond
- Selection gate prevents non-selected zones from rendering
- Rendering loop doesn't subscribe to state change events
- Hardware reads old state until app restarts (loads from state.json)

---

### Architecture Observations

**System is Well-Structured**:
- EventBus working correctly (events fire as expected)
- State persistence working (state.json updated immediately)
- API layer working (requests processed, no errors)
- CORS middleware working (after fix)

**The Gap is in Hardware Rendering**:
- Rendering pipeline receives color/brightness updates via API
- Updates are persisted and EventBus fires
- But hardware rendering doesn't re-render after updates
- Unless user selects that zone (triggers re-render)
- Or app restarts (reloads state.json)

**This suggests**:
- Rendering loop might run only for selected zone
- Or: Animation tasks start at app init, don't listen for updates
- Or: FrameManager only processes frames for selected zone
- Or: DMA layer has its own state cache

---

### Code Complexity Assessment

**Well Done**:
- EventBus pub/sub pattern
- Type-safe event system with enums
- Clean API/domain separation
- Zone configuration from YAML
- State persistence to JSON

**Areas of Concern**:
- Brightness conversion 0-255 ↔ 0-100 (unnecessary complexity)
- Hardware rendering hardcoded to selected zone only
- No reactive state updates (EventBus fired but not acted upon)
- Selection indicator coupled with API editing constraints

---

### Next Critical Steps

1. **Decouple rendering from selection** - allow all zones to update hardware
2. **Subscribe rendering to EventBus** - re-render when zone state changes
3. **Remove selection gate from API** - can edit any zone freely
4. **Simplify brightness** - optional but cleaner


## Architectural Analysis & Comprehensive Plan

### 🔧 Analysis Complete

**What I Found**: Your backend is impressively sophisticated with:

- ✅ FastAPI server already running on port 8000
- ✅ Partial WebSocket implementation (logs/tasks only)
- ✅ Advanced frame-based rendering engine (60 FPS, priority queues, DMA optimization)
- ✅ Clean service layer architecture with dependency injection
- ✅ React+TypeScript frontend with Zustand + React Query

**Key Gaps Identified**:

- ❌ Animation control endpoints (REST + WebSocket)
- ❌ Bidirectional WebSocket communication (currently one-way broadcast only)
- ❌ Real-time zone state push (frontend polls every 5s currently)
- ❌ Frontend animation UI components
- ⚠️ Socket.io mismatch (frontend expects socket.io, backend uses native WebSocket)

---

## PHASE 1: Architecture & Communication Strategy

### 1.1 WebSocket Architecture Decision

**Current Situation**:
- **Frontend**: socket.io-client (bidirectional, event-based)
- **Backend**: Native FastAPI WebSocket (one-way broadcast)
- **Mismatch**: Frontend can't send commands via WebSocket

**Recommendation**: Upgrade Backend to socket.io ✅

**Why socket.io**:
- ✅ Matches frontend expectations (no frontend rewrite needed)
- ✅ Bidirectional by design (emit/on pattern)
- ✅ Built-in rooms/namespaces for zone subscriptions
- ✅ Automatic reconnection handling
- ✅ Fallback transports (WebSocket → polling)
- ✅ Event-based API (cleaner than raw WebSocket)

**Alternative (Not Recommended)**: Rewrite frontend to use native WebSocket
- ❌ Loses automatic reconnection
- ❌ More boilerplate code
- ❌ No event namespacing

**Implementation**:

```bash
# Backend: Install python-socketio
pip install python-socketio
```

```python
# Integrate with FastAPI
from socketio import AsyncServer
sio = AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = socketio.ASGIApp(sio, app)

# Event handlers
@sio.event
async def zone_set_color(sid, data):
    zone_service.set_color(data['zone_id'], Color.from_dict(data['color']))
    await sio.emit('zone:state_changed', {...})
```

### 1.2 Communication Protocol Design

**Hybrid Strategy: REST + WebSocket**

**REST API (Request/Response)**:
- Initial data fetching (zone list, animation list, config)
- Idempotent operations (GET, PUT for initial loads)
- Error handling with HTTP status codes
- OpenAPI documentation

**WebSocket (Real-time Push + Commands)**:
- Zone state changes (hardware knobs → all clients)
- Animation start/stop notifications
- Frame updates (for LED visualization)
- Low-latency commands (color changes, brightness)

**When to Use Each**:

| Operation | Protocol | Reason |
|-----------|----------|--------|
| Initial zone list | REST GET | One-time fetch, cacheable |
| Zone color change from UI | WebSocket | Real-time, needs broadcast |
| Zone brightness slider | WebSocket (debounced) | High-frequency updates |
| Start animation | WebSocket | Real-time feedback |
| Get animation list | REST GET | Static data, cacheable |
| Hardware knob turn | WebSocket broadcast | Update all connected clients |

**Event Flow Example**:

```
Hardware Knob Turn:
  Raspberry Pi → EventBus (ZONE_COLOR_CHANGED)
    → Socket.io emit('zone:state_changed', {zone_id, color, brightness})
      → All connected web clients update UI in real-time

Web UI Color Picker:
  Frontend → Socket.io emit('zone:set_color', {zone_id, color})
    → Backend ZoneService.set_color()
      → Hardware LEDs update
      → Socket.io broadcast('zone:state_changed', {...})
        → All other clients see the change
```

### 1.3 API Contract Design

**RESTful Endpoints** (Complete the missing ones):

```
# Zone Control
GET    /api/v1/zones                        # List zones ✅ EXISTS
GET    /api/v1/zones/{zone_id}              # Get zone ✅ EXISTS
PUT    /api/v1/zones/{zone_id}/color        # Set color ✅ EXISTS
PUT    /api/v1/zones/{zone_id}/brightness   # Set brightness ✅ EXISTS
PUT    /api/v1/zones/{zone_id}/enabled      # Toggle on/off ❌ NEED TO IMPLEMENT
PUT    /api/v1/zones/{zone_id}/render-mode  # STATIC/ANIMATION ❌ NEED TO IMPLEMENT

# Animation Control (NEW - all missing)
POST   /api/v1/zones/{zone_id}/animation           # Start animation
DELETE /api/v1/zones/{zone_id}/animation           # Stop animation
PUT    /api/v1/zones/{zone_id}/animation/params    # Update params
GET    /api/v1/zones/{zone_id}/animation           # Get current animation

# System
GET    /api/v1/animations                   # List available animations ✅ EXISTS
GET    /api/v1/animations/{id}/parameters   # Get animation params ❌ NEW
```

**WebSocket Events**:

```
// Server → Client (Broadcast)
'zone:state_changed'           → {zone_id, color, brightness, is_on, render_mode}
'zone:animation_started'       → {zone_id, animation_id, parameters}
'zone:animation_stopped'       → {zone_id}
'zone:animation_param_changed' → {zone_id, param_id, value}
'frame:update'                 → {zone_id, pixels: number[]} // Optional: visualization
'system:fps_update'            → {fps, render_time_ms}

// Client → Server (Commands)
'zone:set_color'               → {zone_id, color: Color}
'zone:set_brightness'          → {zone_id, brightness: number}
'zone:set_enabled'             → {zone_id, enabled: boolean}
'animation:start'              → {zone_id, animation_id, parameters}
'animation:stop'               → {zone_id}
'animation:set_param'          → {zone_id, param_id, value}
```

**Data Contracts** (Pydantic Schemas):

```python
# Request Schemas
class ZoneColorUpdateRequest(BaseModel):
    mode: ColorModeEnum  # HUE | RGB | PRESET
    hue: Optional[int] = None  # 0-360
    rgb: Optional[List[int]] = None  # [r, g, b]
    preset: Optional[str] = None

class AnimationStartRequest(BaseModel):
    animation_id: str  # "BREATHE", "COLOR_FADE", etc.
    parameters: Dict[str, Any]  # {"ANIM_SPEED": 50, ...}

class AnimationParamUpdateRequest(BaseModel):
    param_id: str  # "ANIM_SPEED"
    value: Any    # 50

# Response Schemas (already exist, verify completeness)
class ZoneResponse(BaseModel):
    id: str
    name: str
    pixel_count: int
    state: ZoneStateResponse
    gpio: int
    layout: Optional[Dict]

class ZoneStateResponse(BaseModel):
    color: ColorResponse
    brightness: int  # 0-255
    is_on: bool
    render_mode: str  # "STATIC" | "ANIMATION"
    animation: Optional[AnimationStateResponse]

class AnimationStateResponse(BaseModel):
    id: str
    parameter_values: Dict[str, Any]
```

### 1.4 State Synchronization Strategy

**Problem**: Multiple sources of truth:
- Backend: state.json persisted state
- Frontend: Zustand stores (in-memory)
- Hardware: Physical knobs/encoders

**Solution**: Event-Driven Sync

```
Single Source of Truth: Backend State Service
                    ↓
        All changes go through EventBus
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
  State Persistence      Socket.io Broadcast
  (state.json)           (all web clients)
        ↓                       ↓
  Hardware Update         Frontend Update
```

**Optimistic Updates in Frontend**:

```javascript
// When user changes color picker:
1. Immediately update local Zustand store (optimistic)
2. Emit socket.io command to backend
3. Wait for 'zone:state_changed' confirmation
4. If confirmation matches → keep optimistic state
5. If different → rollback to server state (rare)
6. If timeout/error → show error, rollback state
```

**Debouncing Strategy**:

```
// For high-frequency inputs (sliders):
- Brightness slider: debounce 150ms before emitting
- Color picker: throttle to 10 updates/sec max
- Backend: last value wins, no queueing needed
```

---

## PHASE 2: UI/UX Design Strategy

### 2.1 Selected Zone Concept in Web UI

**Your Question**: "Do we need selected zone in webapp? Makes sense for hardware, but maybe pointless in webapp?"

**UX Analysis**:

**Arguments FOR Selected Zone**:
- ✅ Consistency: Matches physical hardware mental model
- ✅ Keyboard shortcuts: Arrow keys to switch zones, Space to toggle
- ✅ Batch operations: "Apply color to selected zone"
- ✅ Focus management: Accessibility (screen readers announce selected zone)
- ✅ Visual hierarchy: Clear which zone you're editing

**Arguments AGAINST**:
- ❌ Mouse/touch UX: Direct manipulation is more natural (click zone card to edit it)
- ❌ Spatial redundancy: In a list view, hover/focus already indicates "active" zone
- ❌ Extra clicks: Select zone → change color vs. just change color on card

**Recommendation**: Hybrid Approach ✅

**Desktop (Mouse)**:
- NO global selected zone concept
- Each ZoneCard is independently editable
- Hover state shows "I'm interactive"
- Click color picker → modal opens for THAT zone
- Click brightness slider → drag immediately affects THAT zone

**Mobile/Tablet (Touch)**:
- Optional "expanded" zone (one card expanded at a time)
- Tap zone card → expands to show full controls
- Other zones collapse to compact view

**Keyboard Navigation**:
- Tab cycles through zones
- Enter/Space on zone card expands it (equivalent to "selection")
- Arrow keys within expanded zone adjust brightness/color
- Escape collapses

**Visual Design**:

```
┌─────────────────────────┐
│ Floor Strip        [⚪] │  ← Toggle switch (is_on)
├─────────────────────────┤
│ ████████████████████    │  ← Color preview bar (current color)
│                         │
│ [STATIC ▾] [🎨 Color]  │  ← Mode selector + Color button
│                         │
│ Brightness         80%  │  ← Label + value
│ ────────●───────────    │  ← Slider (instant feedback)
│                         │
│ 🎬 Breathe    [▶ Start]│  ← Animation (if mode=STATIC, show "Start")
│                         │  ← (if mode=ANIMATION, show params)
└─────────────────────────┘

If ANIMATION mode active:
┌─────────────────────────┐
│ 🎬 Breathe         [⏸]  │  ← Stop button
│ Speed              ●    │  ← Animation params
│ Intensity          ●    │
└─────────────────────────┘
```

**Interaction Flow**:
- User clicks color preview bar → color picker modal opens
- User drags brightness slider → real-time WebSocket updates
- User toggles switch → zone turns on/off instantly
- User clicks mode dropdown → switches STATIC ↔ ANIMATION
- User clicks animation "Start" → animation begins on hardware + UI updates

### 2.2 Real-time Feedback Design

**Visual Indicators - Connection Status (Top Bar)**:

```
● Connected to Raspberry Pi  |  60 FPS  |  Updated 2s ago
⚠ Reconnecting...            |  -- FPS  |  Connection lost
✕ Disconnected               |  -- FPS  |  Offline mode
```

**Zone Card States**:

```css
/* Default state */
.zone-card {
  background: var(--bg-panel);
  border: 1px solid var(--border-default);
}

/* Hover (mouse over) */
.zone-card:hover {
  background: var(--bg-elevated);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

/* Updating (WebSocket command sent, waiting for confirmation) */
.zone-card.updating {
  border-color: var(--accent-primary);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.3); /* Glow effect */
}

/* Error state (command failed) */
.zone-card.error {
  border-color: var(--error);
  animation: shake 0.3s;
}

/* Disabled (is_on = false) */
.zone-card.disabled {
  opacity: 0.5;
  filter: grayscale(100%);
}
```

**Loading States**:

```jsx
// Skeleton loading (initial fetch)
<ZoneCardSkeleton /> // Shimmer effect

// Optimistic update (command in-flight)
<Spinner size="sm" className="absolute top-2 right-2" />

// Success confirmation (brief)
<CheckIcon className="absolute top-2 right-2 animate-fade-in" />
```

**Animation Preview**:

```
┌─────────────────────────┐
│ 🎬 Breathe         [⏸]  │
│ ▂▃▅▇▅▃▂▂▃▅▇▅▃▂▂▃▅ │  ← Live waveform (optional)
│ Speed         ●─────    │
│ Intensity     ───●──    │
└─────────────────────────┘
```

### 2.3 Color Picker UX Design

**Component**: HexColorPicker from react-colorful

**Design Decisions - Trigger**:
- Click color preview bar → modal/popover opens
- Preview bar shows current color with smooth gradient

**Picker Layout (Desktop - Popover)**:

```
┌──────────────────────────────┐
│ Pick Color for Floor Strip ✕│  ← Title + close
├──────────────────────────────┤
│ [HUE] [RGB] [PRESETS]       │  ← Tabs (mode selector)
├──────────────────────────────┤
│                              │
│   [Color Wheel - 280px]      │  ← HexColorPicker component
│                              │
│   🎨 Cyan                    │  ← Current color preview + name
├──────────────────────────────┤
│ HUE   #00E5FF    ✓          │  ← Hex input with copy button
├──────────────────────────────┤
│ Recent: [●][●][●][●][●][●]  │  ← Recent colors (localStorage)
├──────────────────────────────┤
│ Presets: [Cyan][Red][Amber]  │  ← Quick presets
├──────────────────────────────┤
│         [Cancel]   [Apply]   │  ← Actions
└──────────────────────────────┘
```

**Interaction Pattern**:
- Live Preview: As user drags picker, send throttled WebSocket updates (10/sec max)
- Apply on Enter: Press Enter to confirm and close
- Cancel on Escape: Revert to original color
- Click Outside: Apply current color and close (or revert? User preference)

**Mobile Adaptation - Bottom Sheet Modal** (full-width):

```
┌────────────────────────────────┐
│ Pick Color              [✕]   │
│ ─────────────────────────────  │  ← Drag handle
│ [HUE] [RGB] [PRESETS]         │
│                                │
│   [Color Wheel - Full Width]  │
│                                │
│   #00E5FF              ✓      │
│ Recent: [●][●][●][●][●][●]    │
│ Presets (horizontal scroll)    │
│ [Cyan] [Red] [Amber] [Purple]→│
│                                │
│ [Cancel]           [Apply]    │
└────────────────────────────────┘
```

### 2.4 Animation Control UI Design

**Component Hierarchy**:

```
ZoneCard
  ├─ ZoneHeader (name, toggle)
  ├─ ColorPreview (click → picker)
  ├─ BrightnessSlider
  ├─ RenderModeSelector (STATIC | ANIMATION)
  └─ AnimationControls (conditional)
      ├─ AnimationSelector (if STATIC mode)
      │   └─ [🎬 Select Animation ▾] [▶ Start]
      └─ AnimationParameters (if ANIMATION mode)
          ├─ [🎬 Breathe ✓ Running] [⏸ Stop]
          ├─ SpeedSlider (ANIM_SPEED param)
          ├─ IntensitySlider (ANIM_INTENSITY param)
          └─ ColorPickers (for ANIM_PRIMARY_COLOR_HUE, etc.)
```

**Animation Selector Design**:

```
┌────────────────────────────┐
│ [Select Animation ▾]       │  ← Dropdown trigger
└────────────────────────────┘

Opens to:
┌────────────────────────────┐
│ 🌬️  Breathe                │  ← Icons + names
│ 🌈 Color Fade              │
│ 🐍 Snake                   │
│ 🎨 Color Snake             │
│ 🔄 Color Cycle             │
│ 💻 Matrix                  │
└────────────────────────────┘
```

**Animation Parameter Controls**: Dynamic Rendering Based on Parameter Type

```javascript
// Backend provides:
AnimationParameter {
  id: "ANIM_SPEED",
  type: "number",
  min: 0,
  max: 100,
  default: 50,
  display_name: "Speed"
}

// Frontend renders:
<Slider
  label="Speed"
  min={0}
  max={100}
  value={50}
  onChange={(val) => updateAnimationParam('ANIM_SPEED', val)}
/>
```

**Parameter Types**:
- `number` → Slider with value display
- `color_hue` → Hue picker (0-360)
- `color_rgb` → Full RGB picker
- `boolean` → Switch toggle
- `select` → Dropdown with options

### 2.5 LED Visualization Design (Future Enhancement)

**Live LED Strip Rendering**:

```
┌──────────────────────────────────────┐
│ Floor Strip (144 LEDs)               │
├──────────────────────────────────────┤
│ ████████████████████████████████████ │  ← Live pixel rendering
│ ▓▓▓▒▒▒░░░   ░░░▒▒▒▓▓▓█████████████  │  ← Shows actual animation
│ ████████████████████████████████████ │  ← 60 FPS canvas
└──────────────────────────────────────┘
```

**Implementation**:
- HTML5 Canvas with requestAnimationFrame
- WebSocket frame:update events (optional, high bandwidth)
- Pixel-level rendering: each LED as rounded rectangle with glow
- Smooth interpolation between frames
- Responsive: scales to container width

**Performance**:
- Only render if visible (Intersection Observer)
- Throttle to 30 FPS for visualization (60 FPS on hardware)
- Option to disable for low-bandwidth connections

---

## PHASE 3: Implementation Roadmap

### Sprint 1: Backend API Completion (3-5 days)

**Tasks**:

**✅ Upgrade WebSocket to socket.io**
- Install python-socketio
- Replace /ws/logs and /ws/tasks with socket.io
- Add bidirectional event handlers

**✅ Implement missing zone endpoints**
- PUT /api/v1/zones/{zone_id}/enabled
- PUT /api/v1/zones/{zone_id}/render-mode

**✅ Add animation control endpoints**
- POST /api/v1/zones/{zone_id}/animation (start)
- DELETE /api/v1/zones/{zone_id}/animation (stop)
- PUT /api/v1/zones/{zone_id}/animation/params
- GET /api/v1/animations/{id}/parameters

**✅ WebSocket events for zones**
- zone:state_changed (broadcast on any change)
- animation:started, animation:stopped
- animation:param_changed

**✅ EventBus integration**
- Subscribe to ZONE_STATE_CHANGED events
- Broadcast to all connected socket.io clients
- Handle commands from web clients

**Acceptance Criteria**:
- All REST endpoints return proper responses
- WebSocket events broadcast to all clients
- Hardware knob turns → web UI updates instantly
- Web UI commands → hardware LEDs update instantly

### Sprint 2: Frontend State Sync (2-3 days)

**Tasks**:

**✅ Update WebSocket service**
- Verify socket.io-client compatibility
- Add event listeners for zone state changes
- Implement command emitters

**✅ Remove REST polling**
- Replace refetchInterval: 5000 with WebSocket push
- Keep REST API for initial data fetch only

**✅ Implement optimistic updates**
- Update Zustand store immediately on user action
- Wait for WebSocket confirmation
- Rollback on error/timeout

**✅ Connection status indicator**
- Top bar component showing connection state
- FPS display (from WebSocket events)
- Reconnection handling

**Acceptance Criteria**:
- No more 5-second polling delays
- UI updates instantly when hardware changes
- Optimistic updates feel snappy (<50ms)
- Connection loss handled gracefully

### Sprint 3: Animation UI Components (3-4 days)

**Tasks**:

**✅ Build AnimationSelector component**
- Dropdown with animation list
- Fetches from GET /api/v1/animations
- Start button triggers WebSocket command

**✅ Build AnimationParameterControls component**
- Dynamic rendering based on parameter metadata
- Sliders, color pickers, switches
- Real-time updates via WebSocket

**✅ Update ZoneCard component**
- Add render mode selector (STATIC/ANIMATION toggle)
- Conditionally show animation controls
- Show "is_on" toggle switch

**✅ Animation state management**
- Add animation state to Zustand store
- Handle animation start/stop events
- Parameter value persistence

**Acceptance Criteria**:
- Can start any animation from UI
- Animation parameters adjustable in real-time
- Animation state persists across page refresh
- Can run different animations on different zones simultaneously

### Sprint 4: UI/UX Polish (2-3 days)

**Tasks**:

**✅ Improve color picker**
- Add presets tab
- Recent colors (localStorage)
- Live preview with throttling

**✅ Loading states**
- Skeleton loaders for initial fetch
- Spinner for in-flight commands
- Success/error animations

**✅ Error handling**
- Toast notifications for errors
- Retry logic for failed commands
- Graceful degradation on disconnect

**✅ Accessibility**
- ARIA labels for all controls
- Keyboard navigation
- Focus indicators
- Screen reader announcements

**✅ Responsive design**
- Mobile-optimized zone cards
- Bottom sheet modals
- Touch-friendly controls (48px min)

**Acceptance Criteria**:
- WCAG AA compliance
- Works on mobile (375px width)
- All interactions have visual feedback
- No console errors

### Sprint 5: LED Visualization (Optional, 3-5 days)

**Tasks**:

**✅ Canvas-based LED strip renderer**
- Pixel-accurate visualization
- Glow effects and color blending

**✅ WebSocket frame streaming**
- Backend emits frame:update events
- Throttled to 30 FPS for bandwidth
- Optional (user can disable)

**✅ Animation preview**
- Show animations in browser before applying
- Thumbnail previews in animation selector

**Acceptance Criteria**:
- LED strip looks realistic in browser
- Animations visible in real-time
- Performant (no lag or jank)
- Can disable for low-bandwidth

---

## PHASE 4: Technical Specifications

### 4.1 Code Style & Contracts

**Backend (Python)**:
- ✅ Type hints everywhere (`async def set_color(zone_id: ZoneID, color: Color) -> None`)
- ✅ Pydantic models for all API requests/responses
- ✅ Docstrings for public methods
- ✅ Async/await patterns (no blocking calls)
- ✅ Dependency injection (constructor-based)
- ✅ EventBus for cross-component communication

**Frontend (TypeScript)**:
- ✅ Strict TypeScript mode
- ✅ Interfaces for all data structures
- ✅ Functional components (no class components)
- ✅ Custom hooks for reusable logic
- ✅ Zustand for state management
- ✅ React Query for server state (initial fetches)
- ✅ socket.io-client for real-time

**Shared Contracts**:
- ✅ Generate TypeScript types from Pydantic models (use pydantic-to-typescript or manual)
- ✅ Version API (/api/v1/...) for future compatibility
- ✅ Consistent enum values (backend Python enums match frontend TypeScript enums)

### 4.2 Error Handling Strategy

**Backend**:

```python
# HTTP errors
raise HTTPException(status_code=404, detail="Zone not found")

# WebSocket errors
@sio.event
async def zone_set_color(sid, data):
    try:
        zone_service.set_color(...)
        await sio.emit('zone:state_changed', {...})
    except ZoneNotFoundError as e:
        await sio.emit('error', {'message': str(e)}, room=sid)
```

**Frontend**:

```javascript
// Optimistic update with rollback
const previousState = zoneStore.getState().zones[zoneId];
zoneStore.updateZone(zoneId, newState); // Optimistic

socket.emit('zone:set_color', {zone_id, color}, (response) => {
  if (response.error) {
    zoneStore.updateZone(zoneId, previousState); // Rollback
    toast.error(response.error.message);
  }
});

// Timeout fallback
setTimeout(() => {
  if (!receivedConfirmation) {
    toast.warning('Update may have failed, reverting...');
    zoneStore.updateZone(zoneId, previousState);
  }
}, 3000);
```

### 4.3 Performance Optimization

**Backend**:
- ✅ Debounce state persistence (500ms)
- ✅ WebSocket broadcasts use rooms (only send to subscribed clients)
- ✅ Frame updates optional (high bandwidth, disabled by default)
- ✅ DMA optimization (already implemented)

**Frontend**:
- ✅ Throttle color picker updates (10/sec)
- ✅ Debounce brightness slider (150ms)
- ✅ Virtual scrolling for large zone lists (if >20 zones)
- ✅ Lazy load animation thumbnails
- ✅ Memoize expensive computations (useMemo, React.memo)

---

## PHASE 5: Open Questions & Decisions Needed

### Q1: WebSocket Frame Streaming for Visualization?

**Trade-offs**:
- ✅ Pros: Pixel-perfect LED preview in browser, shows exact hardware state
- ❌ Cons: High bandwidth (144 LEDs × 3 bytes × 60 FPS = ~25 KB/s per zone)

**Recommendation**:
- Make it optional (user setting)
- Default: OFF (only show solid colors, not live pixels)
- Enable on demand for debugging/demos
- Throttle to 30 FPS if enabled

Your preference?

### Q2: Color Picker Behavior on "Click Outside"?

**Options**:
- Apply and close (macOS style)
- Revert and close (requires explicit "Apply" button)
- Ask user (setting in preferences)

**Recommendation**: Apply and close (less friction)

Your preference?

### Q3: Animation Preview Thumbnails?

**Options**:
- Static images (pre-rendered GIFs in public/animations/)
- Live canvas preview (mini version of LED visualization)
- Text descriptions only

**Recommendation**: Static GIFs (fastest to implement, good UX)

Your preference?

### Q4: Multi-zone Selection for Batch Operations?

**Use case**: "Apply this color to Floor + Lamp + Desk at once"

**Options**:
- Not needed (users can click each zone individually)
- Add multi-select (checkboxes on zone cards)
- Add "Apply to all" button (on color picker)

**Recommendation**: Phase 2 feature (nice-to-have, not MVP)

Your preference?

### Q5: Dark Mode vs. Light Mode?

**Current**: Frontend has dark theme hardcoded

**Options**:
- Dark only (LED tools are typically used in dark environments)
- Add light mode toggle
- System preference (auto-detect OS setting)

**Recommendation**: Dark only for MVP (matches LED aesthetic), add light mode later if requested

Your preference?

---

## Summary & Next Steps

**What We'll Build**:

**✅ Backend**:
- Socket.io bidirectional WebSocket
- Animation control REST endpoints
- Real-time zone state broadcasting
- EventBus → WebSocket bridge

**✅ Frontend**:
- Remove REST polling, use WebSocket push
- Animation selector and parameter controls
- Optimistic UI updates with rollback
- Real-time hardware sync

**✅ UX**:
- No global "selected zone" (direct manipulation)
- Live color picker with throttling
- Visual feedback for all actions
- Mobile-responsive design

---

## FINAL ARCHITECTURE & FRONTEND-BACKEND INTEGRATION PLAN

### DECISIONS LOCKED IN ✅

**Communication & Architecture**:
- **WebSocket Protocol**: Upgrade backend to socket.io for bidirectional communication
- **Hybrid Approach**: REST for initial data + WebSocket for real-time push updates
- **Event-Driven Sync**: Backend EventBus → socket.io broadcast → all web clients
- **State Persistence**: Backend state.json is single source of truth

**UI/UX Design**:
- **Selected Zone**: No global selection in webapp (direct manipulation via click)
- **Selected Zone Visualization**: ✅ Make it configurable - checkbox in settings to show/hide pulse effect (matches hardware when enabled, cleans up UI when disabled)
- **Color Picker Behavior**: Click outside = Apply and close (less friction)
- **Animation Previews**: Static GIFs in public/animations/
- **LED Visualization**: Frame streaming = future feature (optional, disabled by default)
- **Theming**: Dark mode only + Customizable accent color system (primary color for borders, glows, accents, fonts - branded theme support)
- **Zone Grouping**: Future feature - zones will be configurable (1-pixel micro-zones + grouping for batch operations in later sprints)

---

## 📊 COMPLETE FEATURE ROADMAP

### 🚀 MVP (Sprints 1-4, weeks 1-3)

#### Sprint 1: Backend API Completion (3-5 days)

**REST Endpoints**:

```bash
# Complete these 5 endpoints
PUT  /api/v1/zones/{zone_id}/enabled       # Toggle on/off
PUT  /api/v1/zones/{zone_id}/render-mode   # STATIC ↔ ANIMATION

# New animation endpoints
POST   /api/v1/zones/{zone_id}/animation           # Start animation
DELETE /api/v1/zones/{zone_id}/animation           # Stop animation
PUT    /api/v1/zones/{zone_id}/animation/params    # Update params
GET    /api/v1/animations/{id}/parameters          # Get param metadata
```

**WebSocket Migration**:
- Install python-socketio
- Replace /ws/logs and /ws/tasks with socket.io
- Create /ws/zones namespace for zone events

**Socket.io Events** (One-way: Server → Clients):

```
'zone:state_changed'        → {zone_id, color, brightness, is_on, render_mode}
'zone:animation_started'    → {zone_id, animation_id, parameters}
'zone:animation_stopped'    → {zone_id}
'animation:param_changed'   → {zone_id, param_id, value}
'system:fps_update'         → {fps, render_time_ms}
```

**Socket.io Commands** (Bidirectional: Clients → Server):

```
'zone:set_color'      → {zone_id, color: Color}
'zone:set_brightness' → {zone_id, brightness: number}
'zone:set_enabled'    → {zone_id, enabled: boolean}
'zone:set_render_mode' → {zone_id, render_mode: string}
'animation:start'     → {zone_id, animation_id, parameters}
'animation:stop'      → {zone_id}
'animation:set_param' → {zone_id, param_id, value}
```

**EventBus Integration**:
- Subscribe to ZONE_STATE_CHANGED, ANIMATION_STARTED, etc.
- Emit socket.io events to all connected clients
- Broadcast happens in real-time (hardware knob → web UI)

#### Sprint 2: Frontend State Sync (2-3 days)

**Changes**:
- Verify socket.io-client connection works with new backend
- Remove REST polling (refetchInterval: 5000 → WebSocket push)
- Implement optimistic UI updates with rollback
- Add connection status indicator (top bar: Connected/Reconnecting/Offline)
- Show FPS counter from WebSocket events

**Zustand Store Updates**:

```typescript
interface ZoneStore {
  zones: Zone[]
  updateZone(id, updates)      // Called by:
                                // - REST fetch (initial)
                                // - WebSocket event (real-time)
  setConnectionStatus(status)   // Connected|Reconnecting|Offline
  setFps(fps)
}
```

**Real-time Sync Pattern**:

```javascript
// 1. Initial fetch (REST)
GET /api/v1/zones → Zustand store

// 2. User action (WebSocket + Optimistic)
User clicks color picker → Update store immediately (optimistic)
                        → Emit socket.io 'zone:set_color'
                        → Wait for 'zone:state_changed' confirmation
                        → If matches → keep optimistic state ✓
                        → If different → rollback + show error ✗

// 3. Hardware change (WebSocket broadcast)
Knob turn on Pi → EventBus event
              → Backend broadcasts 'zone:state_changed'
              → All web clients receive + update Zustand
              → React re-renders UI
```

#### Sprint 3: Animation UI Components (3-4 days)

**Components to Build**:

```
AnimationSelector (dropdown)
[🎬 Select Animation ▾]  [▶ Start]
└─ Breathe
└─ Color Fade
└─ Snake

AnimationParameterControls (dynamic)
[🎬 Breathe ▾]  [⏸ Stop]
Speed         ●─────────── (0-100)
Intensity     ───●──────── (0-100)

Updated ZoneCard (conditional rendering)
┌─────────────────────────┐
│ Floor Strip         [⚪] │  ← Toggle (is_on)
├─────────────────────────┤
│ ████████████████████    │  ← Color bar
│ Brightness         80%  │
│ ────────●───────────    │  ← Slider
│ [STATIC ▾]              │  ← Mode selector
│ [🎬 Select Anim] [▶]   │  ← If STATIC mode
└─────────────────────────┘

OR (if ANIMATION mode):
┌─────────────────────────┐
│ [🎬 Breathe ▾]  [⏸]    │  ← Current animation + stop
│ Speed      ●────────    │  ← Params (dynamic)
│ Intensity  ───●─────    │
└─────────────────────────┘
```

**Animation State Management**:
- Add to Zustand: `activeAnimations: Map<ZoneID, AnimationState>`
- Handle start/stop WebSocket events
- Store running animation + parameters

#### Sprint 4: UI/UX Polish & Settings (2-3 days)

**Features**:

**Color Picker Enhancement**:
- Presets tab (common LED colors)
- Recent colors (localStorage)
- Hex input field with copy button
- Live preview with throttling (10 updates/sec)

**Settings Panel** (new page):

```
Appearance
└─ Accent Color:  [Color Picker]  ← Leading color system
└─ Show Selected Zone Pulse: [Toggle]  ← Sync with hardware

Connection
└─ Server URL: [Input]
└─ Auto-Reconnect: [Toggle]

Debug
└─ Show FPS: [Toggle]
└─ Enable Frame Visualization: [Toggle]  ← Future
```

**Leading Color System** (CSS variables):

```css
:root {
  --accent-primary: #00e5ff;  /* User selected */
  --accent-secondary: hsla(188, 100%, 50%, 0.3);

  /* Auto-generated variants */
  --border-accent: 1px solid var(--accent-primary);
  --glow-accent: 0 0 12px var(--accent-primary);
  --text-accent: var(--accent-primary);
}

/* Applied everywhere */
.zone-card:hover { border: var(--border-accent); }
.button-primary { color: var(--text-accent); }
.selected-zone { box-shadow: var(--glow-accent); }
```

**Selected Zone Visualization** (configurable):

```javascript
// Settings → Show Selected Zone Pulse [Toggle]

if (settings.showSelectedZonePulse && isSelectedZone) {
  return <div className="zone-card animate-pulse-glow" />
}
```

**Error Handling & Feedback**:
- Toast notifications (success/error/warning)
- Retry buttons for failed commands
- Graceful offline mode (show cached data)
- Connection status indicator

**Accessibility**:
- ARIA labels, roles, live regions
- Keyboard navigation (Tab, Enter, Space, Arrow keys)
- Focus indicators (4px outline)
- Screen reader announcements

### 🔮 FUTURE (Sprint 5+, later weeks)

#### Sprint 5: Advanced Zone Management
- Multi-zone grouping UI
- Batch operations (select multiple zones → apply color/animation)
- Zone configuration (rename, reorder, create 1-pixel micro-zones)
- Zone profiles/presets

#### Sprint 6: LED Visualization (Optional)
- Canvas-based LED strip renderer
- WebSocket frame:update events (throttled to 30 FPS)
- Pixel-accurate animation preview
- Performance: render only if visible (Intersection Observer)

#### Sprint 7: Enhanced UX
- Animation library with thumbnails
- Parameter presets per animation
- Undo/redo stack
- Export/import zone configurations

#### Sprint 8: Advanced Features
- Schedule animations (time-based triggers)
- Sensor integration (temperature, brightness, sound)
- Mobile app (React Native or Capacitor)
- Webhook integrations

---

## 📋 TECHNICAL SPECIFICATIONS

### Backend Changes Required

**1. Install Dependencies**:

```bash
pip install python-socketio
pip install python-socketio[asyncio_client]
```

**2. FastAPI App Factory** (`src/api/main.py`):
- Integrate socket.io with FastAPI
- Setup CORS and allowed origins
- Setup lifespan hooks (connect/disconnect)

**3. WebSocket Handlers** (new file: `src/api/websocket_handler.py`):

```python
class ZoneWebSocketHandler:
    def __init__(self, sio: AsyncServer, services):
        self.sio = sio
        self.zone_service = services.zone_service
        self.animation_engine = services.animation_engine
        self.event_bus = services.event_bus

    async def setup_events(self):
        """Register socket.io event handlers"""
        @self.sio.event
        async def zone_set_color(sid, data):
            # Validate, call zone_service.set_color()
            # Broadcast 'zone:state_changed' to all clients

        @self.sio.event
        async def animation_start(sid, data):
            # Validate, call animation_engine.start_for_zone()
            # Broadcast 'zone:animation_started' to all clients

    async def broadcast_zone_changed(self, zone_id: ZoneID):
        """Called by EventBus on ZONE_STATE_CHANGED"""
        zone = self.zone_service.get_zone(zone_id)
        await self.sio.emit('zone:state_changed', {
            'zone_id': zone_id.name,
            'color': zone.state.color.to_dict(),
            'brightness': zone.state.brightness,
            'is_on': zone.state.is_on,
            'render_mode': zone.state.mode.value
        })
```

**4. Animation Engine Note**:
- Current `src/animations/engine.py` (line 1-281) needs updates in future sprints
- For MVP: Keep as-is, just expose via REST/WebSocket endpoints
- Future: May need parameter update mechanism enhancement

**5. API Route Completions** (`src/api/routes/zones.py`):

```python
# Line ~200: Implement zone enabled endpoint
@router.put("/{zone_id}/enabled")
async def set_zone_enabled(zone_id: str, enabled: bool) -> ZoneResponse:
    zone_id_enum = ZoneID[zone_id.upper()]
    zone_service.set_is_on(zone_id_enum, enabled)
    # Trigger EventBus event → WebSocket broadcast
    return ZoneResponse.from_zone(zone_service.get_zone(zone_id_enum))

# Line ~220: Implement render mode endpoint
@router.put("/{zone_id}/render-mode")
async def set_render_mode(zone_id: str, mode: str) -> ZoneResponse:
    zone_id_enum = ZoneID[zone_id.upper()]
    render_mode = ZoneRenderMode[mode.upper()]
    lighting_controller.set_zone_render_mode(zone_id_enum, render_mode)
    return ZoneResponse.from_zone(zone_service.get_zone(zone_id_enum))

# NEW: Animation endpoints
@router.post("/{zone_id}/animation")
async def start_animation(zone_id: str, request: AnimationStartRequest) -> ZoneResponse:
    zone_id_enum = ZoneID[zone_id.upper()]
    await animation_engine.start_for_zone(zone_id_enum, request.animation_id, request.parameters)
    return ZoneResponse.from_zone(zone_service.get_zone(zone_id_enum))
```

### Frontend Changes Required

**1. WebSocket Service Update** (`frontend/src/services/websocket.ts`):

```typescript
// Already uses socket.io-client ✓
// Just verify event handlers match backend

socket.on('zone:state_changed', (data) => {
  zoneStore.updateZone(data.zone_id, {
    color: data.color,
    brightness: data.brightness,
    is_on: data.is_on,
    render_mode: data.render_mode
  })
})

socket.on('zone:animation_started', (data) => {
  zoneStore.updateZone(data.zone_id, {
    animation: { id: data.animation_id, parameters: data.parameters },
    render_mode: 'ANIMATION'
  })
})
```

**2. Zustand Store Updates** (`frontend/src/stores/`):

```typescript
// zoneStore.ts: Add connection status, FPS, remove polling interval
interface ZoneStore {
  zones: Zone[]
  connectionStatus: 'connected' | 'reconnecting' | 'disconnected'
  fps: number
  lastUpdate: Date

  updateZone(id, updates)
  setConnectionStatus(status)
  setFps(fps)
}

// Remove: refetchInterval: 5000 from useZones hook
// Replace with: WebSocket listener instead
```

**3. Component Updates** (`frontend/src/components/zones/ZoneCard.tsx`):

```jsx
// Add mode selector
<select value={zone.render_mode} onChange={(e) => {
  emit('zone:set_render_mode', { zone_id, render_mode: e.target.value })
}}>
  <option>STATIC</option>
  <option>ANIMATION</option>
</select>

// Add conditional animation controls
{zone.render_mode === 'ANIMATION' ? (
  <AnimationControls zone={zone} />
) : (
  <AnimationSelector zone={zone} />
)}
```

**4. New Components** (`frontend/src/components/animations/`):
- `AnimationSelector.tsx` ← Dropdown + start button
- `AnimationParameter*.tsx` ← Slider, ColorPicker, Switch (dynamic)
- `AnimationControls.tsx` ← Container for params + stop button

**5. Settings Page** (`frontend/src/pages/Settings.tsx`):

```jsx
// Appearance section
<ThemeSettings>
  <AccentColorPicker />
  <Toggle label="Show Selected Zone Pulse" />
</ThemeSettings>

// Connection section
<ConnectionSettings />

// Debug section
<DebugSettings />
```

**6. Accent Color System** (`frontend/src/styles/theme.ts`):

```typescript
const createThemeWithAccent = (accentColor: string) => ({
  '--accent-primary': accentColor,
  '--accent-secondary': `hsla(${getHue(accentColor)}, 100%, 50%, 0.3)`,
  '--border-accent': `1px solid ${accentColor}`,
  '--glow-accent': `0 0 12px ${accentColor}`,
  '--text-accent': accentColor,
})

// Apply to CSS variables on mount
useEffect(() => {
  const accent = settingsStore.accentColor
  Object.entries(createThemeWithAccent(accent)).forEach(([key, val]) => {
    document.documentElement.style.setProperty(key, val)
  })
}, [settingsStore.accentColor])
```

---

## 🎨 UI MOCKUP - FINAL STATE

### Desktop Dashboard (Sprint 4 Complete)

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔌 Connected | 60 FPS | Last update: 2s ago       ⚙️ Settings ▼│
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Zone List                                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Floor Strip                                              [⚪]││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ ████████████████████████████████  ← Color bar (hue)       ││
│  │ Brightness: 80%     ────────●──────                       ││
│  │ [STATIC ▾] [Select Animation ▾] [▶ Start]                ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Lamp Strip                                              [⚪]││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ ████████████████████████████████                         ││
│  │ Brightness: 100%    ────────●──────                      ││
│  │ [ANIMATION ▾]   [🎬 Color Fade ▾] [⏸ Stop]             ││
│  │ Speed:         ──●────────                               ││
│  │ Intensity:     ─────●────                                ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ... more zones ...                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Settings Panel (new)

```
┌──────────────────┐
│ Appearance       │
│ Accent: [🎨]     │
│ [☑] Selected Zone Pulse
│                  │
│ Connection       │
│ Server: [input]  │
│ [☑] Auto-Reconnect
│                  │
│ Debug            │
│ [☑] Show FPS     │
└──────────────────┘
```

### Color Picker (Sprint 4)

```
┌────────────────────────────────┐
│ Pick Color             [✕]    │
├────────────────────────────────┤
│ [HUE] [RGB] [PRESETS]         │
├────────────────────────────────┤
│      [Color Wheel - 260px]    │
│                                │
│   🎨 Cyan       #00E5FF  ✓   │
├────────────────────────────────┤
│ Recent: [●][●][●][●][●][●]  │
│ Presets: [Cyan][Red][Amber] │
├────────────────────────────────┤
│     [Cancel]    [Apply]       │
└────────────────────────────────┘
```

---

## 🚀 TIMELINE ESTIMATE

- **Sprint 1** (Backend APIs): 3-5 days
- **Sprint 2** (Frontend Sync): 2-3 days
- **Sprint 3** (Animation UI): 3-4 days
- **Sprint 4** (Polish + Settings): 2-3 days

**Total MVP**: 10-15 days (2-3 weeks)

---

## ✅ ACCEPTANCE CRITERIA (MVP Complete)

### Backend

- ✅ All REST endpoints return proper responses
- ✅ WebSocket events broadcast to all clients in real-time
- ✅ Hardware knob → web UI updates instantly (< 100ms)
- ✅ Web UI command → hardware LEDs update instantly (< 100ms)

### Frontend

- ✅ Can turn any zone on/off
- ✅ Can change any zone's color in real-time
- ✅ Can adjust brightness with instant feedback
- ✅ Can switch render mode (STATIC ↔ ANIMATION)
- ✅ Can start/stop any of 3+ animations
- ✅ Can adjust animation parameters in real-time
- ✅ Can run different animations on different zones simultaneously
- ✅ All changes synced to other connected clients in real-time
- ✅ No REST polling (5s delays gone)
- ✅ Connection status visible (Connected/Offline)

### UX

- ✅ Color picker with presets and recent colors
- ✅ Settings page with accent color customization
- ✅ Optional selected zone pulse (configurable)
- ✅ Smooth animations and transitions
- ✅ Error handling with retry
- ✅ Offline graceful degradation (cached data)
- ✅ Mobile responsive (375px+)
- ✅ WCAG AA accessibility

---

## 📝 NOTES FOR FUTURE SPRINTS

- **AnimationEngine** (`src/animations/engine.py`): Currently OK for MVP, note for future parameter enhancement
- **Zone Grouping**: Design complete, implementation in Sprint 5+
- **LED Visualization**: Design complete, optional feature for Sprint 6+
- **Advanced Features**: Scheduling, sensors, webhooks for Sprint 7+

---

## ✨ READY TO BUILD

This plan is comprehensive, detailed, and actionable. Each sprint has clear deliverables and acceptance criteria. The architecture is sound with proper separation between REST (initial/config) and WebSocket (real-time/push).

**Perfect! ✅** Plan approved and task list created with comprehensive implementation roadmap across 4 sprints.
Animation start/stop notifications
Frame updates (for LED visualization)
Low-latency commands (color changes, brightness)
When to Use Each:
Operation	Protocol	Reason
Initial zone list	REST GET	One-time fetch, cacheable
Zone color change from UI	WebSocket	Real-time, needs broadcast to other clients
Zone brightness slider	WebSocket (debounced)	High-frequency updates
Start animation	WebSocket	Real-time feedback
Get animation list	REST GET	Static data, cacheable
Hardware knob turn	WebSocket broadcast	Must update all connected clients
Event Flow Example:
Hardware Knob Turn:
  Raspberry Pi → EventBus (ZONE_COLOR_CHANGED)
    → Socket.io emit('zone:state_changed', {zone_id, color, brightness})
      → All connected web clients update UI in real-time

Web UI Color Picker:
  Frontend → Socket.io emit('zone:set_color', {zone_id, color})
    → Backend ZoneService.set_color()
      → Hardware LEDs update
      → Socket.io broadcast('zone:state_changed', {...})
        → All other clients see the change
1.3 API Contract Design
RESTful Endpoints (Complete the missing ones):
# Zone Control
GET    /api/v1/zones                        # List zones ✅ EXISTS
GET    /api/v1/zones/{zone_id}              # Get zone ✅ EXISTS
PUT    /api/v1/zones/{zone_id}/color        # Set color ✅ EXISTS
PUT    /api/v1/zones/{zone_id}/brightness   # Set brightness ✅ EXISTS
PUT    /api/v1/zones/{zone_id}/enabled      # Toggle on/off ❌ NEED TO IMPLEMENT
PUT    /api/v1/zones/{zone_id}/render-mode  # STATIC/ANIMATION ❌ NEED TO IMPLEMENT

# Animation Control (NEW - all missing)
POST   /api/v1/zones/{zone_id}/animation    # Start animation
DELETE /api/v1/zones/{zone_id}/animation    # Stop animation
PUT    /api/v1/zones/{zone_id}/animation/params  # Update params
GET    /api/v1/zones/{zone_id}/animation    # Get current animation

# System
GET    /api/v1/animations                   # List available animations ✅ EXISTS
GET    /api/v1/animations/{id}/parameters   # Get animation params ❌ NEW
WebSocket Events:
// Server → Client (Broadcast)
'zone:state_changed'       → {zone_id, color, brightness, is_on, render_mode}
'zone:animation_started'   → {zone_id, animation_id, parameters}
'zone:animation_stopped'   → {zone_id}
'zone:animation_param_changed' → {zone_id, param_id, value}
'frame:update'             → {zone_id, pixels: number[]} // Optional: for visualization
'system:fps_update'        → {fps, render_time_ms}

// Client → Server (Commands)
'zone:set_color'           → {zone_id, color: Color}
'zone:set_brightness'      → {zone_id, brightness: number}
'zone:set_enabled'         → {zone_id, enabled: boolean}
'animation:start'          → {zone_id, animation_id, parameters}
'animation:stop'           → {zone_id}
'animation:set_param'      → {zone_id, param_id, value}
Data Contracts (Pydantic Schemas):
# Request Schemas
class ZoneColorUpdateRequest(BaseModel):
    mode: ColorModeEnum  # HUE | RGB | PRESET
    hue: Optional[int] = None  # 0-360
    rgb: Optional[List[int]] = None  # [r, g, b]
    preset: Optional[str] = None

class AnimationStartRequest(BaseModel):
    animation_id: str  # "BREATHE", "COLOR_FADE", etc.
    parameters: Dict[str, Any]  # {"ANIM_SPEED": 50, ...}

class AnimationParamUpdateRequest(BaseModel):
    param_id: str  # "ANIM_SPEED"
    value: Any    # 50

# Response Schemas (already exist, verify completeness)
class ZoneResponse(BaseModel):
    id: str
    name: str
    pixel_count: int
    state: ZoneStateResponse
    gpio: int
    layout: Optional[Dict]

class ZoneStateResponse(BaseModel):
    color: ColorResponse
    brightness: int  # 0-255
    is_on: bool
    render_mode: str  # "STATIC" | "ANIMATION"
    animation: Optional[AnimationStateResponse]

class AnimationStateResponse(BaseModel):
    id: str
    parameter_values: Dict[str, Any]

    