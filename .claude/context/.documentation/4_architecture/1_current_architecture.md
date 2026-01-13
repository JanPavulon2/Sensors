# Current Async Architecture Analysis: Diuna LED System

**Last Updated:** 2026-01-02
**Focus:** How the application currently uses asyncio, code examples, data flows
**Assessment:** B- (Strong design with critical execution flaw)

---

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Event Loop Setup](#event-loop-setup)
3. [Task Coordination](#task-coordination)
4. [Render Pipeline Async Flow](#render-pipeline-async-flow)
5. [Animation Engine Async Pattern](#animation-engine-async-pattern)
6. [Event Bus Pattern](#event-bus-pattern)
7. [Concurrency Control](#concurrency-control)

---

## System Architecture Overview

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Diuna LED Control System                       │
│                    (Single asyncio Event Loop)                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input Layer          Coordination Layer       Output Layer      │
│  ────────────        ──────────────────       ──────────────    │
│                                                                  │
│  Keyboard ┐           EventBus ──┐          FrameManager ─────┐ │
│  Encoder  ├─→ Events ─→ (Pub/Sub) ├─→ Handlers ─→ Renders     │ │
│  Hardware ┘           ↓           │          ↓                 │ │
│                    Middleware      │      AnimationEngine       │ │
│                    Filtering       │      (Per-zone tasks)      │ │
│                                    └─→ Controllers             │ │
│                                       (State management)        │ │
│                                                                  │
│                                       Hardware Layer             │ │
│                                       ──────────────             │ │
│                                       ZoneStrip ────────→ LEDs   │ │
│                                       WS281xStrip               │ │
│                                       GPIO/DMA                  │ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Key Components and Their Async Roles

| Component | Location | Type | Purpose | Async Pattern |
|-----------|----------|------|---------|--------------|
| **FrameManager** | `engine/frame_manager.py` | Main loop | 60 FPS rendering | Long-running task |
| **AnimationEngine** | `animations/engine.py` | Coordinator | Manages per-zone animations | Task spawning |
| **EventBus** | `services/event_bus.py` | Pub-Sub | Publish/subscribe events | Handler dispatch |
| **TransitionService** | `services/transition_service.py` | Effect generator | Smooth fades & transitions | Async animation |
| **LedController** | `controllers/led_controller/` | Business logic | Mode changes, state updates | Event handler |
| **TaskRegistry** | `lifecycle/task_registry.py` | Monitor | Track all tasks | Metadata collection |
| **ShutdownCoordinator** | `lifecycle/shutdown_coordinator.py` | Lifecycle | Graceful shutdown | Priority-based handlers |
| **KeyboardInputAdapter** | `api/adapters/keyboard_input_adapter.py` | Input | Read keyboard | Task loop |
| **EncoderAdapter** | `api/adapters/encoder_adapter.py` | Input | Read encoder | Task loop |

---

## Event Loop Setup

### Application Startup (`main_asyncio.py`)

```python
# Lines 1-50: Imports and setup
import asyncio
from main_asyncio import main

# Lines 100-150: Logging and configuration setup
# (Synchronous initialization)

# Lines 150-240: main() coroutine definition
async def main():
    """Main application coroutine - runs in asyncio event loop."""

    # 1. Initialize services and components (sync)
    frame_manager = FrameManager(fps=60)
    event_bus = EventBus()
    animation_engine = AnimationEngine(frame_manager)
    led_controller = LedController(event_bus, animation_engine, ...)

    # 2. Setup shutdown coordination
    shutdown_coordinator = ShutdownCoordinator()
    shutdown_coordinator.register_handler(
        frame_manager.shutdown(),
        priority=10,
        description="Frame Manager"
    )

    # 3. Create and schedule tasks
    # CRITICAL TASK: Frame rendering at 60 FPS
    asyncio.create_task(frame_manager.start())  # ⚠️ Not tracked!

    # Input tasks
    keyboard_task = create_tracked_task(
        KeyboardInputAdapter(event_bus).run(),
        category=TaskCategory.INPUT,
        description="KeyboardInputAdapter"
    )

    # 4. Setup signal handlers for graceful shutdown
    def handle_signal(sig, frame):
        log.info(f"Received signal: {sig.name}")
        asyncio.create_task(shutdown_coordinator.shutdown_all())

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # 5. Wait for shutdown
    await shutdown_event.wait()

# Lines 316-324: Entry point
if __name__ == "__main__":
    try:
        asyncio.run(main())  # ← Creates event loop, runs main()
    except KeyboardInterrupt:
        log.info("Keyboard interrupt received")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
```

### What `asyncio.run()` Does

```
1. Create new event loop (if not already exists)
   ↓
2. Set it as current event loop
   ↓
3. Execute the main() coroutine
   ↓
4. On return, cancel pending tasks
   ↓
5. Close the event loop
   ↓
6. Exit program
```

**Key Point:** This runs on the **main thread** (Raspberry Pi OS thread). All tasks share this one thread and event loop.

---

## Task Coordination

### Task Creation Patterns

#### Pattern 1: Untracked Tasks (Problematic)

```python
# From main_asyncio.py:166
asyncio.create_task(frame_manager.start())
```

**What happens:**
```python
def create_task(coroutine):
    # Internally:
    task = Task(coroutine)           # Create task wrapper
    event_loop.add_task(task)        # Schedule it
    return task                      # Return reference (usually ignored!)
```

**Problem:**
- Task runs independently
- If it crashes, **application doesn't know**
- No monitoring or failure detection
- Critical for LED rendering but not protected!

#### Pattern 2: Tracked Tasks (Recommended)

```python
# From main_asyncio.py:187-191
keyboard_task = create_tracked_task(
    KeyboardInputAdapter(event_bus).run(),
    category=TaskCategory.INPUT,
    description="KeyboardInputAdapter"
)
```

**What happens:**

```python
def create_tracked_task(coro, category, description):
    task = asyncio.create_task(coro)  # Create task

    # Register in TaskRegistry
    registry.register(
        task=task,
        category=category,
        description=description
    )

    # Attach completion callback
    def on_done(completed_task):
        if completed_task.cancelled():
            registry.mark_cancelled(task)
        else:
            exc = completed_task.exception()
            if exc:
                registry.mark_failed(task, exc)
            else:
                registry.mark_success(task)

    task.add_done_callback(on_done)
    return task
```

**Benefit:**
- Task health monitored
- Failures detected (via `registry.failed()`)
- Can introspect all tasks
- Enables graceful shutdown

### Task Hierarchy in Diuna

```
asyncio.run(main())
│
├─ Task: main()
│  │
│  ├─ Task: frame_manager.start() ⚠️ NOT TRACKED
│  │  │
│  │  └─ Infinite loop: _render_loop()
│  │
│  ├─ Task: KeyboardInputAdapter.run() ✓ TRACKED
│  │  │
│  │  └─ Infinite loop: Read input → Publish events
│  │
│  ├─ Task: EncoderAdapter.run() ✓ TRACKED
│  │  │
│  │  └─ Infinite loop: Poll encoder → Publish events
│  │
│  ├─ Task: HardwarePolling.run() ✓ TRACKED
│  │  │
│  │  └─ Infinite loop: Check hardware → Publish events
│  │
│  ├─ Task: API server (Uvicorn) ✓ TRACKED
│  │  │
│  │  └─ Listen for HTTP/WebSocket requests
│  │
│  └─ Task: Animation loops (Per-zone, TRACKED)
│     │
│     ├─ Task: zone_0_animation_loop
│     ├─ Task: zone_1_animation_loop
│     └─ Task: zone_2_animation_loop
│
└─ Main thread waits for all tasks
```

---

## Render Pipeline Async Flow

### Frame Manager: The 60 FPS Heartbeat

**Location:** `src/engine/frame_manager.py`

**Core structure:**

```python
class FrameManager:
    """Manages LED frame rendering at target FPS."""

    def __init__(self, fps: int = 60):
        self.fps = fps
        self._lock = asyncio.Lock()  # Protects frame queue
        self.main_queues = {
            priority.value: deque() for priority in FramePriority
        }
        self.running = False

    async def start(self) -> None:
        """Main entry point - runs in asyncio event loop."""
        self.running = True
        try:
            await self._render_loop()
        except Exception as e:
            log.error(f"Render loop crashed: {e}", exc_info=True)
            raise
        finally:
            self.running = False

    async def _render_loop(self) -> None:
        """Main render loop @ target FPS - executes 60 times/second."""
        frame_delay = 1.0 / self.fps  # 0.0166s = 16.6ms

        while self.running:
            # ════════════════════════════════════════
            # PHASE 1: Handle pause/step requests
            # ════════════════════════════════════════
            if self.paused and not self.step_requested:
                await asyncio.sleep(0.01)
                continue

            self.step_requested = False

            # ════════════════════════════════════════
            # PHASE 2: Enforce hardware timing
            # ════════════════════════════════════════
            elapsed = time.perf_counter() - self.last_show_time

            # WS2811 requires minimum 2.75ms between frames
            if elapsed < WS2811Timing.MIN_FRAME_TIME_MS / 1000:
                await asyncio.sleep(
                    (WS2811Timing.MIN_FRAME_TIME_MS / 1000) - elapsed
                )

            # ════════════════════════════════════════
            # PHASE 3: Render frame
            # ════════════════════════════════════════
            try:
                frame = await self._drain_frames()  # Get next frame

                if frame:
                    self._render_atomic(frame)      # ⚠️ BLOCKING HERE!
                    self.frames_rendered += 1

            except Exception as e:
                log.error(f"Render error: {e}", exc_info=True)

            # ════════════════════════════════════════
            # PHASE 4: Timing adjustment
            # ════════════════════════════════════════
            await asyncio.sleep(frame_delay)
```

### Phase-by-Phase Timing Analysis

**At 60 FPS, each frame has 16.6ms budget:**

```
Time (ms)   | Operation              | Duration | Blocking?
────────────┼────────────────────────┼──────────┼──────────
0.0         | Start frame cycle      | -        | No
0.1         | Check if paused        | 0.1ms    | No (await sleep)
0.2         | Check hardware timing  | 0.1ms    | No
2.75        | (Wait for hardware)    | 2.6ms    | await sleep
5.35        | _drain_frames()        | 0.1ms    | Yes (async lock)
5.45        | _render_atomic()       | 2.75ms   | ❌ YES - BLOCKING!
8.2         | (DMA transfer)         | ~2.75ms  | Blocks event loop!
11.0        | Done rendering         | -        | Now can continue
11.0        | await asyncio.sleep()  | 5.6ms    | Yields to event loop
16.6        | Cycle repeats          | -        | Ready for next frame
```

**Critical Issue:** The 2.75ms DMA transfer (step 5.45-8.2) **blocks the event loop**. During this time:
- ❌ Keyboard input not processed
- ❌ API requests delayed
- ❌ Other animations starved
- ❌ Event bus handlers blocked

### Frame Draining: Async Lock Pattern

```python
async def _drain_frames(self) -> Optional[MainStripFrame]:
    """
    Get the highest-priority frame from queue.

    Lock ensures no race conditions when multiple
    animation tasks submit frames simultaneously.
    """
    async with self._lock:  # Acquire async lock
        # Check each priority level
        for priority_level in [
            FramePriority.TRANSITION,
            FramePriority.ANIMATION,
            FramePriority.STATIC
        ]:
            queue = self.main_queues[priority_level.value]
            if queue:
                return queue.popleft()  # Remove and return

        return None
    # Lock automatically released (even if exception)
```

**How this protects against race conditions:**

```
Scenario: Two animation zones (A and B) submit frames simultaneously

Without lock:
  Zone A.task:                    Zone B.task:
  if queue.empty(): ✓             if queue.empty(): ✓
                                  queue.append(B)
  queue.append(A)
  # A overwrites B? Data corruption!

With async lock:
  Zone A.task:                    Zone B.task:
  async with lock:                async with lock:
    acquire ✓                       wait...
    append(A)                       wait...
    release                         acquire ✓
                                    append(B)
                                    release
  # Both added safely in order
```

### Frame Rendering: The Blocking Problem

```python
def _render_atomic(self, frame: MainStripFrame) -> None:
    """Render frame to all LED strips - CURRENTLY BLOCKING!"""

    start_time = time.perf_counter()

    # Process each zone's pixels
    for zone_id, pixels in frame.zone_pixels.items():
        zone_strip = self.zone_strips[zone_id]

        # Create frame for this zone
        strip_frame = [
            Color(r, g, b)
            for r, g, b in pixels
        ]

        # Apply to hardware - BLOCKS HERE!
        zone_strip.apply_frame(strip_frame)

    elapsed = time.perf_counter() - start_time
    log.debug(f"Render took {elapsed*1000:.2f}ms")

    self.last_show_time = time.perf_counter()
```

**What happens in `zone_strip.apply_frame()`:**

```python
# From src/zone_layer/zone_strip.py
def apply_frame(self, pixels: List[Color]) -> None:
    """Apply pixels to hardware."""

    full_frame = self._build_full_frame(pixels)
    self.hardware.apply_frame(full_frame)  # ← BLOCKING!

# From src/hardware/led/ws281x_strip.py
def apply_frame(self, pixels):
    """Apply pixels to WS281x strip via DMA."""

    for i in range(len(pixels)):
        color = pixels[i]
        # Set in local buffer (fast)
        self._pixel_strip.setPixelColorRGB(i, r, g, b)

    # BLOCKS HERE: DMA transfer to physical LEDs
    self._pixel_strip.show()  # C extension - blocks ~2.75ms
```

**Why it blocks:**
- `_pixel_strip.show()` is a C extension (in rpi_ws281x library)
- Uses DMA (Direct Memory Access) on Raspberry Pi
- Transfers pixel data to physical WS2811 LEDs
- Requires precise timing (1.25µs ±600ns per bit)
- **Cannot yield to event loop** - hardware-controlled timing

---

## Animation Engine Async Pattern

### Location: `src/animations/engine.py`

### Animation Lifecycle

```python
class AnimationEngine:
    """Manages per-zone animations with independent task control."""

    def __init__(self, frame_manager: FrameManager):
        self.frame_manager = frame_manager
        self._lock = asyncio.Lock()  # Protects zone task tracking
        self.tasks: Dict[ZoneID, asyncio.Task] = {}
        self.active_anim_ids: Dict[ZoneID, AnimationID] = {}
        self.active_animations: Dict[ZoneID, BaseAnimation] = {}

    async def start_for_zone(
        self,
        zone_id: ZoneID,
        anim_id: AnimationID,
        params: dict
    ) -> None:
        """Start animation for a zone (or restart if already running)."""

        async with self._lock:
            # Stop previous animation if exists
            if zone_id in self.tasks:
                await self.stop_for_zone(zone_id)

            # Get animation class
            AnimClass = self.ANIMATIONS.get(anim_id)
            if not AnimClass:
                log.error(f"Unknown animation: {anim_id}")
                return

            # Build animation instance
            zone = self.zone_manager.get_zone(zone_id)
            anim = AnimClass(
                zone=zone,
                params=params,
                color_manager=self.color_manager
            )

            # Create task for this animation
            task = create_tracked_task(
                self._run_loop(zone_id, anim),
                category=TaskCategory.ANIMATION,
                description=f"Animation: {zone_id.name} - {anim_id.value}"
            )

            # Store for later management
            self.tasks[zone_id] = task
            self.active_anim_ids[zone_id] = anim_id
            self.active_animations[zone_id] = anim

    async def _run_loop(self, zone_id: ZoneID, animation: BaseAnimation):
        """Per-zone animation loop - runs until animation finishes."""

        frame_count = 0

        try:
            while True:
                # Call animation.step() to get next frame
                frame = await animation.step()

                if frame is None:
                    # Animation has no frame yet
                    await asyncio.sleep(0)  # ⚠️ Busy loop!
                    continue

                # Submit frame to FrameManager
                await self.frame_manager.push_frame(frame)
                frame_count += 1

                # Yield to event loop
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            # Normal shutdown requested
            log.debug(
                f"Animation task for {zone_id.name} "
                f"cancelled after {frame_count} frames"
            )

        except Exception as e:
            # Unexpected error
            log.error(
                f"Animation error in {zone_id.name}: {e}",
                exc_info=True
            )
            raise

        finally:
            # Cleanup
            log.info(
                f"Animation finished for {zone_id.name} "
                f"after {frame_count} frames"
            )
```

### Frame Submission Pattern

```python
# From frame_manager.py:171-212
async def push_frame(self, frame: Frame) -> None:
    """Submit frame to be rendered (async-safe)."""

    async with self._lock:  # Protect queue

        if isinstance(frame, SingleZoneFrame):
            # Convert to MainStripFrame
            msf = MainStripFrame(...)

            # Add to priority queue
            self.main_queues[msf.priority.value].append(msf)

        elif isinstance(frame, MainStripFrame):
            self.main_queues[frame.priority.value].append(frame)

        elif isinstance(frame, PixelFrame):
            # Handle pixel-level updates
            ...
```

**Async Safety:**
- Lock protects queue append operations
- Multiple animations can submit simultaneously without collision
- Each zone's animation runs in its own task
- Tasks are independent - one animation crash doesn't affect others

### Per-Zone Task Independence

```
Main loop (Frame Manager):        Zone 0 animation:        Zone 1 animation:
─────────────────────────          ──────────────────       ──────────────────
_render_loop()                      _run_loop(zone_0)       _run_loop(zone_1)
│                                   │                       │
├─ await _drain_frames()            ├─ await step()         ├─ await step()
│  (Blocking on lock)               │                       │
├─ await sleep()                    ├─ await push_frame()   ├─ await push_frame()
│  (5.6ms)                          │                       │
│                                   ├─ await sleep(0)       ├─ await sleep(0)
│  ← Can handle next frame         │                       │
│     from zone_0 or zone_1       │                       │
```

**Key Advantage:** Animations on different zones never block each other. If Zone 0's animation takes 2ms to generate a frame, Zone 1's animation continues normally.

---

## Event Bus Pattern

### Location: `src/services/event_bus.py`

### Architecture

```python
class EventBus:
    """Publish-Subscribe event system - mixed async/sync handlers."""

    def __init__(self):
        # Handlers storage
        self._handlers: Dict[str, List[HandlerEntry]] = {}

        # Middleware for event filtering/transformation
        self._middleware: List[Callable[[Event], Optional[Event]]] = []

        # Event history for debugging
        self._event_history: List[Event] = []
        self._history_limit = 100

    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        filter_fn: Optional[Callable] = None
    ) -> Subscription:
        """Register handler for event type."""

        if event_type not in self._handlers:
            self._handlers[event_type] = []

        entry = HandlerEntry(
            handler=handler,
            filter_fn=filter_fn
        )

        self._handlers[event_type].append(entry)

        return Subscription(self, event_type, handler)

    async def publish(self, event: Event) -> None:
        """Publish event to all subscribed handlers."""

        # ════════════════════════════════════════
        # Step 1: Middleware pipeline
        # ════════════════════════════════════════
        for middleware in self._middleware:
            # Middleware functions are SYNC (must be fast!)
            processed_event = middleware(event)
            if processed_event is None:
                return  # Event blocked
            event = processed_event

        # ════════════════════════════════════════
        # Step 2: Record in history
        # ════════════════════════════════════════
        self._event_history.append(event)
        if len(self._event_history) > self._history_limit:
            self._event_history.pop(0)  # ⚠️ O(n) operation!

        # ════════════════════════════════════════
        # Step 3: Dispatch to handlers
        # ════════════════════════════════════════
        handlers = self._handlers.get(event.type, [])

        for handler_entry in handlers:
            # Filter check
            if handler_entry.filter_fn:
                if not handler_entry.filter_fn(event):
                    continue

            try:
                # Auto-detect async vs sync handlers
                if asyncio.iscoroutinefunction(handler_entry.handler):
                    # Handler is async - await it
                    await handler_entry.handler(event)
                else:
                    # Handler is sync - call directly
                    handler_entry.handler(event)

            except Exception as e:
                log.error(
                    f"Handler failed: {handler_entry.handler.__name__} "
                    f"for event {event.type}",
                    exc_info=True
                )
                # Continue to next handler (fault tolerance)
```

### Async Handler Pattern Example

```python
# From led_controller.py - subscribes to events
event_bus.subscribe(
    "key_pressed",
    led_controller.on_key_pressed  # Async handler
)

# Handler implementation
class LedController:
    async def on_key_pressed(self, event: KeyPressedEvent) -> None:
        """Handle key press event (async handler)."""

        if event.key == 'A':
            # Start animation
            await self.animation_engine.start_for_zone(
                zone_id=ZoneID.ZONE_0,
                anim_id=AnimationID.STROBE,
                params={}
            )

        elif event.key == 'S':
            # Stop animation
            await self.animation_engine.stop_for_zone(ZoneID.ZONE_0)
```

### Handler Execution Flow

```
Keyboard input → KeyboardAdapter → event_bus.publish()
                                           │
                                    ┌──────┴──────┐
                                    ↓             ↓
                            Middleware       Handlers:
                            Pipeline         ──────────
                            ────────────     • on_key_pressed [async]
                            • Validate       • log_event [sync]
                            • Transform      • send_websocket [async]
                            • Filter         • save_to_state [sync]
                                    │
                                    ↓
                          EventBus.publish():

                          for handler in handlers:
                            if async: await handler(event)
                            else: handler(event)
```

**Key Feature:** Mixed async/sync handlers allow:
- ✅ Async handlers: `await` for I/O operations
- ✅ Sync handlers: Fast operations without overhead
- ✅ Automatic detection: No need to manually choose
- ✅ Fault tolerance: One handler failing doesn't stop others

---

## Concurrency Control

### Async Locks: Protection Against Race Conditions

#### Lock 1: FrameManager Queue Lock

**Location:** `frame_manager.py:117`

```python
self._lock = asyncio.Lock()

# Protected operations:
async def push_frame(self, frame):
    async with self._lock:
        self.main_queues[priority].append(frame)
```

**Why needed:** Multiple animation tasks (`_run_loop`) submit frames simultaneously. Without lock:
```
Frame A submission:         Frame B submission:
pos = len(queue)           pos = len(queue)  # Same position!
queue.append(frame_a)      queue.append(frame_b)
# Collision! Data corruption possible
```

#### Lock 2: AnimationEngine Task Lock

**Location:** `animations/engine.py:63`

```python
self._lock = asyncio.Lock()

async def start_for_zone(self, zone_id, anim_id, params):
    async with self._lock:
        # Stop old animation
        if zone_id in self.tasks:
            task = self.tasks.pop(zone_id)
            task.cancel()

        # Start new animation
        task = asyncio.create_task(...)
        self.tasks[zone_id] = task
```

**Why needed:** Preventing race between stopping and starting animations.

#### Lock 3: TransitionService Lock

**Location:** `transition_service.py:146`

```python
self._transition_lock = asyncio.Lock()

async def fade_in(self, target_frame, config):
    async with self._transition_lock:
        # Only one transition can run at a time
        for step in range(steps):
            faded = [color.with_brightness(...) for color in target_frame]
            await self.frame_manager.push_frame(faded)
            await asyncio.sleep(step_delay)
```

**Why needed:** Two transitions overlapping would create flickering.

### Race Condition Audit

#### ✅ SAFE: Frame Queue Access

**Status:** Protected by `_lock` in both read and write

```python
async def push_frame(self):
    async with self._lock:  # ✓ Write protected

async def _drain_frames(self):
    async with self._lock:  # ✓ Read protected
```

#### ⚠️ POTENTIAL ISSUE: Animation Cleanup Race

**Location:** `animations/engine.py:126-151`

```python
async def stop_for_zone(self, zone_id):
    task = None
    async with self._lock:
        task = self.tasks.pop(zone_id, None)

    # ⚠️ WINDOW: Another task could call start_for_zone() here!

    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Clean up state OUTSIDE lock
    async with self._lock:
        self.active_anim_ids.pop(zone_id, None)
        self.active_animations.pop(zone_id, None)
```

**Scenario:**
```
Timeline:
0ms: stop_for_zone() acquires lock, pops task
1ms: Lock released
2ms: Another coroutine calls start_for_zone()
     → Acquires lock, creates NEW task
3ms: stop_for_zone() cancels task (WRONG TASK!)
4ms: stop_for_zone() cleans up state (removes NEW task)
     Result: New animation removed! (Bug)
```

**Fix:** See [3_issues_and_fixes.md](3_issues_and_fixes.md)

#### ✅ SAFE: Zone Render State

**Status:** Only accessed from `_render_loop()` (single task)

```python
# In _render_loop (single task):
for zid, pix in merged.items():
    self.zone_render_states[zid].pixels = pix  # Only this task writes
```

**No lock needed:** Single task accessing (guaranteed serial access)

---

## Summary: Current Architecture Strengths

1. ✅ **Event-driven design** - All input flows through EventBus
2. ✅ **Per-zone isolation** - Each animation in separate task
3. ✅ **Proper async locks** - Queue and task management protected
4. ✅ **Graceful shutdown** - Priority-based coordinator with timeouts
5. ✅ **Task monitoring** - TaskRegistry tracks all tasks
6. ✅ **Mixed async/sync handlers** - Flexible event processing

## Critical Weaknesses

1. ❌ **Blocking hardware calls** - DMA transfer blocks event loop
2. ❌ **Untracked critical task** - Frame manager not in TaskRegistry
3. ⚠️ **Animation cleanup race** - Potential race condition in stop sequence
4. ❌ **Busy loops** - `sleep(0)` in animation engine

See [3_issues_and_fixes.md](3_issues_and_fixes.md) for detailed solutions.

---

## Next: Async Patterns

Read [2_async_patterns.md](2_async_patterns.md) for specific code examples of good and bad patterns found in the codebase.
