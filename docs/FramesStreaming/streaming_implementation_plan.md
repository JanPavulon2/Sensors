# Frame Streaming Implementation Plan

**Date:** 2026-01-31
**Status:** Pre-implementation
**Goal:** Real-time LED state streaming to frontend

---

## Current Status

### ✅ Completed (Post-Refactor)

1. **OutputFrame model** - Complete ([output_frame.py](../src/models/domain/output_frame.py))
   - `t: float` - global animation time
   - `zones: Dict[ZoneID, List[Color]]` - full pixel state

2. **FrameManager integration** - Fixed
   - `_build_output_frame(t)` - creates OutputFrame from zone_render_states
   - `_emit_output_frame(output_frame)` - placeholder (empty)
   - Called in `_render_frame()` after hardware render

3. **Frame flow** - Working
   - SingleZoneFrame/MultiZoneFrame/PixelFrame → MainStripFrame → render → OutputFrame

### ❌ Not Implemented Yet

1. Global AppClock
2. OutputFrame emission (Socket.IO)
3. Frame throttling (60 fps → 30 fps)
4. Frontend receiver
5. Recording/replay system

---

## Implementation Roadmap

### Phase 1: Global AppClock ⏰

**Goal:** Single source of truth for animation time

**Tasks:**
1. Create `AppClock` service ([src/services/app_clock.py](../src/services/app_clock.py))
   ```python
   class AppClock:
       """Global application clock for animation synchronization."""

       def __init__(self):
           self._start = time.monotonic()
           self._paused_at: Optional[float] = None
           self._total_paused_time = 0.0

       def now(self) -> float:
           """Current time in seconds since app start (excluding paused time)."""
           if self._paused_at is not None:
               return self._paused_at - self._start - self._total_paused_time
           return time.monotonic() - self._start - self._total_paused_time

       def pause(self):
           """Pause the clock."""
           if self._paused_at is None:
               self._paused_at = time.monotonic()

       def resume(self):
           """Resume the clock."""
           if self._paused_at is not None:
               self._total_paused_time += time.monotonic() - self._paused_at
               self._paused_at = None
   ```

2. Add AppClock to ServiceContainer
   ```python
   @dataclass
   class ServiceContainer:
       app_clock: AppClock  # NEW
       event_bus: EventBus
       frame_manager: FrameManager
       # ... rest
   ```

3. Pass AppClock to FrameManager
   ```python
   class FrameManager:
       def __init__(self, fps: int, app_clock: AppClock):
           self.app_clock = app_clock
           # ...

       def _render_frame(self, frame: MainStripFrame):
           # ...
           current_time = self.app_clock.now()  # ✅ Use global clock
           output_frame = self._build_output_frame(t=current_time)
           # ...
   ```

**Testing:**
- Verify `app_clock.now()` increments correctly
- Verify pause/resume works
- Verify OutputFrame.t matches app_clock

---

### Phase 2: OutputFrame Emitter Service 📡

**Goal:** Pluggable consumers for OutputFrame

**Tasks:**
1. Create `OutputFrameEmitter` ([src/services/output_frame_emitter.py](../src/services/output_frame_emitter.py))
   ```python
   from typing import Protocol, List

   class OutputFrameConsumer(Protocol):
       """Consumer interface for OutputFrame."""
       async def consume(self, frame: OutputFrame) -> None: ...

   class OutputFrameEmitter:
       """Emits OutputFrame to registered consumers."""

       def __init__(self, target_fps: int = 30):
           self.consumers: List[OutputFrameConsumer] = []
           self.target_fps = target_fps
           self.last_emit_time = 0.0
           self.frame_interval = 1.0 / target_fps

       def register(self, consumer: OutputFrameConsumer):
           """Register a consumer."""
           self.consumers.append(consumer)

       async def emit(self, frame: OutputFrame):
           """Emit frame to all consumers (with throttling)."""
           now = time.perf_counter()
           if now - self.last_emit_time < self.frame_interval:
               return  # Throttle

           for consumer in self.consumers:
               try:
                   await consumer.consume(frame)
               except Exception as e:
                   log.error(f"Consumer error: {e}")

           self.last_emit_time = now
   ```

2. Integrate with FrameManager
   ```python
   class FrameManager:
       def __init__(self, fps: int, app_clock: AppClock, output_emitter: OutputFrameEmitter):
           self.output_emitter = output_emitter
           # ...

       def _emit_output_frame(self, output_frame: OutputFrame):
           """Emit to registered consumers."""
           asyncio.create_task(self.output_emitter.emit(output_frame))
   ```

**Testing:**
- Register dummy consumer, verify `consume()` is called
- Verify throttling (60 fps render → 30 fps emit)
- Measure performance impact

---

### Phase 3: Socket.IO Streaming Consumer 🌐

**Goal:** Stream OutputFrame to frontend via Socket.IO

**Tasks:**
1. Create `SocketIOStreamingConsumer` ([src/api/socketio/streaming_consumer.py](../src/api/socketio/streaming_consumer.py))
   ```python
   class SocketIOStreamingConsumer:
       """Streams OutputFrame to Socket.IO clients."""

       def __init__(self, sio):
           self.sio = sio

       async def consume(self, frame: OutputFrame):
           """Serialize and emit OutputFrame."""
           payload = self._serialize(frame)
           await self.sio.emit("output_frame", payload)

       def _serialize(self, frame: OutputFrame) -> dict:
           """Convert OutputFrame to JSON-serializable dict."""
           return {
               "t": frame.t,
               "zones": {
                   zone_id.name: [c.to_rgb() for c in pixels]
                   for zone_id, pixels in frame.zones.items()
               }
           }
   ```

2. Register consumer in main.py
   ```python
   # Create Socket.IO streaming consumer
   streaming_consumer = SocketIOStreamingConsumer(sio)
   output_emitter.register(streaming_consumer)
   ```

3. Add Socket.IO event handler (client request)
   ```python
   @sio.on("request_streaming")
   async def handle_streaming_request(sid, data):
       """Client requests to start/stop streaming."""
       if data.get("enabled"):
           # Enable streaming for this client (future: per-client filtering)
           await sio.emit("streaming_started", {}, room=sid)
       else:
           await sio.emit("streaming_stopped", {}, room=sid)
   ```

**Testing:**
- Connect frontend, verify "output_frame" events received
- Verify payload structure
- Measure bandwidth (bytes/second)
- Test with multiple clients

---

### Phase 4: Frontend Receiver 🖥️

**Goal:** Visualize streamed LED state in frontend

**Tasks:**
1. Create Socket.IO listener ([frontend/src/features/streaming/useOutputFrame.ts](../frontend/src/features/streaming/useOutputFrame.ts))
   ```typescript
   interface OutputFrameData {
       t: number;
       zones: Record<string, [number, number, number][]>;
   }

   export function useOutputFrame() {
       const [frame, setFrame] = useState<OutputFrameData | null>(null);
       const [fps, setFps] = useState(0);

       useEffect(() => {
           const socket = getSocket();

           socket.on("output_frame", (data: OutputFrameData) => {
               setFrame(data);
               updateFps();
           });

           // Request streaming
           socket.emit("request_streaming", { enabled: true });

           return () => {
               socket.emit("request_streaming", { enabled: false });
               socket.off("output_frame");
           };
       }, []);

       return { frame, fps };
   }
   ```

2. Create virtual LED visualizer ([frontend/src/features/streaming/VirtualLEDs.tsx](../frontend/src/features/streaming/VirtualLEDs.tsx))
   ```typescript
   export function VirtualLEDs() {
       const { frame } = useOutputFrame();

       if (!frame) return <div>Waiting for stream...</div>;

       return (
           <div className="virtual-leds">
               {Object.entries(frame.zones).map(([zoneId, pixels]) => (
                   <ZoneVisualization
                       key={zoneId}
                       zoneId={zoneId}
                       pixels={pixels}
                   />
               ))}
           </div>
       );
   }
   ```

3. Add to Dashboard
   ```typescript
   <VirtualLEDs />
   ```

**Testing:**
- Verify real-time updates
- Measure latency (backend render → frontend display)
- Test performance with all zones

---

### Phase 5: Recording/Replay (Optional) 🎬

**Goal:** Record and replay LED sequences

**Tasks:**
1. Create `FrameRecordingConsumer` ([src/services/frame_recorder.py](../src/services/frame_recorder.py))
   ```python
   class FrameRecorder:
       """Records OutputFrame stream to buffer/file."""

       def __init__(self, max_frames: int = 18000):  # 10 minutes @ 30 fps
           self.buffer: Deque[OutputFrame] = deque(maxlen=max_frames)
           self.recording = False

       async def consume(self, frame: OutputFrame):
           """Record frame if recording is active."""
           if self.recording:
               self.buffer.append(frame)

       def start_recording(self):
           """Start recording."""
           self.recording = True
           self.buffer.clear()

       def stop_recording(self) -> List[OutputFrame]:
           """Stop recording and return frames."""
           self.recording = False
           return list(self.buffer)

       def save(self, filename: str):
           """Save recording to file."""
           frames = list(self.buffer)
           with open(filename, "wb") as f:
               pickle.dump(frames, f)
   ```

2. Create `FrameReplayer` ([src/services/frame_replayer.py](../src/services/frame_replayer.py))
   ```python
   class FrameReplayer:
       """Replays recorded OutputFrame sequences."""

       def __init__(self, frames: List[OutputFrame], frame_manager: FrameManager):
           self.frames = frames
           self.frame_manager = frame_manager
           self.index = 0
           self.playing = False

       async def play(self):
           """Play recorded sequence."""
           self.playing = True
           while self.playing and self.index < len(self.frames):
               frame = self.frames[self.index]

               # Convert OutputFrame → PixelFrame → render
               pixel_frame = PixelFrame(
                   priority=FramePriority.DEBUG,
                   source=FrameSource.DEBUG,
                   zone_pixels=frame.zones
               )
               await self.frame_manager.push_frame(pixel_frame)

               # Wait for next frame (based on t delta)
               if self.index + 1 < len(self.frames):
                   delta_t = self.frames[self.index + 1].t - frame.t
                   await asyncio.sleep(delta_t)

               self.index += 1

       def step_forward(self):
           """Advance one frame."""
           self.index = min(self.index + 1, len(self.frames) - 1)

       def step_backward(self):
           """Go back one frame."""
           self.index = max(self.index - 1, 0)
   ```

---

## Performance Considerations

### Bandwidth Estimation

**Scenario:** 5 zones, average 20 pixels each, 30 fps stream

```
Per frame:
- t: 8 bytes (float64)
- zones: 5 zones × 20 pixels × 3 bytes (RGB) = 300 bytes
- JSON overhead: ~100 bytes (keys, brackets, etc.)
Total: ~408 bytes/frame

Per second:
408 bytes × 30 fps = 12.24 KB/s

Per minute:
12.24 KB/s × 60 = 734 KB/min
```

**Optimizations:**
1. Binary format (MessagePack) - 50% reduction
2. Delta compression (send only changed pixels) - 80-90% reduction in static scenes
3. Zone filtering (stream only visible zones) - variable reduction

### CPU Impact

**Current render loop:** 60 fps
**Added overhead:**
- `_build_output_frame()` - O(zones × pixels) copy
- `_emit_output_frame()` - O(1) queue append
- Serialization (Socket.IO consumer) - O(zones × pixels) JSON encode

**Mitigation:**
- Throttle to 30 fps (50% reduction)
- Offload serialization to thread pool
- Use msgpack instead of JSON

---

## Testing Checklist

### Unit Tests
- [ ] AppClock pause/resume
- [ ] OutputFrameEmitter throttling
- [ ] Serialization correctness
- [ ] FrameRecorder buffer overflow

### Integration Tests
- [ ] End-to-end frame flow (animation → render → emit → frontend)
- [ ] Socket.IO reconnection handling
- [ ] Multiple clients simultaneously
- [ ] Recording + replay accuracy

### Performance Tests
- [ ] Measure FPS impact (target: <5% degradation)
- [ ] Measure bandwidth (target: <20 KB/s)
- [ ] Measure latency (target: <100ms backend → frontend)

---

## Rollout Plan

### Stage 1: Backend Foundation (Week 1)
1. Implement AppClock
2. Implement OutputFrameEmitter
3. Add unit tests
4. Integrate with FrameManager

### Stage 2: Socket.IO Streaming (Week 2)
1. Implement SocketIOStreamingConsumer
2. Test with Socket.IO test client
3. Measure bandwidth/performance
4. Optimize if needed

### Stage 3: Frontend Visualization (Week 3)
1. Implement useOutputFrame hook
2. Build VirtualLEDs component
3. Add to Dashboard
4. Test latency/performance

### Stage 4: Recording/Replay (Week 4 - Optional)
1. Implement FrameRecorder
2. Implement FrameReplayer
3. Add API endpoints (start/stop recording, load/play)
4. Add frontend controls

---

## Open Questions

1. **Serialization format:**
   - JSON (human-readable, large)
   - MessagePack (binary, smaller)
   - Custom binary (smallest, complex)
   → **Decision:** Start with JSON, optimize to MessagePack later

2. **Per-client filtering:**
   - Send all zones to all clients?
   - Let clients subscribe to specific zones?
   → **Decision:** All zones initially, add filtering later

3. **Delta compression:**
   - Send full frame every time?
   - Send deltas (only changed pixels)?
   → **Decision:** Full frames initially, add deltas in Phase 2

4. **Recording format:**
   - In-memory only?
   - Save to disk automatically?
   - On-demand export?
   → **Decision:** In-memory buffer, on-demand export

---

## Success Criteria

✅ Frontend displays real-time LED state synchronized with physical LEDs
✅ Latency < 100ms from render to frontend display
✅ FPS impact < 5% (maintain 60 fps render)
✅ Bandwidth < 20 KB/s per client
✅ No crashes or memory leaks during 1-hour streaming session

---

**Last Updated:** 2026-01-31
**Status:** Planning complete, ready for Phase 1 implementation
