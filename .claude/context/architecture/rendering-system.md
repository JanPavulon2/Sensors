---
Last Updated: 2025-11-15
Updated By: Human
Changes: Updated with unified rendering architecture, type-safe refactoring, and FramePlaybackController implementation details
---

# Lighting & Rendering System Architecture

## 1. System Overview

The Diuna LED system is a **centralized frame-based rendering architecture** that manages real-time visualization of colors, animations, and transitions across two physical LED strips.

### 1.1 Core Components

**Physical Hardware**:
- **Main Strip**: 90 addressable pixels (WS2811, 12V) organized into 6-8 logical zones
- **Preview Panel**: 8 RGB pixels (WS2812B, 5V) for parameter visualization

**Software Layers**:
1. **Hardware Abstraction** (ZoneStrip, PreviewPanel) - Direct GPIO control
2. **Frame Management** (FrameManager) - Centralized rendering with priority queues
3. **Animation System** (AnimationEngine, BaseAnimation) - Async generators yielding frames
4. **Transition Service** - Smooth LED state transitions
5. **Controllers** (LEDController, AnimationModeController, StaticModeController) - Business logic

### 1.2 Rendering Flow

```
┌──────────────────────────────────────────────────────────┐
│                  FRAME SOURCES                           │
├──────────────┬──────────────┬───────────────┬────────────┤
│ AnimationEngine │ Transitions │  Static Pulse │  Manual  │
│   (async gen)   │  (Service)  │   (Controller)│ (Service)│
└──────┬──────────┴──────┬──────┴────────┬──────┴────┬─────┘
       │                 │               │           │
       └─────────────────┼───────────────┼───────────┘
                         ▼
         ┌─────────────────────────────┐
         │   FrameManager              │
         │ - Priority Queue            │
         │ - Frame Selection           │
         │ - Atomic Rendering          │
         └──────────┬──────────────────┘
                    │
         ┌──────────▼──────────────┐
         │  Hardware Drivers       │
         │ - ZoneStrip.show()      │
         │ - PreviewPanel().show() │
         └─────────────────────────┘
```

---

## 2. Hardware Layer (Layer 0)

### 2.1 ZoneStrip - Main LED Strip Control

**Location**: `src/components/zone_strip.py`

**Responsibilities**:
- Abstraction for 90-pixel WS2811 strip
- Zone-to-pixel mapping (logical zones → physical indices)
- Per-pixel and per-zone color setting
- Single `show()` call per frame cycle

**Zone Configuration** (from config):
```
FLOOR:  0-11   (12 pixels)
LAMP:   12-30  (19 pixels)
TOP:    31-34  (4 pixels)
RIGHT:  35-37  (3 pixels)
BOTTOM: 38-41  (4 pixels)
LEFT:   42-44  (3 pixels)
BACK:   45-89  (45 pixels, optional second strip)
```

**Key Methods**:
```python
set_zone_color(zone_id: str, r, g, b, show=True)      # Uniform zone color
set_pixel_color(zone_id: str, idx, r, g, b, show=True) # Individual pixel
get_frame() -> List[(r, g, b)]                         # Capture current state
show()                                                  # DMA transfer to strip
```

**Critical Constraint**: Only ONE `show()` can execute at a time (DMA channel).
- Each `show()` takes ~2.7ms (90 pixels × 24 bits @ 800kHz)
- Minimum 50µs reset time between frames (WS2811 protocol)

### 2.2 PreviewPanel - 8-LED Feedback Panel

**Location**: `src/components/preview_panel.py`

**Responsibilities**:
- 8-pixel WS2812B strip (GPIO 19, separate DMA channel)
- UI feedback (animation previews, parameter visualization)
- Upside-down orientation (physical mounting)

**Key Methods**:
```python
show_frame(frame: List[(r, g, b)])  # Display 8-pixel animation frame
show_bar(value, max_value, color)   # Show N pixels lit (progress bar)
show_color(r, g, b)                 # Fill all 8 pixels with color
```

**Synchronization**: Must stay synchronized with main strip frames via FrameManager.

---

## 3. Frame System (Layer 1)

### 3.1 Frame Models - Atomic Update Units

**Location**: `src/models/frame.py`

**Design Principle**: Each frame represents a complete renderable state for one display cycle.

#### BaseFrame (All frames inherit)
```python
@dataclass
class BaseFrame:
    priority: FramePriority        # Priority level (0-50)
    source: FrameSource            # Source identifier (ANIMATION, TRANSITION, etc.)
    timestamp: float               # Creation time
    ttl: float = 0.1               # Time-to-live (auto-expiration)

    def is_expired() -> bool       # Check if stale
```

#### ZoneFrame - Per-Zone Colors
```python
@dataclass
class ZoneFrame(BaseFrame):
    zone_colors: Dict[ZoneID, (r, g, b)]

# Usage: BreatheAnimation (zones breathe with individual colors)
# Yield format: (zone_id, r, g, b) - converted to ZoneFrame by FrameManager
```

#### PixelFrame - Per-Pixel Colors
```python
@dataclass
class PixelFrame(BaseFrame):
    zone_pixels: Dict[ZoneID, List[(r, g, b)]]

# Usage: SnakeAnimation (pixel-level control)
# Yield format: (zone_id, pixel_idx, r, g, b) - converted by FrameManager
```

#### FullStripFrame - Uniform Color
```python
@dataclass
class FullStripFrame(BaseFrame):
    color: (r, g, b)

# Usage: ColorCycleAnimation (entire strip one color)
# Yield format: (r, g, b) - converted by FrameManager
```

#### PreviewFrame - Panel Visualization
```python
@dataclass
class PreviewFrame(BaseFrame):
    pixels: List[(r, g, b)]  # Always exactly 8 pixels

# Synchronized with main strip rendering
```

### 3.2 Priority System

**Priority Levels** (higher = more important):
```
IDLE (0)       - No rendering (black)
MANUAL (10)    - Direct zone color sets (user control)
PULSE (20)     - Edit mode zone pulsing
ANIMATION (30) - Running animations
TRANSITION (40)- Smooth transitions (absolute highest)
DEBUG (50)     - Debug overlays / diagnostics
```

**Selection Logic**:
- Each cycle, FrameManager selects **highest-priority non-expired frame**
- When high-priority source stops → automatically falls back to lower priority
- Prevents conflicts (e.g., transition always wins vs animation)

### 3.3 TTL (Time-To-Live) System

**Purpose**: Prevent stale frames from being re-rendered.

**Mechanism**:
- Every frame has `ttl` (default 100ms)
- Frames expire 100ms after creation
- Expired frames removed from queue
- Prevents "ghost pixels" from old animations

**Example**: Animation yields 60 frames/sec (16.6ms intervals)
- Frame N expires at timestamp + 100ms
- By frame N+6, old frame is gone
- FrameManager falls back to next priority level

---

## 4. FrameManager - Centralized Rendering (Layer 2)

### 4.1 Architecture

**Location**: `src/engine/frame_manager.py`

**Core Responsibilities**:
- Collect frames from multiple sources (animations, transitions, static, etc.)
- Maintain separate priority queues for main strip and preview panel
- Select highest-priority non-expired frame each cycle
- Render selected frames atomically to both strips
- Support pause/step/FPS control for debugging
- Manage frame lifecycle (TTL expiration, priority conflicts)

**Key Data Structures**:
```python
class FrameManager:
    main_queues: Dict[FramePriority, Deque[MainStripFrame]]  # Per-priority queue
    preview_queues: Dict[FramePriority, Deque[PreviewFrame]]

    # Selected frames (rendered last cycle)
    _selected_main_frame: Optional[MainStripFrame]
    _selected_preview_frame: Optional[PreviewFrame]

    # Render state
    _fps: int = 60                 # Target render frequency
    _paused: bool = False          # Pause rendering
    _step_pending: bool = False    # Single-frame advance (debug)
```

### 4.2 Render Cycle (60 Hz default)

```
1. Fetch new frames from queues
   - Dequeue all pending frames (accumulated since last cycle)

2. Expire old frames
   - Remove frames where (now - timestamp) > ttl

3. Select frames (main strip + preview separately)
   - For main strip:
     - For priority in [DEBUG, TRANSITION, ANIMATION, PULSE, MANUAL]:
       - Find highest-priority non-expired frame
       - If found, use it; break
   - For preview panel (same priority selection)

4. Render atomically
   - Composite selected frame onto hardware state
   - Call ZoneStrip.show() (DMA transfer ~2.7ms)
   - Call PreviewPanel.show() (separate DMA channel)

5. Sleep until next cycle
   - await asyncio.sleep(1.0 / fps)
   - Total cycle time ≥ 2.7ms (hardware constraint)
```

### 4.3 Frame Submission API

**For Animation Sources**:
```python
frame_manager.submit_zone_frame(zone_colors: Dict[ZoneID, (r,g,b)],
                                priority=ANIMATION,
                                source=ANIMATION)

frame_manager.submit_pixel_frame(zone_pixels: Dict[ZoneID, List[(r,g,b)]],
                                 priority=ANIMATION,
                                 source=ANIMATION)
```

**For Transition Sources**:
```python
frame_manager.submit_full_strip_frame(color: (r, g, b),
                                      priority=TRANSITION,
                                      source=TRANSITION,
                                      ttl=0.05)  # Short TTL for smooth fades
```

**For Static/Manual Control**:
```python
frame_manager.submit_zone_frame(zone_colors,
                                priority=MANUAL,
                                source=STATIC)
```

### 4.4 Frame Rendering Logic

**Zone-Based Rendering** (for zone colors):
```python
if selected_frame is ZoneFrame:
    # Apply zone colors to strip
    for zone_id, (r, g, b) in selected_frame.zone_colors.items():
        strip.set_zone_color(zone_id, r, g, b, show=False)
    strip.show()
```

**Pixel-Based Rendering** (for pixel animations):
```python
if selected_frame is PixelFrame:
    # Apply per-pixel colors
    for zone_id, pixels in selected_frame.zone_pixels.items():
        for i, (r, g, b) in enumerate(pixels):
            strip.set_pixel_color(zone_id, i, r, g, b, show=False)
    strip.show()
```

**Full Strip Rendering** (uniform color):
```python
if selected_frame is FullStripFrame:
    # Apply color to all zones
    for zone in all_zones:
        strip.set_zone_color(zone.id, *selected_frame.color, show=False)
    strip.show()
```

---

## 5. Animation System (Layer 3)

### 5.1 AnimationEngine - Lifecycle Manager

**Location**: `src/animations/engine.py`

**Responsibilities**:
- Manage animation lifecycle (start, stop, pause, resume)
- Switch between animations with smooth transitions
- Distribute parameter updates to running animation
- Consume animation frames and submit to FrameManager
- Manage preview panel animations

**Core API**:
```python
class AnimationEngine:
    async def start(animation_id, excluded_zones, transition_config, **params)
    async def stop(skip_fade=False)
    async def update_param(param_id, value)  # Live parameter changes
    async def pause()
    async def resume()
```

**Startup Sequence** (smooth fade-in):
```python
async def start(anim_id, excluded_zones, transition):
    # 1. Wait for any active transition to complete
    await self.transition_service.wait_for_idle()

    # 2. Create animation instance
    animation = self.ANIMATIONS[anim_id](self.zones, **params)

    # 3. Get first frame (capture initial state)
    first_frame = await animation._get_first_frame()

    # 4. Smooth transition from current → new (via TransitionService)
    old_frame = self.strip.get_frame()
    await self.transition_service.crossfade(old_frame, first_frame, transition)

    # 5. Start animation loop
    self.animation_task = asyncio.create_task(self._run_loop())
```

**Runtime Loop**:
```python
async def _run_loop():
    async for frame_data in current_animation.run():
        # Frame data can be:
        # - (zone_id, r, g, b)           - zone-based
        # - (zone_id, pixel_idx, r, g, b) - pixel-based
        # - (r, g, b)                     - full strip

        # Convert to frame object
        frame = self._convert_to_frame(frame_data)

        # Submit to FrameManager (high priority)
        self.frame_manager.submit_frame(
            frame,
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION
        )

        # Yield control
        await asyncio.sleep(0)
```

### 5.2 BaseAnimation - Generator Interface

**Location**: `src/animations/base.py`

**Design**: Async generators that yield frame data tuples.

**Contract**:
```python
class BaseAnimation:
    async def run(self) -> AsyncIterator[FrameTuple]:
        """
        Main animation loop - yields frame data.

        Yields:
        - Zone-based: (zone_id, r, g, b) - uniform zone color
        - Pixel-based: (zone_id, pixel_idx, r, g, b) - individual pixel
        - Full strip: (r, g, b) - all zones same color
        """
        raise NotImplementedError()

    def update_param(param: str, value):
        """Update parameter live (called by AnimationEngine)"""
        setattr(self, param, value)

    def stop():
        """Stop animation"""
        self.running = False
```

**Parameter Update Mechanism**:
- Live updates: Parameter changed by user (encoder rotation)
- AnimationEngine calls `animation.update_param(param, value)`
- Animation reads parameter **inside loop** on each frame
- Next frame uses new value → smooth parameter changes

### 5.3 Animation Types

#### Per-Zone Animations
```python
# BreatheAnimation - zones breathe with individual colors
class BreatheAnimation(BaseAnimation):
    async def run(self):
        while self.running:
            for zone_id in active_zones:
                brightness = calculate_breathing_brightness()
                r, g, b = apply_brightness_to_color(brightness)
                yield (zone_id, r, g, b)
            await asyncio.sleep(frame_delay)
```

**Used for**: All zones display same effect with zone-specific colors.

#### Per-Pixel Animations
```python
# SnakeAnimation - single/multi-pixel snake travels through zones
class SnakeAnimation(BaseAnimation):
    async def run(self):
        while self.running:
            for i in range(snake_length):
                pos = (current_position - i) % total_pixels
                zone_id, pixel_idx = map_to_zone_pixel(pos)
                brightness = 1.0 - (i * 0.2)
                r, g, b = apply_brightness_to_color(brightness)
                yield (zone_id, pixel_idx, r, g, b)
            current_position += 1
            await asyncio.sleep(move_delay)
```

**Used for**: Fine-grained pixel control (effects that move/change at pixel level).

#### Full-Strip Animations
```python
# ColorCycleAnimation - entire strip cycles through hue spectrum
class ColorCycleAnimation(BaseAnimation):
    async def run(self):
        hue = 0
        while self.running:
            r, g, b = hue_to_rgb(hue)
            yield (r, g, b)  # Full strip same color
            hue = (hue + 1) % 360
            await asyncio.sleep(frame_delay)
```

**Used for**: Entire strip uniform color effect.

---

## 6. Transition Service (Layer 3)

### 6.1 Architecture

**Location**: `src/services/transition_service.py`

**Purpose**: Smooth LED state transitions across entire system.

**Uses**: FrameManager with TRANSITION priority (40) to guarantee smooth crossfades.

**Key Methods**:
```python
async def crossfade(from_frame, to_frame, config):
    """Smooth interpolation between two LED states"""

async def fade_out(duration_ms=600):
    """Fade to black"""

async def fade_in(to_frame, duration_ms=2000):
    """Fade from black to target state"""

async def wait_for_idle():
    """Wait until all transitions complete"""
```

### 6.2 Crossfade Algorithm

```python
async def crossfade(from_frame, to_frame, config: TransitionConfig):
    async with self._transition_lock:  # Prevent concurrent transitions
        for step in range(config.steps + 1):
            progress = step / config.steps              # 0.0 → 1.0
            factor = config.ease_function(progress)    # Easing curve

            # Interpolate all pixels
            interpolated = []
            for (r1,g1,b1), (r2,g2,b2) in zip(from_frame, to_frame):
                r = int(r1 + (r2 - r1) * factor)
                g = int(g1 + (g2 - g1) * factor)
                b = int(b1 + (b2 - b1) * factor)
                interpolated.append((r, g, b))

            # Submit as high-priority frame
            self.frame_manager.submit_full_strip_frame(
                interpolated,
                priority=TRANSITION,
                ttl=step_delay * 1.5  # Short TTL
            )

            # Respect WS2811 timing (2.75ms minimum)
            await asyncio.sleep(max(step_delay, 0.00275))
```

**Presets**:
```python
STARTUP = TransitionConfig(duration_ms=2000, steps=30)    # Slow fade-in
SHUTDOWN = TransitionConfig(duration_ms=600, steps=15)    # Quick fade-out
MODE_SWITCH = TransitionConfig(duration_ms=400, steps=15) # Medium fade
ANIMATION_SWITCH = TransitionConfig(duration_ms=400, steps=15)
```

---

## 7. Controllers - Business Logic (Layer 4)

### 7.1 LEDController - Main Orchestrator

**Location**: `src/controllers/led_controller/led_controller.py`

**Responsibilities**:
- Route mode changes (STATIC ↔ ANIMATION)
- Coordinate StaticModeController and AnimationModeController
- Handle power toggles
- Manage state persistence

**State Machine**:
```
STARTUP
  ↓
POWERED_OFF
  ↓
STATIC ↔ ANIMATION (user toggles)
  ↓
POWERED_OFF
  ↓
SHUTDOWN
```

### 7.2 AnimationModeController - Animation Control

**Location**: `src/controllers/led_controller/animation_mode_controller.py`

**Responsibilities**:
- Start/stop animations
- Handle parameter adjustments (speed, hue, length, etc.)
- Update preview panel (animation preview or parameter bar)
- Route encoder input to AnimationEngine

**Key Methods**:
```python
async def handle_animation_switch(new_animation_id):
    """Stop current animation, start new one with transition"""

async def adjust_parameter(param_id, delta):
    """Update animation parameter (speed, color, etc.)"""

async def handle_encoder_turn(direction, magnitude):
    """Selector or modulator turned"""
```

### 7.3 StaticModeController - Manual Color Control (Refactored Phase 6)

**Location**: `src/controllers/led_controller/static_mode_controller.py`

**Responsibilities**:
- Select current zone
- Adjust zone color, brightness
- Implement pulsing effect (selected zone @ 1 Hz)
- Update preview panel with zone colors
- **UNIFIED**: All rendering through FrameManager.submit_zones()

**Key Refactoring** (Phase 6 - Unified Rendering):

Before (dual paths):
```python
# OLD: Direct hardware rendering
self.strip_controller.render_zone(zone_id, color, brightness)
```

After (unified path):
```python
# NEW: All rendering through FrameManager
zone_colors = {zone_id: (zone.state.color, zone.brightness)}
self.strip_controller.submit_zones(zone_colors)
```

**Benefits**: Single source of truth, instant response (MANUAL priority = 10), no conflicting rendering paths.

**Pulsing Implementation** (still uses unified path):
```python
async def _pulse_task():
    """Pulse selected zone @ 1 Hz (edit indicator)"""
    while self.pulse_active:
        current_zone = self._get_current_zone()
        base = current_zone.brightness

        for step in range(steps):
            # Calculate sine wave brightness (0.2 to 1.0)
            scale = 0.2 + 0.8 * (math.sin(step / steps * 2 * math.pi - math.pi/2) + 1) / 2
            pulse_brightness = int(base * scale)

            # Submit through unified path
            self.strip_controller.submit_zones({
                current_zone.id: (current_zone.state.color, pulse_brightness)
            })

            await asyncio.sleep(cycle / steps)
```

---

## 8. Color Management

### 8.1 Color Spaces

**Supported Spaces**:
- **RGB**: Direct (r, g, b) tuples
- **HSV**: Hue (0-360), Saturation (0-100), Value (0-100)
- **HSL**: Hue (0-360), Saturation (0-100), Lightness (0-100)

### 8.2 Color Conversion

**Location**: `src/utils/colors.py`

```python
def hue_to_rgb(hue: int) -> Tuple[int, int, int]:
    """Convert hue (0-360) to RGB with full saturation/value"""

def hsv_to_rgb(h, s, v) -> Tuple[int, int, int]:
    """Convert HSV to RGB"""

def rgb_to_hsv(r, g, b) -> Tuple[int, int, int]:
    """Convert RGB to HSV"""

def apply_brightness(r, g, b, brightness: float) -> Tuple[int, int, int]:
    """Modulate color brightness (0.0 = black, 1.0 = full)"""
```

### 8.3 Gamma Correction

**Purpose**: Account for non-linear human brightness perception.

**Future**: Consider implementing linear brightness scaling for better animation smoothness.

---

## 9. Data Flow Examples

### 9.1 User Changes Zone Color (STATIC mode)

```
1. User turns modulator encoder
   ↓
2. ControlPanel detects rotation
   ↓
3. EventBus publishes EncoderRotateEvent
   ↓
4. StaticModeController receives event
   ↓
5. ZoneService.adjust_brightness(zone_id, delta)
   ↓
6. StaticModeController submits frame:
   frame_manager.submit_zone_frame(
       {zone_id: (r, g, b)},
       priority=MANUAL,
       source=STATIC
   )
   ↓
7. FrameManager (next cycle):
   - Selects MANUAL frame (no TRANSITION/ANIMATION running)
   - Renders to ZoneStrip: strip.set_zone_color(zone_id, r, g, b, show=false)
   - Calls strip.show() (DMA transfer)
   ↓
8. Preview Panel updated with all zone colors
```

### 9.2 Animation Starts (ANIMATION mode)

```
1. User selects animation + presses button
   ↓
2. EventBus publishes AnimationSwitchEvent
   ↓
3. AnimationModeController.handle_animation_switch(animation_id)
   ↓
4. AnimationEngine.start(animation_id, transition=ANIMATION_SWITCH):
   a) Wait for idle (any prior transition completes)
   b) Capture current strip state: old_frame = strip.get_frame()
   c) Create animation instance
   d) Get first animation frame: first_frame = animation._get_first_frame()
   e) TransitionService.crossfade(old_frame, first_frame, config):
      - For each transition step (30 steps over 400ms):
        * Interpolate frame
        * Submit to FrameManager with TRANSITION priority (40)
        * FrameManager renders (overrides any ANIMATION from old animation)
        * Sleep 13.3ms (400ms / 30 steps)
   f) Start animation loop: _run_loop()
   ↓
5. AnimationEngine._run_loop():
   While animation.running:
   a) Async for frame_data in animation.run():
      * Convert to Frame object (ZoneFrame, PixelFrame, etc.)
      * Submit to FrameManager:
        frame_manager.submit_zone_frame(
            frame_data,
            priority=ANIMATION,
            source=ANIMATION
        )
      * await asyncio.sleep(0)  # Yield control

   b) FrameManager (each 16.6ms cycle @ 60 FPS):
      * Dequeue pending ANIMATION frames
      * Select highest-priority non-expired
      * Render to strip
      * Preview panel shows animation preview (if available)
```

### 9.3 Parameter Update (Live)

```
1. User rotates modulator during animation
   ↓
2. EventBus publishes EncoderRotateEvent
   ↓
3. AnimationModeController.adjust_parameter(ANIM_SPEED, delta)
   ↓
4. AnimationEngine.update_param('speed', new_value):
   animation.speed = new_value
   ↓
5. Animation's _run_loop() next iteration reads self.speed
   ↓
6. Next frame uses new speed value
   → Smooth parameter change (no animation restart)
```

---

## 10. Key Architectural Principles

### 10.1 Separation of Concerns

| Layer | Responsibility | Examples |
|-------|-----------------|----------|
| **Hardware (0)** | GPIO control, DMA transfer | ZoneStrip, PreviewPanel |
| **Frame (1)** | Atomic render units, priority | ZoneFrame, PixelFrame, FrameManager |
| **Animation (3)** | Frame generation, lifecycle | AnimationEngine, BaseAnimation |
| **Controller (4)** | Business logic, routing | StaticModeController, AnimationModeController |
| **Service (4)** | Cross-cutting concerns | TransitionService, ZoneService |

### 10.2 Async/Await Patterns

**Rule 1: No blocking calls in animation loops**
- All I/O: wrapped in `run_in_executor()`
- All delays: use `await asyncio.sleep()`
- All waits: use `asyncio.Event`, `asyncio.Lock`, etc.

**Rule 2: Frame submission is non-blocking**
- `frame_manager.submit_*()` returns immediately
- FrameManager renders asynchronously
- Animation loop yields control: `await asyncio.sleep(0)`

**Rule 3: Transitions are atomic**
- `_transition_lock` prevents concurrent transitions
- Entire crossfade completes before animation starts
- No flickering from overlapping transitions

### 10.3 Priority-Based Rendering

**Key Insight**: High-priority frames override low-priority ones.

```
Animation running + Pulsing enabled:
  - TRANSITION (if switching): shows transition (40 > 30)
  - ANIMATION: shows animation (30 > 20)
  - PULSE: never renders (overridden by animation)

Static mode + Pulsing enabled:
  - MANUAL: shows manual zone (10 > 20) - WAIT, this is wrong!

Actually:
  - PULSE (20) > MANUAL (10)
  - So pulsing zone shows pulse, other zones show manual

This is elegant: pulsing naturally overlays on manual colors.
```

### 10.4 TTL-Based Lifecycle

**Benefits**:
- Prevents "ghost pixels" from old animations
- Automatic fallback to lower priority when source stops
- No explicit cleanup needed

**Example**: When animation stops
```
1. Animation loop exits
2. No more ANIMATION frames submitted
3. FrameManager's next cycle:
   - Previous ANIMATION frames are expired (100ms old)
   - Falls back to PULSE or MANUAL
   - Preview panel shows zone colors (STATIC) or parameter bar
4. Clean transition without explicit "clear" call
```

---

## 11. Hardware Constraints & Performance

### 11.1 WS2811 Protocol Requirements

| Constraint | Value | Impact |
|-----------|-------|--------|
| Data Rate | 800 kHz | 1.25µs per bit |
| Bits per Pixel | 24 (RGB) | 30µs per pixel |
| Pixels | 90 | 2,700µs DMA transfer |
| Reset Time | 50µs min | 50µs between frames |
| **Minimum Frame Time** | **2.75ms** | Max 363 FPS theoretical |

### 11.2 Python/Asyncio Constraints

| Factor | Typical Value | Effect |
|--------|---------------|--------|
| GC Pause | 10-50ms | Occasional frame stutter |
| Task Scheduling Jitter | ±5-10ms | Non-deterministic timing |
| Target FPS | 60 | 16.6ms per cycle |
| Practical Max FPS | 100-150 | Safe margin with overhead |

**Why 60 FPS?**
- Hardware minimum: 2.75ms (363 FPS possible)
- Python overhead: ~3ms per frame
- Practical limit: 100-150 FPS
- Human perception: 60 FPS imperceptible flicker
- **Target leaves 40% headroom** for system tasks

### 11.3 Memory Constraints

**Current Footprint** (~500 KB):
- 90 pixels × 3 bytes × 10 buffers = 27 KB frame buffers
- Animation instances: ~50 KB (per active animation)
- FrameManager queues: ~50 KB
- Other state: ~300 KB

**Raspberry Pi 4**: 4GB RAM (plenty of headroom)

---

## 12. Future Extensions

### 12.1 Advanced Frame Rendering

- [ ] **Frame Diffing**: Only update changed pixels (save DMA bandwidth)
- [ ] **Double Buffering**: Pre-compute next frame while rendering current
- [ ] **Adaptive FPS**: Reduce FPS during low-activity periods (power save)

### 12.2 New Animation Types

- [ ] **Matrix Rain**: Pixel-based vertical scrolling
- [ ] **Wave Effects**: Sine wave traveling through zones
- [ ] **Gradient Transitions**: Smooth color gradients across zones
- [ ] **Music Reactive**: LED patterns synchronized to audio

### 12.3 Interactive Features

- [ ] **Game Mode**: Interactive snake game (snake responds to input)
- [ ] **WebSocket Streaming**: Live animation viewer
- [ ] **Animation Recording**: Capture and replay animations
- [ ] **Custom Animation Upload**: User-defined animation files

### 12.4 Debugging & Monitoring

- [ ] **Frame Playback**: Step through animation frame-by-frame (✅ started)
- [ ] **FPS Counter**: Real-time render performance metrics
- [ ] **Memory Profiler**: Track buffer usage and allocations
- [ ] **Hardware Timing**: Measure actual DMA transfer times

---

## 12.5 Frame-By-Frame Debugging (NEW - Phase 5-6)

**Location**: `src/controllers/led_controller/frame_playback_controller.py`

**Purpose**: Step through animation frames one at a time for debugging.

**Features**:
- Offline frame preloading (async generator → list)
- Frame navigation with wrapping (next/previous)
- Play/pause toggle with separate background loop
- Keyboard input via EventBus (A/D/SPACE/Q)
- Frame format conversion (3/4/5-tuple → Frame objects)
- Detailed logging (RGB/hex, frame index, animation info)

**Integration**:
- Subscribes to KEYBOARD_KEYPRESS events
- Uses FrameManager.pause() during stepping
- Submits frames with DEBUG priority (50)

**Usage**:
```python
# Enter frame-by-frame mode
await controller.enter_frame_by_frame_mode(AnimationID.SNAKE, ANIM_SPEED=50)
# Keyboard controls active:
# - A: previous frame
# - D: next frame
# - SPACE: play/pause
# - Q: exit
```

---

## 13. Known Issues & Future Fixes

### Current (Unfixed)

1. **Animation Startup Flicker**
   - Brief flicker before animation stabilizes
   - Likely inherent to transition system
   - Status: Acceptable for current use

2. **Preview Panel Sync**
   - Not all animations have synchronized preview
   - Some previews lag behind main animation
   - Fix: Implement `run_preview()` for all animation types

### Addressed in Phase 5

✅ Eliminated parallel rendering (no more race conditions)
✅ Centralized FrameManager (single source of truth)
✅ Atomic rendering (single `show()` per cycle)
✅ Priority system prevents conflicts

---

## 14. Testing & Validation

### 14.1 Unit Tests Needed

- [ ] Frame priority selection logic
- [ ] TTL expiration
- [ ] Crossfade interpolation
- [ ] Animation parameter updates
- [ ] Zone-to-pixel mapping

### 14.2 Integration Tests Needed

- [ ] Animation switching (no ghost pixels)
- [ ] Mode switching (STATIC ↔ ANIMATION)
- [ ] Power on/off transitions
- [ ] Concurrent parameter updates
- [ ] Preview panel synchronization

### 14.3 Hardware Tests Needed

- [ ] 60 FPS sustained rendering
- [ ] DMA transfer timing validation
- [ ] WS2811 reset pulse compliance
- [ ] Thermal stability (65W sustained)

---

## Conclusion

The Diuna LED rendering system is a sophisticated, multi-layered architecture that prioritizes:

1. **Reliability**: Priority-based rendering prevents conflicts
2. **Performance**: Centralized FrameManager eliminates race conditions
3. **Extensibility**: Async generator pattern supports new animation types
4. **Maintainability**: Clear separation of concerns across layers
5. **Correctness**: Hardware timing constraints respected

The system is production-ready for current use cases and has strong foundations for future enhancements (game mode, WebSocket streaming, recording/playback).

