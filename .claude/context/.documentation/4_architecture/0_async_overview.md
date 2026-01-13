# Async/Await and Asyncio Fundamentals in Diuna

**Last Updated:** 2026-01-02
**Audience:** Developers new to async programming, understanding Diuna's LED control architecture
**Status:** Complete analysis with code examples from the actual codebase

---

## Table of Contents
1. [What is Async/Await?](#what-is-asyncawait)
2. [Event Loop Mechanics](#event-loop-mechanics)
3. [How Diuna Uses Asyncio](#how-diuna-uses-asyncio)
4. [Task Lifecycle](#task-lifecycle)
5. [Key Concepts Explained](#key-concepts-explained)

---

## What is Async/Await?

### Simple Explanation

**Traditional Programming (Synchronous):**
```
┌─────────────────────────────────────┐
│ Task 1: Request data from network   │
│ ⏸️ WAIT - entire program pauses    │
│ Receive response                    │
│ ✓ Continue to Task 2                │
└─────────────────────────────────────┘
     ↓
┌─────────────────────────────────────┐
│ Task 2: Process data                │
│ ✓ Complete                          │
└─────────────────────────────────────┘
```

**Async Programming:**
```
┌─────────────────────────────────────┐
│ Task 1: Request data                │
│ 🚀 DON'T WAIT - yield control       │
│ ↓ (event loop runs other tasks)     │
│ ← Receive response, resume          │
└─────────────────────────────────────┘
      ↑           ↓
      │     ┌─────────────────────────┐
      │     │ Task 2: Render LED frame│
      │     │ ✓ Complete quickly      │
      │     └─────────────────────────┘
      │           ↓
      │     ┌─────────────────────────┐
      │     │ Task 3: Handle keyboard │
      │     │ ✓ Responsive            │
      │     └─────────────────────────┘
      └─────────────────────────────────
```

### Core Concepts

| Concept | Explanation | Diuna Example |
|---------|-------------|---------------|
| **coroutine** | A pausable function that can `await` | `async def _render_loop()` |
| **await** | Pause here, let other tasks run | `await asyncio.sleep(0.016)` |
| **event loop** | Schedules and runs coroutines | `asyncio.run(main())` |
| **task** | A scheduled coroutine | Frame manager render loop |
| **async context manager** | Resource cleanup with async/await | `async with lock:` |

---

## Event Loop Mechanics

### What is the Event Loop?

The event loop is **a single thread that schedules and executes multiple coroutines**, switching between them at strategic points:

```python
# From main_asyncio.py:316
if __name__ == "__main__":
    asyncio.run(main())  # ← This creates and runs the event loop
```

**What `asyncio.run()` does:**

```
1. Create a fresh event loop
2. Run the main() coroutine until it completes
3. Cancel pending tasks
4. Close the event loop
5. Exit program
```

### How the Event Loop Switches Between Tasks

**Diuna's startup creates multiple concurrent tasks:**

```python
# From main_asyncio.py:165-200

# Task 1: Render at 60 FPS
asyncio.create_task(frame_manager.start())

# Task 2: Run API server
api_task = asyncio.create_task(
    uvicorn.run(api_app, ...)
)

# Task 3: Handle keyboard input
keyboard_task = create_tracked_task(
    KeyboardInputAdapter(event_bus).run(),
    category=TaskCategory.INPUT
)

# Task 4: Handle encoder
encoder_task = create_tracked_task(
    EncoderAdapter(event_bus).run(),
    category=TaskCategory.INPUT
)

# Task 5: Listen to hardware polling
hardware_task = create_tracked_task(
    HardwarePolling(event_bus).run(),
    category=TaskCategory.HARDWARE
)
```

**The event loop schedules these like this:**

```
Time (ms) | Frame Manager  | API Server    | Keyboard      | Encoder       | Hardware
----------|----------------|---------------|---------------|---------------|----------
0         | Render frame 1 | Idle (await)  | Idle (await)  | Idle (await)  | Idle
1         | ← await show() | Idle          | Idle          | Idle          | Idle
4         | ✓ Continue     | Idle          | Idle          | Idle          | Idle
5         | ← await sleep  | Check API req | Idle          | Idle          | Idle
6         | Waiting        | Handle GET    | Idle          | Idle          | Idle
7         | Waiting        | ← await resp  | Idle          | Check input   | Idle
8         | Waiting        | Waiting       | ← await read  | Waiting       | Idle
9         | Waiting        | Waiting       | Idle (no key) | ← await read  | Idle
10        | Waiting        | Waiting       | Idle          | Idle          | ← await
11        | Waiting        | Waiting       | Idle          | Idle          | Check sensors
16        | Ready! Render  | Waiting       | Idle          | Idle          | Idle
17        | Render frame 2 | Response OK   | Idle          | Idle          | Idle
...
```

### Key Insight: Pause Points (`await`)

The event loop **only switches between tasks at `await` points**:

```python
async def _render_loop(self) -> None:
    """Main render loop @ target FPS."""
    frame_delay = 1.0 / self.fps  # 60 FPS = 0.0166s

    while self.running:
        # PAUSE POINT 1: Can other tasks run here?
        if self.paused and not self.step_requested:
            await asyncio.sleep(0.01)  # ← YES! Event loop switches here
            continue

        elapsed = time.perf_counter() - self.last_show_time
        if elapsed < WS2811Timing.MIN_FRAME_TIME_MS / 1000:
            # PAUSE POINT 2: YES, event loop can run other tasks
            await asyncio.sleep(
                (WS2811Timing.MIN_FRAME_TIME_MS / 1000) - elapsed
            )

        try:
            # PAUSE POINT 3: YES, draining frames involves async lock
            frame = await self._drain_frames()
            if frame:
                # NO PAUSE HERE - _render_atomic is synchronous
                # This blocks the event loop!
                self._render_atomic(frame)  # ← CRITICAL ISSUE (see 3_issues_and_fixes.md)
                self.frames_rendered += 1
        except Exception as e:
            log.error(f"Render error: {e}", exc_info=True)

        # PAUSE POINT 4: YES, yield to event loop
        await asyncio.sleep(frame_delay)  # ← Event loop switches here
```

**Critical Rule:** Between `await` points, the event loop **cannot switch tasks**. If code runs for 3ms without `await`, all other tasks wait 3ms.

---

## How Diuna Uses Asyncio

### Architecture Overview

Diuna combines **multiple concurrent subsystems** via asyncio:

```
┌─────────────────────────────────────────────────────────────┐
│                  asyncio.run(main())                        │
│                                                             │
│ Single-threaded event loop coordinating:                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────┐  ┌──────────────────────┐         │
│  │  RENDERING (60FPS) │  │  API SERVER          │         │
│  │ ─────────────────  │  │ ──────────────────── │         │
│  │ FrameManager       │  │ Uvicorn + FastAPI    │         │
│  │ AnimationEngine    │  │ WebSocket for live    │         │
│  │ TransitionService  │  │ updates              │         │
│  └────────────────────┘  └──────────────────────┘         │
│           ↕                        ↕                        │
│  ┌────────────────────┐  ┌──────────────────────┐         │
│  │  INPUT HANDLING    │  │  HARDWARE POLLING    │         │
│  │ ─────────────────  │  │ ──────────────────── │         │
│  │ KeyboardInput      │  │ EncoderAdapter       │         │
│  │ EncoderAdapter     │  │ HardwarePolling      │         │
│  │ Publishes to       │  │ Publishes to         │         │
│  │ EventBus           │  │ EventBus             │         │
│  └────────────────────┘  └──────────────────────┘         │
│           ↕                        ↕                        │
│           └────────┬───────────────┘                       │
│                    ↓                                        │
│           ┌────────────────────┐                           │
│           │    EVENT BUS       │                           │
│           │ ──────────────────  │                           │
│           │ Pub-Sub Event       │                           │
│           │ Distribution        │                           │
│           │ (sync & async       │                           │
│           │  handlers)          │                           │
│           └────────────────────┘                           │
│                    ↑                                        │
│                    ↓                                        │
│           ┌────────────────────┐                           │
│           │   CONTROLLERS      │                           │
│           │ ──────────────────  │                           │
│           │ LedController       │                           │
│           │ Triggers animations │                           │
│           │ Manages state       │                           │
│           └────────────────────┘                           │
│                    ↓                                        │
│           ┌────────────────────┐                           │
│           │  HARDWARE CONTROL  │                           │
│           │ ──────────────────  │                           │
│           │ ZoneStrip          │                           │
│           │ WS281xStrip        │                           │
│           │ GPIO/DMA control   │                           │
│           └────────────────────┘                           │
│                    ↓                                        │
│           ┌────────────────────┐                           │
│           │  LED STRIPS        │                           │
│           │ ──────────────────  │                           │
│           │ WS2811 LEDs        │                           │
│           │ (Raspberry Pi GPIO)│                           │
│           └────────────────────┘                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Data Flows

#### 1. Rendering Pipeline (60 FPS Loop)

```python
# Frame Manager: Main render loop
async def _render_loop(self) -> None:
    frame_delay = 1.0 / self.fps  # 16.6ms for 60 FPS

    while self.running:
        # Enforce hardware timing constraints
        await self._wait_for_frame_time()

        # Get next frame from queue (may have come from animation)
        frame = await self._drain_frames()

        if frame:
            # Render to all LED strips (currently BLOCKING - critical issue!)
            self._render_atomic(frame)

        # Yield to event loop (60 FPS)
        await asyncio.sleep(frame_delay)
```

**Data flow:**
```
Animation.step()
    ↓ [frame object]
AnimationEngine._run_loop()
    ↓ await push_frame()
FrameManager.push_frame()
    ↓ [enqueued in priority queue]
FrameManager._render_loop()
    ↓ await _drain_frames()
    ↓ await asyncio.sleep(frame_delay)  [60 FPS timing]
FrameManager._render_atomic()  [SYNCHRONOUS - renders to hardware]
    ↓
ZoneStrip.apply_frame()
    ↓
WS281xStrip.show()  [BLOCKING - 2.75ms minimum]
    ↓
Raspberry Pi GPIO [DMA transfer]
    ↓
Physical WS2811 LEDs [Colors displayed]
```

#### 2. Event Handling Pipeline (Responsive Input)

```python
# Keyboard input example
async def _input_loop(self):
    """Read keyboard input and publish events."""
    while self.running:
        key_pressed = await asyncio.to_thread(
            getch  # or similar non-blocking read
        )
        if key_pressed:
            # Publish event to EventBus
            event = KeyPressedEvent(key=key_pressed)
            await self.event_bus.publish(event)

        await asyncio.sleep(0)  # Yield to event loop
```

**Data flow:**
```
Keyboard input
    ↓
KeyboardInputAdapter.run()
    ↓ await event_bus.publish()
EventBus.publish()
    ↓ [to all subscribed handlers]
LedController.on_key_pressed()
    ↓ await animation_engine.start_for_zone()
AnimationEngine.start_for_zone()
    ↓ [creates animation task]
    ↓ await self.frame_manager.push_frame()
[Next render loop picks up frame]
    ↓
User sees LED animation
```

### Real Example: Mode Change Sequence

**What happens when user presses key 'A' (change to animation mode)?**

```
Time | Component | Action | Async?
-----|-----------|--------|-------
0ms  | Keyboard  | Read key 'A' | await asyncio.to_thread(read_key)
0ms  | EventBus  | Publish KeyPressedEvent | await event_bus.publish()
1ms  | Controller| on_key_pressed handler | await animation_engine.start_animation()
1ms  | AnimEngine| Create animation task | asyncio.create_task()
2ms  | EventBus  | Publish AnimationStartedEvent | await event_bus.publish()
2ms  | FrameManager| Animation starts submitting frames | await push_frame()
16ms | FrameManager| Render loop picks up first frame | (already in queue)
16ms | FrameManager| _render_atomic() called | BLOCKING 2.75ms!
18.75ms | FrameManager| Resume (hardware call done)
19ms | FrameManager| await asyncio.sleep(16.6ms) | Resume next frame cycle
```

---

## Task Lifecycle

### Task Creation Patterns in Diuna

#### Pattern 1: Fire-and-Forget with `asyncio.create_task()`

```python
# From main_asyncio.py:166
asyncio.create_task(frame_manager.start())
```

**What happens:**
1. Task created and immediately scheduled
2. No reference kept to task
3. Task runs independently in event loop
4. **Problem:** If task crashes, application continues silently!

**When used in Diuna:**
- Frame manager startup (critical!)
- Should use tracked task pattern instead

#### Pattern 2: Tracked Tasks with TaskRegistry

```python
# From main_asyncio.py:187-191
keyboard_task = create_tracked_task(
    KeyboardInputAdapter(event_bus).run(),
    category=TaskCategory.INPUT,
    description="KeyboardInputAdapter"
)
```

**What happens:**
1. Task created via `asyncio.create_task()`
2. Registered in TaskRegistry with metadata
3. Done callback attached automatically
4. If crashes: failure detected, can trigger shutdown
5. Can be introspected: `registry.failed()`, `registry.list_all()`

**When used in Diuna:**
- All critical long-running tasks
- Input handlers (keyboard, encoder)
- Hardware polling
- API server
- **Best practice:** Use for everything except internal animation loops

### Complete Task Lifecycle

```
1. CREATE
   ↓
   asyncio.create_task(coroutine)
   OR
   create_tracked_task(coroutine, ...)

2. SCHEDULE
   ↓
   Event loop adds to internal queue

3. RUN
   ↓
   Event loop executes until first await

4. AWAIT
   ↓
   Coroutine pauses at await point
   Event loop switches to another task

5. RESUME
   ↓
   When awaited operation completes,
   coroutine resumes after await point

6. REPEAT (Steps 3-5)
   ↓
   Until coroutine reaches end or exception

7. COMPLETE
   ↓
   If tracked: done_callback fires
   Result available via task.result()
   Exception available via task.exception()
```

### Exception Handling in Tasks

```python
async def animation_loop(zone_id, animation):
    try:
        while True:
            frame = await animation.step()
            await frame_manager.push_frame(frame)
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        # Normal cancellation - cleanup here
        log.info(f"Animation for {zone_id} cancelled")
        raise  # Must re-raise CancelledError!
    except Exception as e:
        # Unexpected error
        log.error(f"Animation error: {e}")
        # Task ends, done_callback fires
        # TaskRegistry detects failure
        raise  # Re-raise so task captures exception
    finally:
        # Always runs - perfect for cleanup
        log.info(f"Animation finished, rendered {frame_count} frames")
```

**Key Rules:**
1. ✅ Always re-raise `asyncio.CancelledError` (for proper shutdown)
2. ✅ Use `finally` for guaranteed cleanup
3. ✅ Let exceptions propagate (TaskRegistry captures them)
4. ❌ Never silently catch exceptions in critical tasks

---

## Key Concepts Explained

### 1. Async Lock (`asyncio.Lock`)

**Problem it solves:** Multiple tasks accessing shared data simultaneously

```python
# From frame_manager.py:117, 171-212
self._lock = asyncio.Lock()

async def push_frame(self, frame):
    async with self._lock:  # ← Acquire lock
        # Only one task can run this section at a time
        self.main_queues[priority].append(frame)
    # ← Release lock automatically
```

**What happens:**
```
Task A                          Task B
─────────────────────────────  ─────────────────────────────
async with self._lock:          async with self._lock:
  # Get lock                      # WAIT! Task A has it
  queue.append(frame)
                                  # Wait...
# Release lock                    # Wait...
                                  # Now I get lock!
                                  queue.append(frame)
                                  # Release
```

### 2. Async Sleep vs Busy Wait

```python
# ✅ GOOD: Yields to event loop every iteration
while True:
    result = await get_data()
    if result:
        process(result)
    await asyncio.sleep(0.001)  # ← Yields for 1ms

# ❌ BAD: Busy loop, wastes CPU
while True:
    result = await get_data()
    if result:
        process(result)
    await asyncio.sleep(0)  # ← Yields but doesn't sleep, busy loop!

# ❌ VERY BAD: Blocks event loop entirely
while True:
    result = await get_data()
    if result:
        process(result)
    # No sleep at all! Tight loop blocks other tasks
```

**In Diuna:**
```python
# From animations/engine.py:188-196
# CURRENT: Potentially busy loop
async def _run_loop(self, zone_id: ZoneID, animation: BaseAnimation):
    while True:
        frame = await animation.step()
        if frame is None:
            await asyncio.sleep(0)  # ⚠️ Busy loop!
            continue
        await self.frame_manager.push_frame(frame)
        await asyncio.sleep(0)  # ⚠️ Yields but no sleep
```

### 3. Context Managers for Resource Cleanup

```python
# ✅ GOOD: Guaranteed cleanup with async context manager
async with lock:
    # Do work with lock held
    queue.append(item)
# Lock automatically released, even if exception occurs

# ❌ BAD: May forget to release lock
lock_acquired = await lock.acquire()
try:
    queue.append(item)
finally:
    lock.release()  # Easy to forget!
```

### 4. Task Cancellation Pattern

```python
# From animations/engine.py:126-151
async def stop_for_zone(self, zone_id: ZoneID):
    task = None
    async with self._lock:
        task = self.tasks.pop(zone_id, None)

    if task:
        task.cancel()  # Request cancellation
        try:
            await task  # Wait for cleanup (receives CancelledError)
        except asyncio.CancelledError:
            pass  # Expected exception
```

**What happens:**
```
Before: task = asyncio.create_task(long_running_work())

task.cancel()                          # Request cancellation

long_running_work()                    # Receives CancelledError
  ↓                                    # at next await point
  await asyncio.sleep(1)               # ← EXCEPTION HERE!
  # CancelledError raised

exception propagates                   # Task becomes "cancelled"
  ↓
await task                             # Waits for task to finish cleanup
  ↓
CancelledError caught (or ignored)

Task is now cancelled and cleaned up
```

### 5. Why No Blocking Calls

**Blocking call (blocks event loop):**
```python
# ❌ WRONG
async def render_frame(self, frame):
    await self.push_frame(frame)
    # DON'T DO THIS:
    time.sleep(0.01)  # ← Blocks entire event loop!
    # All other tasks frozen for 10ms
```

**Correct pattern:**
```python
# ✅ CORRECT
async def render_frame(self, frame):
    await self.push_frame(frame)
    # DO THIS:
    await asyncio.sleep(0.01)  # ← Only pauses this task
    # Other tasks can run!
```

**In LED control:**
```python
# From frame_manager.py:295-299
# Enforce hardware timing
elapsed = time.perf_counter() - self.last_show_time
if elapsed < WS2811Timing.MIN_FRAME_TIME_MS / 1000:
    await asyncio.sleep(...)  # ✅ GOOD - doesn't block

# But then:
self._render_atomic(frame)  # ❌ CALLS strip.show() which blocks!
```

---

## Summary: How Diuna's Event Loop Works

1. **Single Event Loop Thread** manages all I/O and timing
2. **Multiple Concurrent Tasks** (render, input, API, animations) run cooperatively
3. **Tasks pause at `await` points** to let others run
4. **Tasks must be fast** between await points (ideally <1ms)
5. **Blocking calls** (like `strip.show()`) freeze everything
6. **Async locks** protect shared data (queues, state)
7. **TaskRegistry** monitors task health and enables graceful shutdown

**Key Principle:** Asyncio is like a **highly-efficient juggler** who catches and throws each ball (task) just long enough to move it forward, then catches the next ball. If any ball is heavy (blocking code), the juggling becomes clumsy and drops other balls.

For Diuna's LED control, **hardware operations must be lightweight** (yield frequently) or **offloaded to separate threads** (via `run_in_executor`). See [3_issues_and_fixes.md](3_issues_and_fixes.md) for how the current implementation falls short.

---

## Next Steps

- **Understand current issues:** Read [1_current_architecture.md](1_current_architecture.md) for detailed code analysis
- **Learn about patterns:** See [2_async_patterns.md](2_async_patterns.md) for good and bad examples from codebase
- **Fix critical issues:** Check [3_issues_and_fixes.md](3_issues_and_fixes.md) for specific solutions
- **Best practices:** Study [4_best_practices.md](4_best_practices.md) for professional async patterns
- **Performance:** Review [5_performance_analysis.md](5_performance_analysis.md) for impact analysis
