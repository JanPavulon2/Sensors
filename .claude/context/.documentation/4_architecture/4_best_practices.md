# Professional Async Patterns for Embedded Systems

**Last Updated:** 2026-01-02
**Audience:** Developers looking to write production-quality async code
**Focus:** Lessons from industry, applied to LED control systems

---

## Table of Contents
1. [Core Principles](#core-principles)
2. [Async/Sync Integration](#asyncsync-integration)
3. [Hardware Integration](#hardware-integration)
4. [Error Handling](#error-handling)
5. [Performance Patterns](#performance-patterns)
6. [Testing Async Code](#testing-async-code)
7. [Common Pitfalls](#common-pitfalls)

---

## Core Principles

### Principle 1: Never Block the Event Loop

**The Golden Rule of Asyncio:**

> Any time your async function takes more than ~1ms without `await`, you're harming responsiveness.

**Why 1ms?**
```
At 60 FPS (16.6ms per frame):
- 1ms blocking = 6% jank
- 2ms blocking = 12% jank
- 3ms blocking = 18% jank (noticeable)
- 5ms blocking = 30% jank (bad)
```

**Examples:**

```python
# ❌ BAD: CPU-bound work without yields
async def calculate_animation_frame(params):
    for i in range(1000000):  # Long loop without await
        result = expensive_calculation(i)
    return result

# ✅ GOOD: Yield every now and then
async def calculate_animation_frame(params):
    result = 0
    for i in range(1000000):
        result += expensive_calculation(i)

        if i % 1000 == 0:  # Yield every 1000 iterations
            await asyncio.sleep(0)

    return result

# ✅ BETTER: Use executor for CPU-bound work
async def calculate_animation_frame(params):
    loop = asyncio.get_running_loop()

    # Offload CPU-heavy work to thread
    result = await loop.run_in_executor(
        None,  # Use default executor
        expensive_calculation_blocking,
        params
    )

    return result

def expensive_calculation_blocking(params):
    """CPU-bound work - OK to block in executor."""
    result = 0
    for i in range(1000000):
        result += expensive_calculation(i)
    return result
```

### Principle 2: Structure Concurrency - TaskGroups

**Python 3.11+ Best Practice:**

```python
# ✅ MODERN: TaskGroup (Python 3.11+)
async def run_application():
    """All tasks grouped, clean error handling."""

    try:
        async with asyncio.TaskGroup() as tg:
            # All tasks run concurrently
            tg.create_task(render_loop())
            tg.create_task(input_handler())
            tg.create_task(api_server())
            # If ANY task raises exception, all are cancelled

    except ExceptionGroup as eg:
        # Handle multiple exceptions
        for exc in eg.exceptions:
            log.error(f"Task failed: {exc}")

    # ALL tasks guaranteed cancelled here

# ✅ COMPATIBLE: Manual task tracking (Python 3.9+)
async def run_application():
    """Traditional approach - works on Pi."""

    tasks = []

    try:
        # Create all tasks
        tasks.append(asyncio.create_task(render_loop()))
        tasks.append(asyncio.create_task(input_handler()))
        tasks.append(asyncio.create_task(api_server()))

        # Wait for all (will re-raise if any exception)
        await asyncio.gather(*tasks)

    except Exception as e:
        log.error(f"Application error: {e}")

    finally:
        # Cancel remaining tasks
        for task in tasks:
            if not task.done():
                task.cancel()

        # Wait for cancellation
        await asyncio.gather(*tasks, return_exceptions=True)
```

**Key Benefit:** Structured concurrency ensures:
- No orphaned tasks
- Clean error propagation
- Proper resource cleanup
- Cancellation guarantees

### Principle 3: Resource Management with Context Managers

**Rule: Async resources need async context managers**

```python
# ❌ BAD: Manual resource management
async def handle_hardware():
    lock = asyncio.Lock()
    try:
        await lock.acquire()  # Forgettable step
        # Do work
    finally:
        lock.release()  # Could forget!

# ✅ GOOD: Use async context manager
async def handle_hardware():
    async with lock:  # Guaranteed release
        # Do work
    # Lock automatically released

# ✅ GOOD: Implement custom context managers
class HardwareConnection:
    async def __aenter__(self):
        """Setup connection."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup connection."""
        await self.disconnect()

    async def setup(self):
        # Usage
        async with HardwareConnection() as hw:
            await hw.write_frame(frame)
        # Cleanup guaranteed even if exception
```

### Principle 4: Know Your Timeouts

**Every blocking operation needs a timeout**

```python
# ❌ BAD: Can wait forever
async def get_temperature():
    result = await temperature_sensor.read()  # No timeout!
    return result

# ✅ GOOD: Sensible timeout
async def get_temperature(timeout_sec=5.0):
    try:
        result = await asyncio.wait_for(
            temperature_sensor.read(),
            timeout=timeout_sec
        )
        return result
    except asyncio.TimeoutError:
        log.warning(f"Temperature sensor timeout after {timeout_sec}s")
        return DEFAULT_TEMP

# ✅ GOOD: Timeout appropriate to operation
async def render_frame(timeout_sec=0.016):  # 60 FPS = 16.6ms
    try:
        frame = await self._drain_frames()
        await asyncio.wait_for(
            self._apply_frame(frame),
            timeout=timeout_sec
        )
    except asyncio.TimeoutError:
        log.error("Frame rendering exceeded time budget")
        # Skip this frame, continue with next
```

---

## Async/Sync Integration

### Pattern: Async Boundary

**Key Insight:** You can't avoid sync code entirely. Design clear boundaries.

```python
# Concentric Architecture:
┌─────────────────────────────────────────────────┐
│              Async Applications                  │
│         (UI, API, Events, Coordination)         │
├─────────────────────────────────────────────────┤
│              Async/Sync Boundary                │
│  (Use run_in_executor for sync operations)     │
├─────────────────────────────────────────────────┤
│              Sync Libraries                     │
│        (NumPy, hardware drivers, etc)           │
└─────────────────────────────────────────────────┘
```

**Good Example: Hybrid Stack**

```python
# Layer 1: Async coordination
async def render_frame():
    # Async: Get frame data
    frame_data = await animation_engine.get_frame()

    # Async → Sync boundary
    loop = asyncio.get_running_loop()

    # Layer 2: Sync processing (in executor)
    result = await loop.run_in_executor(
        None,
        process_frame_blocking,  # Sync function
        frame_data
    )

    # Back to async: Submit to hardware
    await hardware.apply_frame(result)

# Layer 2: Sync processing (can block, no problem)
def process_frame_blocking(frame_data):
    """Sync function - OK to use blocking operations."""
    # Use NumPy, OpenCV, heavy computation
    pixels = numpy.array(frame_data.pixels)
    gamma_corrected = numpy.power(pixels / 255.0, 2.2) * 255
    return gamma_corrected.astype(numpy.uint8)

# Layer 3: Native libraries
# (numpy, hardware drivers, etc)
```

**Benefits:**
- ✅ Separates async/sync concerns
- ✅ No need to rewrite sync libraries
- ✅ Clear performance boundaries
- ✅ Easy to profile and optimize

---

## Hardware Integration

### Pattern 1: Hardware Abstractions

**Never couple application logic to hardware details**

```python
# ❌ BAD: Tight coupling
class LedController:
    async def render(self, frame):
        # Direct hardware access
        gpio.setPin(17, HIGH)
        time.sleep(0.001)
        dma_transfer(frame_buffer)

# ✅ GOOD: Hardware abstraction
from abc import ABC, abstractmethod

class PhysicalStrip(ABC):
    """Interface that hardware implementations must provide."""

    @abstractmethod
    async def apply_frame(self, pixels: List[Color]) -> None:
        """Apply pixel data to physical strip."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup hardware resources."""
        pass

class WS281xStrip(PhysicalStrip):
    """WS2811/WS2812 implementation."""

    async def apply_frame(self, pixels: List[Color]) -> None:
        loop = asyncio.get_running_loop()
        # Offload blocking DMA to executor
        await loop.run_in_executor(
            self._executor,
            self._apply_frame_blocking,
            pixels
        )

    def _apply_frame_blocking(self, pixels):
        """Hardware-specific blocking code."""
        for i, color in enumerate(pixels):
            self._pixel_strip.setPixelColorRGB(i, color.r, color.g, color.b)
        self._pixel_strip.show()  # DMA transfer (blocking)

class MockStrip(PhysicalStrip):
    """Mock implementation for testing."""

    async def apply_frame(self, pixels: List[Color]) -> None:
        # No actual hardware - just track
        self.last_frame = pixels

class LedController:
    """Application logic - independent of hardware."""

    def __init__(self, strip: PhysicalStrip):
        self.strip = strip  # Injected dependency

    async def render(self, frame):
        # Works with any PhysicalStrip implementation
        await self.strip.apply_frame(frame)
        self.frame_count += 1
```

**Why This Works:**
- ✅ Test with MockStrip (instant, no hardware)
- ✅ Easy to support multiple hardware types
- ✅ Clear dependencies
- ✅ Hardware details isolated

### Pattern 2: Error Recovery

**Hardware can fail, plan for it**

```python
# ❌ BAD: Failure stops application
async def render_loop():
    while True:
        frame = await get_frame()
        await hardware.apply_frame(frame)  # Crashes entire app

# ✅ GOOD: Handle hardware failures gracefully
async def render_loop():
    while True:
        try:
            frame = await get_frame()
            await hardware.apply_frame(frame)

        except HardwareError as e:
            log.error(f"Hardware error: {e}")

            # Try recovery
            try:
                await hardware.reinitialize()
                log.info("Hardware reinitialized")
            except Exception as e:
                log.error(f"Hardware recovery failed: {e}")
                # Continue trying, maybe system recovers later

        except Exception as e:
            log.error(f"Unexpected error: {e}", exc_info=True)
            # Continue running
```

### Pattern 3: Temperature Monitoring

**Raspberry Pi can overheat, especially with LEDs**

```python
# Monitor temperature
async def temperature_monitor():
    """Monitor and throttle if overheating."""

    while True:
        try:
            temp = await get_cpu_temperature()

            if temp > 80:  # Celsius
                log.warning(f"CPU hot: {temp}°C, throttling LEDs")
                await event_bus.publish(
                    ThermalThrottleEvent(temperature=temp)
                )

                # Reduce frame rate
                if self.fps > 30:
                    self.fps = 30

            elif temp < 70 and self.fps < 60:
                # Cool down enough, restore fps
                self.fps = 60

        except Exception as e:
            log.error(f"Temperature monitoring error: {e}")

        await asyncio.sleep(5.0)  # Check every 5 seconds
```

---

## Error Handling

### Pattern 1: Exception Hierarchies

**Organize exceptions for better handling**

```python
# ✅ GOOD: Hierarchical exceptions
class DiunaError(Exception):
    """Base exception for all Diuna errors."""
    pass

class HardwareError(DiunaError):
    """LED hardware communication failure."""
    pass

class GPIOError(HardwareError):
    """GPIO-specific error."""
    pass

class AnimationError(DiunaError):
    """Animation generation failure."""
    pass

class ConfigError(DiunaError):
    """Configuration validation failure."""
    pass

# Usage:
try:
    await hardware.apply_frame(frame)
except GPIOError as e:
    log.error(f"GPIO error (can recover): {e}")
    await hardware.reset()
except HardwareError as e:
    log.error(f"Hardware error (might recover): {e}")
except DiunaError as e:
    log.error(f"Diuna error (internal): {e}")
except Exception as e:
    log.error(f"Unexpected error: {e}", exc_info=True)
```

### Pattern 2: Context-Rich Logging

**Include context in error logs for easier debugging**

```python
# ❌ BAD: Minimal info
log.error(f"Error: {e}")

# ✅ GOOD: Rich context
log.error(
    "Frame rendering failed",
    extra={
        'zone_id': zone_id.name,
        'animation_type': animation.__class__.__name__,
        'frame_number': self.frame_count,
        'timestamp': time.time(),
    },
    exc_info=True
)

# ✅ GOOD: Structured logging (for aggregation)
logger.error(
    "frame_rendering_failed",
    zone_id=zone_id.name,
    animation=animation.__class__.__name__,
    frame_num=self.frame_count,
    exc_info=True
)
```

### Pattern 3: Fault Tolerant Event Dispatch

**One handler shouldn't stop others**

```python
# ✅ GOOD: Continue on handler failure (from event_bus.py)
async def publish(self, event: Event) -> None:
    handlers = self._handlers.get(event.type, [])

    for handler_entry in handlers:
        try:
            if asyncio.iscoroutinefunction(handler_entry.handler):
                await handler_entry.handler(event)
            else:
                handler_entry.handler(event)

        except Exception as e:
            log.error(
                f"Handler failed: {handler_entry.handler.__name__}",
                exc_info=True
            )
            # Continue to next handler (fault tolerance)
```

**Why:** If one event handler crashes, don't break event delivery for all others.

---

## Performance Patterns

### Pattern 1: Async Profiling

**Measure before optimizing**

```python
import asyncio
import time

class PerformanceMonitor:
    """Track async task performance."""

    def __init__(self):
        self.measurements = {}

    async def measure(self, name: str, coro):
        """Measure async operation duration."""
        start = time.perf_counter()
        result = await coro
        elapsed = time.perf_counter() - start

        if name not in self.measurements:
            self.measurements[name] = []

        self.measurements[name].append(elapsed * 1000)  # ms

        return result

    def report(self):
        """Print performance report."""
        for name, times in self.measurements.items():
            avg = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)

            print(f"{name}:")
            print(f"  Avg: {avg:.2f}ms, Max: {max_time:.2f}ms, Min: {min_time:.2f}ms")

# Usage:
monitor = PerformanceMonitor()

async def render_frame():
    await monitor.measure("frame_drain", self._drain_frames())
    await monitor.measure("frame_apply", self._apply_frame(frame))

# Later:
monitor.report()
```

### Pattern 2: Batch Operations

**Group work to reduce overhead**

```python
# ❌ BAD: One at a time
async def apply_zones(zones):
    for zone in zones:
        await zone.apply_frame(frame)  # N context switches

# ✅ GOOD: Batch with gather
async def apply_zones(zones):
    tasks = [zone.apply_frame(frame) for zone in zones]
    await asyncio.gather(*tasks)  # Parallel, fewer context switches
```

### Pattern 3: Priority Queuing

**Process high-priority work first**

```python
# From frame_manager.py - excellent example
class PriorityFrameQueue:
    """Frame queue with priority levels."""

    def __init__(self):
        # Higher priority first
        self.queues = {
            FramePriority.TRANSITION: deque(),  # Fade operations
            FramePriority.ANIMATION: deque(),   # Active animations
            FramePriority.STATIC: deque(),      # Static colors
        }

    async def get_next(self):
        """Get highest priority available frame."""
        for priority in FramePriority:
            if self.queues[priority]:
                return self.queues[priority].popleft()
        return None

    async def push(self, frame: Frame, priority: FramePriority):
        """Add frame at specified priority."""
        self.queues[priority].append(frame)

# Effect: Transitions always render immediately, animations wait if needed
```

---

## Testing Async Code

### Pattern 1: Using `pytest-asyncio`

```python
import pytest
import asyncio

# Fixture for async event loop
@pytest.fixture
async def event_loop():
    """Event loop for tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Test async function
@pytest.mark.asyncio
async def test_frame_submission():
    """Test that frames submit correctly."""
    frame_manager = FrameManager(fps=60)

    # Submit frame
    test_frame = MainStripFrame(
        zone_pixels={ZoneID.ZONE_0: [(255, 0, 0)] * 30},
        priority=FramePriority.ANIMATION
    )

    await frame_manager.push_frame(test_frame)

    # Verify queued
    frame = await frame_manager._drain_frames()
    assert frame.zone_pixels[ZoneID.ZONE_0][0] == (255, 0, 0)
```

### Pattern 2: Mocking Async Functions

```python
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_with_mocked_hardware():
    """Test with mocked hardware."""

    # Create mock strip
    mock_strip = AsyncMock(spec=PhysicalStrip)
    mock_strip.apply_frame = AsyncMock()

    # Test application
    controller = LedController(strip=mock_strip)
    frame = [Color(255, 0, 0)] * 30

    await controller.render(frame)

    # Verify hardware was called
    mock_strip.apply_frame.assert_called_once_with(frame)
```

### Pattern 3: Testing Concurrency

```python
@pytest.mark.asyncio
async def test_concurrent_frame_submissions():
    """Test that multiple concurrent submissions work."""

    frame_manager = FrameManager(fps=60)

    # Create many concurrent submissions
    async def submit_frame(zone_id, color):
        frame = SingleZoneFrame(
            zone_id=zone_id,
            pixels=[(color.r, color.g, color.b)] * 30
        )
        await frame_manager.push_frame(frame)

    # Run concurrently
    zones = [ZoneID.ZONE_0, ZoneID.ZONE_1, ZoneID.ZONE_2]
    colors = [Color(255, 0, 0), Color(0, 255, 0), Color(0, 0, 255)]

    await asyncio.gather(
        *[submit_frame(z, c) for z, c in zip(zones, colors)]
    )

    # Verify all submitted
    for _ in range(3):
        frame = await frame_manager._drain_frames()
        assert frame is not None
```

---

## Common Pitfalls

### Pitfall 1: Forgetting `await`

```python
# ❌ WRONG: Returns coroutine, doesn't execute
result = get_data()  # Forgot await!

# ✅ CORRECT:
result = await get_data()

# Common with callbacks:
# ❌ WRONG
task.add_done_callback(log_result)  # Never awaited
async def log_result(result):
    print(result)

# ✅ CORRECT
task.add_done_callback(lambda t: print(t.result()))
```

### Pitfall 2: Mixing Sync and Async Without Executor

```python
# ❌ WRONG: Blocks event loop
async def get_temperature():
    temp_file = open("/sys/class/thermal/thermal_zone0/temp")
    reading = temp_file.read()  # ← Blocks!
    temp_file.close()
    return int(reading) / 1000

# ✅ CORRECT: Use executor
async def get_temperature():
    loop = asyncio.get_running_loop()

    def read_temp_blocking():
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            reading = f.read()
        return int(reading) / 1000

    temp = await loop.run_in_executor(None, read_temp_blocking)
    return temp
```

### Pitfall 3: Not Handling `CancelledError`

```python
# ❌ WRONG: Swallows cancellation
async def worker():
    try:
        while True:
            await asyncio.sleep(1)
    except Exception:
        pass  # Catches CancelledError too!

# ✅ CORRECT: Let cancellation propagate
async def worker():
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        log.info("Worker cancelled")
        raise  # MUST re-raise!
    except Exception as e:
        log.error(f"Error: {e}")
```

### Pitfall 4: Creating Tasks Without Tracking

```python
# ❌ WRONG: No way to know if it crashed
asyncio.create_task(important_work())

# ✅ CORRECT: Track it
task = asyncio.create_task(important_work())
task.add_done_callback(lambda t: log_if_failed(t))

# OR: Use application task registry
task = create_tracked_task(
    important_work(),
    category=TaskCategory.IMPORTANT,
    description="Important background work"
)
```

### Pitfall 5: Timeout Too Short

```python
# ❌ WRONG: Times out under load
async def render():
    await asyncio.wait_for(
        hardware.apply_frame(frame),
        timeout=0.001  # 1ms - too short!
    )

# ✅ CORRECT: Realistic timeout
async def render():
    await asyncio.wait_for(
        hardware.apply_frame(frame),
        timeout=0.005  # 5ms - allows for contention
    )
```

---

## Summary: Professional Async Development

**Key Takeaways:**

1. **Never block the event loop** - Use `run_in_executor()` for blocking I/O
2. **Structure concurrency** - Use TaskGroups or manual task tracking
3. **Resource management** - Use async context managers
4. **Know your timeouts** - Every operation needs one
5. **Separate async/sync** - Clear boundaries with executor
6. **Abstract hardware** - Use interfaces, not direct hardware access
7. **Graceful degradation** - Handle failures, don't crash
8. **Profile and measure** - Data-driven optimization
9. **Test concurrency** - Concurrent tests catch race conditions
10. **Handle all exceptions** - Especially `CancelledError`

**Diuna Specific:**
- ✅ Good: Excellent task tracking and shutdown coordination
- ✅ Good: Good hardware abstraction with PhysicalStrip interface
- ⚠️ Needs: Fix blocking hardware calls with `run_in_executor()`
- ⚠️ Needs: Fix busy loops with proper sleep durations
- ✅ Good: Already uses async context managers for locks

---

## Next: Performance Analysis

Read [5_performance_analysis.md](5_performance_analysis.md) to understand the impact of issues and expected improvements from fixes.
