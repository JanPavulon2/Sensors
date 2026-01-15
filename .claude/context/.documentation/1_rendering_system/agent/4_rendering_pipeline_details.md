---
Last Updated: 2025-11-25
Type: Agent Documentation
Purpose: Rendering pipeline data flow with code snippets
---

# Rendering Pipeline Details

## Complete Frame Journey

```
Animation yields color
  ↓
AnimationEngine._run_loop() consumes yield
  ↓
Convert to ZoneFrame object
  ↓
frame_manager.submit_zone_frame(frame)
  ↓
FrameManager stores in _zone_frame_queue
  ↓
[Next render cycle @ 60 FPS]
  ↓
FrameManager._render() called
  ↓
_select_frame() picks highest priority non-expired frame
  ↓
_render_zone_frame() converts to pixel array
  ↓
ZoneStrip.show_full_pixel_frame(pixels)
  ↓
WS281xStrip.apply_frame(dma_buffer)  [software operation]
  ↓
WS281xStrip.show()  [hardware DMA transfer]
  ↓
LEDs update on physical strip
```

## FrameManager.submit_zone_frame()

**Location**: `src/engine/frame_manager.py:150`

```python
async def submit_zone_frame(self, frame: ZoneFrame) -> None:
    """Submit zone-based frame for rendering."""
    frame.timestamp = asyncio.get_event_loop().time()
    self._zone_frame_queue.put(frame)  # Priority queue
```

**Frame Object**:
```python
@dataclass
class ZoneFrame:
    zones: Dict[ZoneID, Color]  # Zone ID → Color
    priority: int = ANIMATION   # Priority level
    ttl: float = 0.1            # 100ms time-to-live
    timestamp: float = 0.0      # Creation time (auto-set)
```

## FrameManager._render()

**Location**: `src/engine/frame_manager.py:200`

**Executes every 16.67ms (60 FPS)**:

```python
async def _render(self) -> None:
    """Main render loop."""
    while True:
        # 1. Select highest priority frames
        zone_frame = self._select_zone_frame()
        pixel_frame = self._select_pixel_frame()
        preview_frame = self._select_preview_frame()

        # 2. Render zone frame to pixels
        if zone_frame:
            await self._render_zone_frame(zone_frame)

        # 3. Render pixel frame (overrides zones)
        if pixel_frame:
            await self._render_pixel_frame(pixel_frame)

        # 4. Update preview panel
        if preview_frame:
            await self._render_preview_frame(preview_frame)

        # 5. Hardware update (single DMA per cycle)
        for strip in self._strips:
            strip.show()  # Called once per cycle

        # 6. Next cycle in 16.67ms
        await asyncio.sleep(1/60)
```

## Frame Selection

**Location**: `src/engine/frame_manager.py:250`

```python
def _select_zone_frame(self) -> Optional[ZoneFrame]:
    """Select highest priority non-expired zone frame."""
    current_time = asyncio.get_event_loop().time()
    highest_frame = None
    highest_priority = -1

    # Scan all frames
    for frame in self._zone_frame_queue.all_items():  # Get all, don't remove
        # Check TTL
        frame_age = current_time - frame.timestamp
        if frame_age > frame.ttl:
            continue  # Skip expired

        # Track highest priority
        if frame.priority > highest_priority:
            highest_priority = frame.priority
            highest_frame = frame

    return highest_frame
```

## Zone Frame Rendering

**Location**: `src/engine/frame_manager.py:350`

```python
async def _render_zone_frame(self, frame: ZoneFrame) -> None:
    """Convert ZoneFrame to pixel array."""
    # Get all registered strips
    for strip in self._strips:
        # For each zone in frame
        for zone_id, color in frame.zones.items():
            # Get zone from zone service
            zone = self._zone_service.get_by_id(zone_id)

            # Apply zone brightness
            r, g, b = color.to_rgb_with_brightness(zone.brightness)

            # Get pixel indices for this zone
            pixel_indices = strip.get_zone_pixel_indices(zone_id)

            # Set all pixels in zone to this color
            for pixel_idx in pixel_indices:
                strip.pixels[pixel_idx] = (r, g, b)
```

## Hardware Update

**Location**: `src/zone_layer/led_channel.py:120`

```python
async def show_full_pixel_frame(self, pixels: List[Tuple[int, int, int]]) -> None:
    """Render pixel array to hardware."""
    # Convert each color to hardware bytes
    hw_pixels = []
    for r, g, b in pixels:
        # Remap color order if needed (BGR vs GRB)
        if self.hardware.color_order == ColorOrder.BGR:
            hw_pixels.append([b, g, r])  # BGR order
        else:
            hw_pixels.append([r, g, b])  # RGB/GRB order

    # Load into DMA buffer (software operation)
    self.hardware.apply_frame(hw_pixels)

    # Send to hardware (DMA transfer)
    self.hardware.show()
```

## DMA Transfer

**Location**: `src/hardware/led/ws281x_strip.py:180`

```python
def show(self) -> None:
    """Send DMA buffer to hardware."""
    # Hardware-specific: rpi_ws281x library
    self._strip.begin()       # Start DMA
    self._strip.show()        # Transfer buffer
    self._strip.end()         # End DMA (waits for complete)
```

## Priority Queue Operations

**Submitting a frame** (priority queue):
```python
frame = ZoneFrame(zones={FLOOR: red_color}, priority=ANIMATION)
await frame_manager.submit_zone_frame(frame)
# → Stored in _zone_frame_queue
```

**Selecting highest priority**:
```python
highest = None
for frame in all_frames:
    if not expired(frame):
        if frame.priority > (highest.priority if highest else -1):
            highest = frame
return highest
```

**TTL Expiration**:
```python
frame_age = current_time - frame.timestamp
if frame_age > frame.ttl:
    # Frame too old, discard
    pass
else:
    # Frame still valid
    consider_for_selection(frame)
```

## Animation Frame Generation

**Location**: `src/animations/engine.py:250`

```python
async def _run_loop(self):
    """Consume animation yields and submit frames."""
    while self.animation_running:
        try:
            # Get next yield from animation generator
            frame_data = await self.animation_gen.asend(None)

            # Convert yield to frame object
            if isinstance(frame_data, tuple) and len(frame_data) == 2:
                # Zone-based: (zone_id, Color)
                zone_id, color = frame_data
                frame = ZoneFrame(
                    zones={zone_id: color},
                    priority=ANIMATION
                )
            elif isinstance(frame_data, tuple) and len(frame_data) == 3:
                # Pixel-based: (zone_id, pixel_idx, Color)
                zone_id, pixel_idx, color = frame_data
                frame = PixelFrame(
                    pixels={(zone_id, pixel_idx): color},
                    priority=ANIMATION
                )

            # Submit to FrameManager
            await self.frame_manager.submit_zone_frame(frame)

            # Wait for next frame
            await self.frame_manager.wait_render_cycle()

        except StopAsyncIteration:
            self.animation_running = False
```

## Static Mode Frame Submission

**Location**: `src/controllers/led_controller/static_mode_controller.py:80`

```python
async def render_zone(self, zone_id: ZoneID, color: Color, brightness: float):
    """Render static zone color."""
    # Get current colors for all zones
    zone_colors = {}
    for zone in self.zone_service.get_all():
        if zone.config.id == zone_id:
            zone_colors[zone_id] = color
        else:
            zone_colors[zone.config.id] = zone.state.color

    # Create frame
    frame = ZoneFrame(zones=zone_colors, priority=MANUAL)

    # Submit to FrameManager
    await self.led_channel_controller.submit_all_zones_frame(zone_colors)
```

## Transition Frame Sequence

**Location**: `src/services/transition_service.py:180`

```python
async def crossfade(self, from_frame: ZoneFrame, to_frame: ZoneFrame, duration_ms: int = 500):
    """Smooth crossfade between frames."""
    start_time = asyncio.get_event_loop().time()

    while True:
        elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        if elapsed_ms >= duration_ms:
            # Fade complete
            break

        # Compute fade progress (0.0 to 1.0)
        progress = elapsed_ms / duration_ms

        # Interpolate each zone
        interpolated_colors = {}
        for zone_id in from_frame.zones:
            from_color = from_frame.zones[zone_id]
            to_color = to_frame.zones[zone_id]

            # Linear RGB interpolation
            t = progress
            r = int(from_color.red * (1-t) + to_color.red * t)
            g = int(from_color.green * (1-t) + to_color.green * t)
            b = int(from_color.blue * (1-t) + to_color.blue * t)

            interpolated_colors[zone_id] = Color(r, g, b)

        # Submit interpolated frame
        frame = ZoneFrame(zones=interpolated_colors, priority=TRANSITION)
        await self.frame_manager.submit_zone_frame(frame)

        # Wait for next frame
        await asyncio.sleep(1/60)
```

## Error Handling

**Frame submission**:
```python
try:
    await frame_manager.submit_zone_frame(frame)
except Exception as e:
    logger.error(f"Frame submission failed: {e}")
    # Continue with next frame
```

**Animation crash**:
```python
# If animation generator crashes:
# 1. _run_loop() catches exception
# 2. Stops consuming yields
# 3. Animation frames stop being submitted
# 4. Existing frames remain (with TTL)
# 5. After TTL expires, frame removed
# 6. System displays next highest priority frame
```

## Performance Metrics

**Render cycle time**:
- Target: 16.67ms (60 FPS)
- Frame selection: ~0.5ms
- Zone→pixel conversion: ~1ms
- Hardware DMA: ~2.75ms
- Total: ~4.25ms (plenty of headroom)

**Memory usage**:
- Frame queues: ~50KB max (depends on backlog)
- DMA buffers: ~500 bytes total
- Animation generators: ~5-10KB per active animation

---

**Next**: [Implementation Patterns](5_implementation_patterns.md)
