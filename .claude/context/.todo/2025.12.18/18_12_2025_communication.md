# Circular Update Prevention Architecture
**Date:** 2025-12-18
**Status:** Architecture Design
**Purpose:** Prevent circular updates in bidirectional WebSocket communication

---

## Table of Contents
1. [The Problem](#the-problem)
2. [Solution Comparison](#solution-comparison)
3. [Recommended Architecture](#recommended-architecture)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Layer Separation](#layer-separation)
6. [Implementation Plan](#implementation-plan)
7. [Alternative Solutions](#alternative-solutions)

---

## The Problem

### Circular Update Scenario
```
┌─────────────────────────────────────────────────────────────┐
│ WITHOUT CIRCULAR PREVENTION:                                │
│                                                              │
│ 1. Client A: set zone color to red                         │
│    → WebSocket emit: zone:set_color(red)                   │
│                                                              │
│ 2. Backend: receives command                                │
│    → ZoneService.set_color(red)                             │
│    → Publishes ZoneStateChangedEvent                        │
│                                                              │
│ 3. StaticModeController: listens to event                  │
│    → Submits frame to FrameManager                          │
│    → Hardware LEDs update ✓                                 │
│                                                              │
│ 4. WebSocket layer: broadcasts to ALL clients              │
│    → Sends zone:state_changed(red) to Client A too!        │
│                                                              │
│ 5. Client A: receives own change echoed back               │
│    → Updates local state (again)                            │
│    → Conflict with optimistic update!                       │
│    → Might trigger another update if not careful ⚠️         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Why This Matters
- **Performance**: Redundant rendering cycles
- **State consistency**: Conflicts between optimistic updates and server state
- **User experience**: Janky UI, flickering, race conditions
- **Scalability**: Problem multiplies with more clients

---

## Solution Comparison

| Solution | Complexity | Scalability | Diuna Fit | Industry Use |
|----------|------------|-------------|-----------|--------------|
| **A: Command Pattern** | Medium | High | ✅ Perfect | Netflix, Stripe |
| **B: Event Sourcing** | High | Very High | ⚠️ Overkill | Financial systems |
| **C: CQRS** | High | Very High | ⚠️ Too complex | Large enterprise |
| **D: Simple Client Filtering** | Low | Low | ❌ Brittle | Small demos |
| **E: Server-Side State Only** | Low | Medium | ❌ No optimistic updates | Traditional web |

### Detailed Comparison

#### Solution A: Command Pattern ⭐ RECOMMENDED
**What it is**: Separate client intent (commands) from state changes (events)

**Pros:**
- ✅ Clear separation of concerns
- ✅ Easy to add idempotency
- ✅ Natural fit for Diuna's existing event-driven architecture
- ✅ Client ID + Request ID prevent circular updates
- ✅ Optimistic updates work cleanly
- ✅ Used by Netflix, Figma, Google Docs

**Cons:**
- ➖ Additional layer (CommandHandler)
- ➖ More code than simple filtering

**Best for**: Systems with clear user actions (set color, adjust brightness, start animation)

---

#### Solution B: Event Sourcing
**What it is**: Store immutable event log, rebuild state from events

**Pros:**
- ✅ Complete audit trail
- ✅ Time-travel debugging
- ✅ Undo/redo built-in

**Cons:**
- ❌ High complexity
- ❌ Event replay overhead
- ❌ Storage requirements
- ❌ Overkill for LED control

**Best for**: Banking, healthcare, systems requiring audit compliance

---

#### Solution C: CQRS (Command Query Responsibility Segregation)
**What it is**: Separate write model from read model

**Pros:**
- ✅ Scales reads and writes independently
- ✅ Optimized query models

**Cons:**
- ❌ Very complex
- ❌ Eventual consistency issues
- ❌ Not needed for Diuna's scale

**Best for**: Large systems with read-heavy workloads (10k+ users)

---

#### Solution D: Simple Client Filtering
**What it is**: Client ignores events it sent

```javascript
// Client-side only
socket.on('zone:state_changed', (data) => {
  if (data.from_client_id === myClientId) {
    return; // Ignore
  }
  updateState(data);
});
```

**Pros:**
- ✅ Minimal code
- ✅ Easy to implement

**Cons:**
- ❌ Client-side filtering unreliable (client can be malicious)
- ❌ No deduplication
- ❌ No server-side control
- ❌ Doesn't scale

**Best for**: Prototypes, demos, single-developer projects

---

#### Solution E: Server-Side State Only
**What it is**: No optimistic updates, wait for server response

**Pros:**
- ✅ Simple
- ✅ No conflicts

**Cons:**
- ❌ Laggy UI (wait for round-trip)
- ❌ Poor UX for remote users
- ❌ Doesn't leverage modern real-time patterns

**Best for**: Traditional request/response web apps

---

## Recommended Architecture

### Why Command Pattern?

**Perfect fit for Diuna because:**
1. ✅ **Existing event-driven architecture** - Already has EventBus and ZoneStateChangedEvent
2. ✅ **Clear command semantics** - set_color, set_brightness, start_animation are natural commands
3. ✅ **Minimal changes to existing code** - ZoneService stays the same
4. ✅ **Scales to multiple clients** - Used by Netflix at massive scale
5. ✅ **Supports optimistic updates** - Fast UI feedback
6. ✅ **Professional standard** - Industry-proven pattern

**Not overkill because:**
- Diuna already has complexity (async, EventBus, frame management)
- Adding 2-3 new files is proportional
- Clean architecture pays off as features grow

---

## Data Flow Diagrams

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
│  ┌────────────┐      ┌────────────┐      ┌────────────┐            │
│  │  Browser A │      │  Browser B │      │  Mobile    │            │
│  │            │      │            │      │  App       │            │
│  └─────┬──────┘      └─────┬──────┘      └─────┬──────┘            │
│        │                   │                   │                     │
│        │ Commands          │ Commands          │ Commands            │
│        │ (zone:set_color)  │ (zone:set_brightness)                  │
│        │                   │                   │                     │
└────────┼───────────────────┼───────────────────┼─────────────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      WEBSOCKET LAYER                                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ WebSocketServer                                                │  │
│  │                                                                 │  │
│  │ - Receives commands from clients                               │  │
│  │ - Routes to CommandHandler                                     │  │
│  │ - Sends response ONLY to sender                                │  │
│  │ - Broadcasts state changes to ALL except sender ⭐            │  │
│  └───────────────┬───────────────────────────────────────────────┘  │
└──────────────────┼──────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      COMMAND LAYER (NEW)                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ CommandHandler                                                 │  │
│  │                                                                 │  │
│  │ 1. Validate command (bounds, permissions)                      │  │
│  │ 2. Check deduplication (request_id cache)                      │  │
│  │ 3. Delegate to ZoneService                                     │  │
│  │ 4. Return success/error                                        │  │
│  └───────────────┬───────────────────────────────────────────────┘  │
└──────────────────┼──────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER (EXISTING)                        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ ZoneService                                                     │  │
│  │                                                                 │  │
│  │ - Mutates zone state                                           │  │
│  │ - Persists to state.json                                       │  │
│  │ - Publishes ZoneStateChangedEvent ⭐                           │  │
│  └───────────────┬───────────────────────────────────────────────┘  │
└──────────────────┼──────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EVENT BUS (EXISTING)                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ EventBus                                                        │  │
│  │                                                                 │  │
│  │ Publishes: ZoneStateChangedEvent                               │  │
│  │   {                                                             │  │
│  │     zone_id: FLOOR,                                            │  │
│  │     color: red,                                                │  │
│  │     client_id: "client_A",  ⭐ NEW                            │  │
│  │     source_type: "command"   ⭐ NEW                            │  │
│  │   }                                                             │  │
│  └───────┬───────────────────────────────────┬───────────────────┘  │
└──────────┼───────────────────────────────────┼──────────────────────┘
           │                                   │
           │ Subscribers                       │ Subscribers
           ▼                                   ▼
┌──────────────────────────┐       ┌──────────────────────────┐
│ StaticModeController     │       │ WebSocketServer          │
│                          │       │                          │
│ Filters events by        │       │ Broadcasts to ALL        │
│ source_type:             │       │ clients EXCEPT           │
│ - "internal" ✓           │       │ client_id="client_A" ⭐  │
│ - "hardware" ✓           │       │                          │
│ - "command"  ✗ skip      │       │ Prevents circular!       │
│                          │       │                          │
│ Submits frame to         │       └──────────────────────────┘
│ FrameManager             │
└──────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ FrameManager             │
│                          │
│ Renders to Hardware      │
└──────────────────────────┘
```

### Detailed Flow: Client A Sets Color

```
CLIENT A                  BACKEND                     CLIENT B
   │                         │                           │
   │ 1. User clicks red      │                           │
   ├─────────────────────────┤                           │
   │ Optimistic update:      │                           │
   │ zone.color = red        │                           │
   │ (UI instant ✓)          │                           │
   │                         │                           │
   │ 2. Emit command         │                           │
   │─────────────────────────>                           │
   │ zone:set_color(         │                           │
   │   request_id: REQ123,   │                           │
   │   zone_id: FLOOR,       │                           │
   │   color: red            │                           │
   │ )                       │                           │
   │                         │                           │
   │                         │ 3. CommandHandler         │
   │                         │    - Validate ✓           │
   │                         │    - Dedup check ✓        │
   │                         │    - Call ZoneService     │
   │                         │                           │
   │                         │ 4. ZoneService            │
   │                         │    - zone.color = red     │
   │                         │    - Save to state.json   │
   │                         │    - Publish event:       │
   │                         │      ZoneStateChangedEvent│
   │                         │      {                    │
   │                         │        zone: FLOOR,       │
   │                         │        color: red,        │
   │                         │        client_id: A, ⭐   │
   │                         │        source: command    │
   │                         │      }                    │
   │                         │                           │
   │                         │ 5. EventBus fires         │
   │                         │    ├─> StaticModeCtrl    │
   │                         │    │   (source=command,   │
   │                         │    │    SKIP render)      │
   │                         │    │                      │
   │                         │    └─> WebSocketServer   │
   │                         │        (broadcast)        │
   │                         │                           │
   │ 6. Response to A only   │                           │
   │<─────────────────────────                           │
   │ {success: true,         │                           │
   │  request_id: REQ123}    │                           │
   │                         │                           │
   │ ⚠️ NO state_changed     │ 7. Broadcast to B        │
   │    sent to A!           │──────────────────────────>│
   │    (client_id filter)   │ zone:state_changed(      │
   │                         │   zone: FLOOR,            │
   │                         │   color: red              │
   │                         │ )                         │
   │                         │                           │
   │                         │                           │ 8. Client B updates
   │                         │                           │    zone.color = red
   │                         │                           │    (UI updates ✓)
   │                         │                           │
```

### Hardware Event Flow (for comparison)

```
HARDWARE                  BACKEND                     CLIENTS A & B
   │                         │                           │
   │ 1. User turns knob      │                           │
   │    (physical encoder)   │                           │
   │                         │                           │
   │ 2. GPIO interrupt       │                           │
   ├─────────────────────────>                           │
   │ ENCODER_ROTATE event    │                           │
   │                         │                           │
   │                         │ 3. LEDController          │
   │                         │    receives event         │
   │                         │                           │
   │                         │ 4. ZoneService            │
   │                         │    - zone.brightness += 5 │
   │                         │    - Save                 │
   │                         │    - Publish event:       │
   │                         │      ZoneStateChangedEvent│
   │                         │      {                    │
   │                         │        zone: FLOOR,       │
   │                         │        brightness: 50,    │
   │                         │        client_id: null, ⭐│
   │                         │        source: hardware ⭐│
   │                         │      }                    │
   │                         │                           │
   │                         │ 5. EventBus fires         │
   │                         │    ├─> StaticModeCtrl    │
   │                         │    │   (source=hardware,  │
   │                         │    │    RENDER frame ✓)   │
   │                         │    │                      │
   │                         │    └─> WebSocketServer   │
   │                         │        (broadcast)        │
   │                         │                           │
   │                         │ 6. Broadcast to ALL      │
   │                         │    (no client filter)     │
   │                         │──────────────────────────>│
   │                         │ zone:state_changed(      │
   │                         │   zone: FLOOR,            │
   │                         │   brightness: 50          │
   │                         │ )                         │
   │                         │                           │
   │                         │                           │ 7. Clients A & B
   │                         │                           │    update state
   │                         │                           │    (UI updates ✓)
```

---

## Layer Separation

### Clean Architecture Layers

```
┌───────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Web UI     │  │   Mobile     │  │   Hardware   │        │
│  │  (React)     │  │   (Flutter)  │  │   (Encoders) │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│         │                  │                  │                │
│         │ Commands         │ Commands         │ GPIO Events   │
│         │                  │                  │                │
└─────────┼──────────────────┼──────────────────┼────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌───────────────────────────────────────────────────────────────┐
│                    TRANSPORT LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  WebSocket   │  │     MQTT     │  │ GPIO Handler │        │
│  │   Server     │  │   Broker     │  │              │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│         │                  │                  │                │
│         │ Parse            │ Parse            │ Parse          │
│         ▼                  ▼                  ▼                │
│  ┌──────────────────────────────────────────────────┐         │
│  │          Command Router                           │         │
│  └──────────────────────────────────────────────────┘         │
└─────────┬─────────────────────────────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER (NEW)                     │
│  ┌──────────────────────────────────────────────────┐         │
│  │           CommandHandler                          │         │
│  │                                                    │         │
│  │  Responsibilities:                                │         │
│  │  - Validation (bounds, permissions)               │         │
│  │  - Deduplication (request_id cache)               │         │
│  │  - Delegation to services                         │         │
│  │  - Error handling                                 │         │
│  └──────────────────────────────────────────────────┘         │
└─────────┬─────────────────────────────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────────────────────────────┐
│                    DOMAIN LAYER (EXISTING)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ ZoneService  │  │  Animation   │  │    Color     │        │
│  │              │  │   Service    │  │   Manager    │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│         │                  │                  │                │
│         │ Publishes events │                  │                │
│         ▼                  ▼                  ▼                │
│  ┌──────────────────────────────────────────────────┐         │
│  │           EventBus                                │         │
│  └──────────────────────────────────────────────────┘         │
└─────────┬─────────────────────────────────────────────────────┘
          │
          ▼
┌───────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │FrameManager  │  │ State JSON   │  │  GPIO/SPI    │        │
│  │              │  │ Persistence  │  │   Driver     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└───────────────────────────────────────────────────────────────┘
```

### Dependency Flow (DIP - Dependency Inversion Principle)

```
┌─────────────────────────────────────────────────────────────┐
│ WebSocketServer                                              │
│                                                              │
│ Depends on:                                                 │
│  - CommandHandler (interface)  ← NOT concrete class        │
│  - EventBus (interface)                                     │
│                                                              │
│ Does NOT depend on:                                         │
│  ✗ ZoneService (too low-level)                             │
│  ✗ FrameManager (infrastructure)                            │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ CommandHandler                                               │
│                                                              │
│ Depends on:                                                 │
│  - ZoneService (interface)                                  │
│  - EventBus (interface)                                     │
│                                                              │
│ Does NOT depend on:                                         │
│  ✗ WebSocket layer (too high-level)                        │
│  ✗ FrameManager (infrastructure)                            │
└─────────────────────────────────────────────────────────────┘
```

### Event Flow vs Command Flow

```
┌────────────────────────────────────────────────────────────┐
│ COMMANDS (Client → Server)                                 │
│                                                             │
│ Characteristics:                                           │
│ - Intent to change state                                   │
│ - Can be rejected (validation fails)                       │
│ - Requires acknowledgment                                  │
│ - Has originating client                                   │
│ - Includes idempotency key                                 │
│                                                             │
│ Examples:                                                  │
│ - SetZoneColorCommand                                      │
│ - AdjustBrightnessCommand                                  │
│ - StartAnimationCommand                                    │
│                                                             │
│ Direction: Client → Server only (unidirectional)          │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ EVENTS (Server → Everyone)                                 │
│                                                             │
│ Characteristics:                                           │
│ - Describes what happened                                  │
│ - Already occurred (immutable fact)                        │
│ - No acknowledgment needed                                 │
│ - Includes source info (for filtering)                     │
│ - Broadcast to all interested parties                      │
│                                                             │
│ Examples:                                                  │
│ - ZoneStateChangedEvent                                    │
│ - AnimationStartedEvent                                    │
│ - FrameRenderedEvent                                       │
│                                                             │
│ Direction: Server → Multiple subscribers                   │
│            (internal handlers + WebSocket clients)         │
└────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Foundation (Day 1)

**New Files:**
```bash
src/
├── models/
│   └── commands.py               # Command class hierarchy
├── services/
│   └── command_handler.py        # Validation + deduplication
└── websocket/
    ├── __init__.py
    └── server.py                 # Socket.IO integration
```

**Steps:**
1. Create command models with `client_id` + `request_id`
2. Implement CommandHandler with deduplication cache
3. Add unit tests for validation logic

**Time estimate:** 4-6 hours

---

### Phase 2: Event Enhancement (Day 1)

**Modify Files:**
```bash
src/models/events.py              # Add client_id, source_type fields
src/services/zone_service.py      # Pass metadata when publishing events
```

**Steps:**
1. Add new fields to `ZoneStateChangedEvent`
2. Update ZoneService methods to include source tracking
3. Update event tests

**Time estimate:** 2-3 hours

---

### Phase 3: WebSocket Integration (Day 2)

**New Files:**
```bash
src/websocket/
├── command_router.py             # Route commands to handlers
└── broadcast_manager.py          # Manage client subscriptions
```

**Modify Files:**
```bash
src/api/main.py                   # Mount Socket.IO server
```

**Steps:**
1. Install `python-socketio` dependency
2. Create WebSocketServer with client tracking
3. Implement selective broadcasting (filter by client_id)
4. Wire up command routing
5. Integration tests with mock clients

**Time estimate:** 6-8 hours

---

### Phase 4: Controller Updates (Day 2)

**Modify Files:**
```bash
src/controllers/led_controller/static_mode_controller.py
src/controllers/led_controller/animation_mode_controller.py
```

**Steps:**
1. Add event filtering by `source_type`
2. Skip rendering for WebSocket commands (already rendered)
3. Test hardware updates still work

**Time estimate:** 2-3 hours

---

### Phase 5: Frontend Integration (Day 3)

**Modify Files:**
```bash
frontend/src/hooks/useZones.ts           # Disable polling
frontend/src/services/websocket.ts       # Add command emitters
frontend/src/stores/zoneStore.ts         # Optimistic updates
```

**Steps:**
1. Disable REST polling (`refetchInterval: false`)
2. Add WebSocket listeners for state changes
3. Implement optimistic update pattern
4. Test with multiple browser tabs

**Time estimate:** 4-6 hours

---

### Phase 6: Testing & Documentation (Day 3)

**Tests:**
- Unit: CommandHandler deduplication
- Unit: Event filtering in controllers
- Integration: Full circular update prevention flow
- Manual: Multiple clients, hardware knob, concurrent updates

**Documentation:**
- WebSocket API contract (commands, events, error codes)
- Architecture decision record (why Command Pattern)
- Developer guide for adding new commands

**Time estimate:** 4-5 hours

---

### Total Estimate: 3 days (24-30 hours)

---

## Alternative Solutions (Detailed Analysis)

### Why NOT Event Sourcing?

**Event Sourcing Pattern:**
```python
# Store immutable events
event_store = [
    {"type": "ZoneCreated", "zone_id": 1, "timestamp": 0},
    {"type": "ColorSet", "zone_id": 1, "color": "red", "timestamp": 100},
    {"type": "BrightnessAdjusted", "zone_id": 1, "delta": 10, "timestamp": 200},
]

# Rebuild current state by replaying events
def rebuild_state():
    state = {}
    for event in event_store:
        apply_event(event, state)
    return state
```

**Why it's overkill for Diuna:**
- ❌ Storage overhead (every LED change = new event in DB)
- ❌ Replay time increases as history grows
- ❌ Complexity: snapshots, compaction, versioning
- ❌ No clear benefit for LED control (don't need time-travel)

**When you WOULD use it:**
- Financial transactions (audit trail required)
- Collaborative editing with undo/redo
- Compliance-heavy industries (healthcare)

---

### Why NOT CQRS?

**CQRS Pattern:**
```python
# Write model (commands)
class WriteModel:
    def set_zone_color(self, zone_id, color):
        # Validate, mutate, persist
        pass

# Read model (queries, optimized)
class ReadModel:
    def get_zones_by_color(self, color):
        # Query denormalized view
        pass
```

**Why it's overkill:**
- ❌ Adds eventual consistency complexity
- ❌ Requires sync between write/read models
- ❌ Diuna has simple queries (get all zones, get by ID)
- ❌ No read bottleneck to optimize

**When you WOULD use it:**
- 10k+ concurrent users
- Complex analytics queries
- Read-heavy workloads (90% reads, 10% writes)

---

### Why NOT Simple Client Filtering?

**Simple Pattern:**
```typescript
// Client sends command with flag
socket.emit('zone:set_color', { color: 'red', echo: false });

// Client ignores echoed events
socket.on('zone:state_changed', (data) => {
  if (data.echo === false && data.from_me) {
    return; // Ignore
  }
  updateState(data);
});
```

**Why it's insufficient:**
- ❌ No server-side control (client can cheat)
- ❌ No deduplication (network retries cause duplicates)
- ❌ Doesn't prevent controller re-rendering
- ❌ Brittle (easy to forget filtering logic)

**When you WOULD use it:**
- Proof of concept
- Single-developer hobby project
- Trusted clients only

---

## Recommendation Summary

### ✅ Use Command Pattern (Solution A)

**Reasons:**
1. **Perfect fit for Diuna's architecture**
   - Already event-driven
   - Clear command semantics
   - Minimal code changes

2. **Industry-proven at scale**
   - Netflix uses for personalization
   - Figma uses for collaborative editing
   - Stripe uses for payment processing

3. **Balanced complexity**
   - More than client filtering
   - Less than Event Sourcing or CQRS
   - Right level for Diuna's needs

4. **Future-proof**
   - Easy to add new commands
   - Supports multiple client types (web, mobile, MQTT)
   - Audit trail can be added later if needed

5. **Clean separation of concerns**
   - Commands = intent (client)
   - Events = state changes (server)
   - Controllers = rendering (hardware)

**Trade-offs accepted:**
- ➕ 2-3 new files (~500 lines total)
- ➕ Learning curve for new developers
- ➖ Worth it for scalability and maintainability

---

## Conclusion

The **Command Pattern** architecture is the recommended solution for Diuna because:

1. ✅ **Prevents circular updates** via client_id filtering
2. ✅ **Fits existing architecture** (event-driven, async)
3. ✅ **Scales to multiple clients** (proven by Netflix, Figma)
4. ✅ **Balanced complexity** (not too simple, not overkill)
5. ✅ **Future-proof** (easy to extend)

Alternative solutions (Event Sourcing, CQRS) are too complex for Diuna's current needs. Simple client filtering is too brittle and doesn't scale.

**Next steps:** Review this plan, ask questions, then proceed with Phase 1 implementation.

---

**Last updated:** 2025-12-18
**Architecture reviewer:** architecture-expert-sonnet
