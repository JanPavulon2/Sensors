Doskonale! Plan został zaktualizowany z poprawną analizą problemu (starvation zamiast deadlock) i znacznie prostszym rozwiązaniem. Teraz mogę zakończyć planowanie.

---

## Sonnet's Corrected Analysis: Lock Starvation (Not Deadlock)

Now I need to verify the user's claim about asyncio.Lock behavior. Let me check the Python asyncio documentation and analyze the actual code behavior.

## Critical Analysis: User's Correction is CORRECT

After reading the code and considering asyncio.Lock semantics, I must **admit I was WRONG** in my previous analysis. Here's the honest truth:

### 1. User is RIGHT: `asyncio.Lock` DOES release on CancelledError

The user is absolutely correct. In Python's asyncio:

```python
async with self._lock:
    # ... code ...
```

**ALWAYS** calls `__aexit__()` when exiting the context manager, even when `CancelledError` is raised. This is fundamental to Python's context manager protocol - it's designed to be exception-safe.

**My mistake**: I incorrectly assumed that cancellation would prevent lock release, treating it like a C mutex or threading.Lock. This is wrong - asyncio.Lock is designed to be cancellation-safe.

### 2. The REAL Problem: Starvation / Head-of-Line Blocking

The user's alternative hypothesis is much more accurate. The actual problem is:

**Breathe Animation Loop** (engine.py:197-229):
```python
async def _run_loop(self, zone_id: ZoneID, animation: BaseAnimation):
    while True:
        frame = await animation.step()  # Fast for Breathe
        if frame is not None:
            await self.frame_manager.push_frame(frame)  # Line 226 - acquires lock
        await asyncio.sleep(1 / self.frame_manager.fps)  # 16.67ms @ 60 FPS
```

**FrameManager Render Loop** (frame_manager.py:297-348):
```python
async def _render_loop(self) -> None:
    while self.running:
        # ... timing checks ...
        frame = await self._drain_frames()  # Line 319 - needs lock
        # ... render ...
```

**FrameManager._drain_frames** (frame_manager.py:352-428):
```python
async def _drain_frames(self) -> Optional[MainStripFrame]:
    async with self._lock:  # Line 363 - competes for lock
        # Drain ALL queues, merge frames
        # This is a LONG operation
```

### 3. The Starvation Mechanism

What actually happens:

1. **Breathe loop runs fast**: step() is nearly instant, yields frame immediately
2. **push_frame() acquires lock**: Briefly holds lock to append to queue (fast operation)
3. **Breathe releases lock**: Lock is available again
4. **Breathe sleeps 16ms**: But immediately wakes up and tries to acquire lock again
5. **Render loop tries to drain**: Needs lock to drain ALL queues (slower operation)
6. **Scheduling unfairness**: Breathe loop gets lock repeatedly before render loop gets its turn

**Result**: Render loop is STARVED of lock access because:
- Breathe acquires/releases lock very quickly (just append to deque)
- Render needs longer lock hold time (drain all queues, merge frames)
- Python asyncio has NO fairness guarantee for lock acquisition
- High-frequency producer (animation) wins over low-frequency consumer (render)

### 4. Why My Proposed Fixes Were Wrong

**Fix 1 (try/finally)**: Unnecessary - lock already releases properly
**Fix 2 (timeout)**: Would detect timeout but not solve starvation

### 5. Actual Solutions for Starvation

Here are proper solutions:

**Option A: Remove lock from push_frame (queue.append is atomic for deque)**
```python
# In push_frame - NO LOCK NEEDED
# deque.append() is thread-safe and atomic
self.main_queues[msf.priority.value].append(msf)
```

**Option B: Batch frame submission**
```python
# Animation collects multiple frames before pushing
frames_batch = []
while len(frames_batch) < 5:
    frame = await animation.step()
    frames_batch.append(frame)

async with self._lock:
    for frame in frames_batch:
        self.main_queues[...].append(frame)
```

**Option C: Priority/fairness in lock acquisition**
```python
# Use asyncio.Queue instead of deque + lock
self.main_queues[priority] = asyncio.Queue(maxlen=10)

# push_frame becomes:
await self.main_queues[priority].put(frame)  # Built-in fairness
```

**Option D: Rate limit animation submission**
```python
# In _run_loop, limit submission rate
last_submit = 0
async def _run_loop(...):
    while True:
        frame = await animation.step()
        now = time.monotonic()
        if now - last_submit >= 0.05:  # Max 20 submissions/sec
            await self.frame_manager.push_frame(frame)
            last_submit = now
```

## My Recommendation

**Best solution: Option A + Option D**

1. **Remove lock from push_frame entirely** - deque.append is atomic
2. **Keep lock ONLY in _drain_frames** - protects iteration over queues
3. **Rate-limit animation submissions** - prevent queue flooding

This eliminates lock contention entirely while maintaining thread safety.

---

## Intellectual Honesty

I was WRONG about:
- The nature of asyncio.Lock behavior with cancellation
- The root cause being "deadlock" rather than starvation
- The necessity of try/finally for lock release

The user's engineering insight was correct. This is a classic **producer-consumer starvation problem** with unfair lock scheduling, NOT a deadlock caused by improper lock release.

**File References**:
- `d:\DEV\Projects\LED\Diuna\src\engine\frame_manager.py` (lines 166-217: push_frame, lines 352-428: _drain_frames)
- `d:\DEV\Projects\LED\Diuna\src\animations\engine.py` (lines 197-249: _run_loop)
