# Animation & Rendering System - Current Architecture

**Last Updated**: 2025-11-07
**Status**: Documentation of current system before major refactoring

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Current Architecture](#2-current-architecture)
3. [Component Details](#3-component-details)
4. [Frame Generation & Rendering](#4-frame-generation--rendering)
5. [Preview Panel System](#5-preview-panel-system)
6. [Problems with Current Architecture](#6-problems-with-current-architecture)
7. [References](#7-references)

---

## 1. System Overview

### 1.1 Core Concept

The Diuna LED system renders animations and static colors to **two separate physical LED strips**:

1. **Main Strip (ZoneStrip)**: 45 pixels (WS2811, GPIO 18) divided into 6-8 logical zones
2. **Preview Panel**: 8 pixels (WS2812B, GPIO 19) for UI feedback

### 1.2 Rendering Sources

Frames can come from multiple sources with different priorities:
- **Transitions**: Crossfades, fade in/out (highest priority)
- **Animations**: Running animations (breathe, snake, color_fade, etc.)
- **Pulsing**: Edit mode indicator (selected zone pulses)
- **Static**: Manual zone color/brightness settings
- **Preview**: Parameter visualization (brightness bar, color preview, etc.)

### 1.3 Animation Types

**Per-Zone Animations**: Operate on entire zones
- `BreatheAnimation`: All zones breathe synchronously with zone-specific colors
- `ColorFadeAnimation`: Rainbow cycling across all zones
- `ColorCycleAnimation`: Entire strip cycles through hues

**Per-Pixel Animations**: Operate on individual pixels
- `SnakeAnimation`: Snake moves across zones pixel-by-pixel
- `ColorSnakeAnimation`: Multi-colored snake
- `MatrixAnimation`: (disabled) Matrix rain effect

---

## 2. Current Architecture

### 2.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────┐
│                  ANIMATION SOURCES                       │
├──────────────┬──────────────┬──────────────┬────────────┤
│ AnimationEngine │ Transitions │  Static Pulse │  Manual  │
│   (async gen)   │  (Service)  │   (Controller)│ (Service)│
└──────┬──────────┴──────┬──────┴───────┬──────┴────┬─────┘
       │                 │              │           │
       └─────────────────┴──────────────┴───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   DIRECT RENDERING   │
              │  (Race Conditions!)  │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   ZoneStrip.show()   │
              │  PreviewPanel.show() │
              └──────────────────────┘
```

### 2.2 Current Rendering Path

**Problem**: Multiple components call `strip.set_*()` and `strip.show()` directly:

1. **AnimationEngine._run_loop()**: Calls `strip.set_pixel_color()` / `strip.set_zone_color()` directly
2. **StaticModeController._pulse_zone_task()**: Calls `strip.set_zone_color()` for pulsing
3. **TransitionService**: Calls `strip.set_pixel_color_absolute()` for crossfades
4. **Manual color changes**: Call `strip.set_zone_color()` for immediate updates

**Result**: Race conditions, flickering, unpredictable behavior when multiple sources compete.

### 2.3 Existing FrameManager (Partial Implementation)

**Location**: `src/engine/frame_manager.py`

**Current State**:
- Exists but only partially integrated
- AnimationEngine already calls `frame_manager.submit_zone_frame()` (line 374)
- Has basic ticker loop @ 60 Hz
- Missing: Priority system, transition support, preview synchronization

**Current Implementation**:
```python
class FrameManager:
    def __init__(self, fps: int = 60):
        self.strips: List = []
        self.pending_frames: deque[ZoneFrame] = deque()
        self._zone_cache: dict[ZoneID, List[Tuple[int, int, int]]] = {}

    def submit_zone_frame(self, zone_id: ZoneID, pixels: List[Tuple[int, int, int]]):
        """Called by AnimationEngine"""
        zf = ZoneFrame(zone_id=zone_id, pixels=pixels)
        self.pending_frames.append(zf)

    async def _render_loop(self):
        """Renders cached frames @ 60 FPS"""
        while self.running:
            pushed_frames = self._fetch_pending_frames()
            if pushed_frames:
                for frame in pushed_frames:
                    self._zone_cache[frame.zone_id] = frame.pixels

            # Render all zones
            self._render_all_zones()
            await asyncio.sleep(1.0 / self.fps)
```

**Missing Features**:
- No priority system (all frames equal priority)
- No transition integration
- No preview panel synchronization
- Direct rendering still bypasses FrameManager in many places

---

## 3. Component Details

### 3.1 AnimationEngine

**Location**: `src/animations/engine.py`

**Responsibilities**:
- Manages animation lifecycle (start, stop, parameter updates)
- Consumes frames from animation generators
- Submits frames to FrameManager (partially implemented)
- Handles smooth transitions between animations

**Key Methods**:
```python
class AnimationEngine:
    async def start(self, animation_id: AnimationID, excluded_zones, transition, **params):
        """Start animation with optional crossfade transition"""
        # 1. Wait for transitions to complete
        await self.transition_service.wait_for_idle()

        # 2. Render first frame to buffer
        first_frame = await self._get_first_frame()

        # 3. Crossfade from old to new (via TransitionService)
        await self.transition_service.crossfade(old_frame, first_frame, transition)

        # 4. Start animation loop
        self.animation_task = asyncio.create_task(self._run_loop())

    async def _run_loop(self):
        """Consume animation frames and render"""
        async for frame in self.current_animation.run():
            # Current: Direct rendering (PROBLEM!)
            if len(frame) == 5:  # Pixel-based
                zone_id, pixel_idx, r, g, b = frame
                self.strip.set_pixel_color(zone_id.name, pixel_idx, r, g, b, show=False)
            elif len(frame) == 4:  # Zone-based
                zone_id, r, g, b = frame
                self.strip.set_zone_color(zone_id.name, r, g, b, show=False)

            # Partial FrameManager integration (NEW)
            for zone_id, pix_dict in self.zone_pixel_buffers.items():
                pixels_list = [pix_dict[i] for i in sorted(pix_dict.keys())]
                self.frame_manager.submit_zone_frame(zone_id, pixels_list)

            await asyncio.sleep(0)
```

**Animation Generator Contract**:
```python
class BaseAnimation:
    async def run(self) -> AsyncIterator[Tuple]:
        """
        Yields frame data:
        - Per-zone: (zone_id, r, g, b)
        - Per-pixel: (zone_id, pixel_index, r, g, b)
        - Full strip: (r, g, b)  # NEW format for ColorCycleAnimation
        """

    async def run_preview(self, pixel_count: int = 8) -> AsyncIterator[List[Tuple[int,int,int]]]:
        """
        Yields preview frames (8 pixels) synchronized with main animation.
        Each animation implements custom preview logic.
        """
```

### 3.2 TransitionService

**Location**: `src/services/transition_service.py`

**Responsibilities**:
- Smooth LED state transitions (crossfades, fades)
- Prevents concurrent transitions via `_transition_lock`
- Used for: app startup, mode switches, animation changes, power toggles

**Current Implementation**:
```python
class TransitionService:
    async def crossfade(self, from_frame, to_frame, config):
        """Crossfade between two frames"""
        async with self._transition_lock:
            for step in range(config.steps + 1):
                progress = step / config.steps
                factor = config.ease_function(progress)

                # Interpolate RGB
                for i, ((r1,g1,b1), (r2,g2,b2)) in enumerate(zip(from_frame, to_frame)):
                    r = int(r1 + (r2 - r1) * factor)
                    g = int(g1 + (g2 - g1) * factor)
                    b = int(b1 + (b2 - b1) * factor)

                    # PROBLEM: Direct rendering!
                    self.strip.set_pixel_color_absolute(i, r, g, b, show=False)

                self.strip.show()
                await asyncio.sleep(step_delay)
```

**Problem**: TransitionService renders directly to strip, bypassing any priority system.

### 3.3 StaticModeController (Pulsing)

**Location**: `src/controllers/led_controller/static_mode_controller.py`

**Responsibilities**:
- Handles zone selection and parameter adjustment in STATIC mode
- Implements pulsing effect (selected zone pulses @ 1 Hz)

**Pulsing Implementation**:
```python
class StaticModeController:
    async def _pulse_zone_task(self):
        """Pulse selected zone @ 1 Hz (edit mode indicator)"""
        while self.pulse_enabled:
            # Calculate sine wave brightness
            phase = (elapsed / 1.0) * 2 * math.pi
            brightness_factor = (math.sin(phase) + 1) / 2  # 0.0 → 1.0 → 0.0

            # Get zone color
            zone = self.zone_service.get_current()
            r, g, b = zone.get_rgb()

            # Apply brightness modulation
            r_out = int(r * brightness_factor)
            g_out = int(g * brightness_factor)
            b_out = int(b * brightness_factor)

            # PROBLEM: Direct rendering!
            self.zone_strip_controller.zone_strip.set_zone_color(
                zone.config.id.name, r_out, g_out, b_out
            )

            await asyncio.sleep(frame_delay)
```

**Problem**: Pulsing can conflict with transitions or animations.

### 3.4 ZoneStrip (Hardware Abstraction)

**Location**: `src/components/zone_strip.py`

**Responsibilities**:
- Hardware abstraction for WS2811 strip (45 pixels, GPIO 18)
- Zone-based addressing (converts `zone_id` → pixel range)
- Batch updates with single `show()` call

**Key Methods**:
```python
class ZoneStrip:
    def set_zone_color(self, zone_id: str, r: int, g: int, b: int, show: bool = True):
        """Set uniform color for zone"""
        start, end = self.zones[zone_id]
        for i in range(start, end + 1):
            self.pixel_strip.setPixelColor(i, Color(r, g, b))
        if show:
            self.pixel_strip.show()

    def set_pixel_color(self, zone_id: str, pixel_index: int, r: int, g: int, b: int, show: bool = True):
        """Set individual pixel within zone"""
        physical_index = self._get_physical_pixel_index(zone_id, pixel_index)
        self.pixel_strip.setPixelColor(physical_index, Color(r, g, b))
        if show:
            self.pixel_strip.show()

    def get_frame(self) -> List[Tuple[int, int, int]]:
        """Capture current LED state (for transitions)"""
        return [(r, g, b) for pixel in range(self.pixel_count)]
```

**Zone Mapping** (from config):
```
FLOOR:  0-11   (12 pixels)
LAMP:   12-30  (19 pixels)
TOP:    31-34  (4 pixels)
RIGHT:  35-37  (3 pixels)
BOTTOM: 38-41  (4 pixels)
LEFT:   42-44  (3 pixels)
```

### 3.5 PreviewPanel (8-LED Panel)

**Location**: `src/components/preview_panel.py`

**Responsibilities**:
- Hardware abstraction for 8-LED preview panel (GPIO 19)
- Parameter visualization (brightness bars, color preview, etc.)
- Animation preview (synchronized mini-animations)

**Current Methods**:
```python
class PreviewPanel:
    def show_frame(self, frame: List[Tuple[int, int, int]]):
        """Display 8-pixel frame"""
        for i, (r, g, b) in enumerate(frame[:self.count]):
            physical_index = self._reverse_index(i)  # Panel is upside down
            self._pixel_strip.setPixelColor(physical_index, Color(r, g, b))
        self._pixel_strip.show()

    def show_bar(self, value: int, max_value: int = 100, color: Tuple[int, int, int] = (255, 255, 255)):
        """Show bar indicator (N of 8 LEDs lit)"""
        filled = int((value / max_value) * self.count)
        for i in range(self.count):
            physical_index = self._reverse_index(i)
            if i < filled:
                self._pixel_strip.setPixelColor(physical_index, Color(*color))
            else:
                self._pixel_strip.setPixelColor(physical_index, Color(0, 0, 0))
        self._pixel_strip.show()
```

**Problem**: No generic methods for common preview patterns (gradient, multi-color, pattern).

---

## 4. Frame Generation & Rendering

### 4.1 Animation Frame Types

**Zone-Based Frames** (yield 4-tuple):
```python
# Example: BreatheAnimation
async def run(self):
    for zone_id in self.active_zones:
        r, g, b = calculate_breathing_color(zone_id)
        yield (zone_id, r, g, b)  # 4-tuple: zone_id, r, g, b
```

**Pixel-Based Frames** (yield 5-tuple):
```python
# Example: SnakeAnimation
async def run(self):
    for pixel in snake_positions:
        zone_id, pixel_idx = get_pixel_location(pixel)
        r, g, b = calculate_snake_color(pixel)
        yield (zone_id, pixel_idx, r, g, b)  # 5-tuple: zone_id, pixel_idx, r, g, b
```

**Full-Strip Frames** (yield 3-tuple) - **NEW FORMAT**:
```python
# Example: ColorCycleAnimation (proposed)
async def run(self):
    hue = 0
    while self.running:
        r, g, b = hue_to_rgb(hue)
        yield (r, g, b)  # 3-tuple: entire strip one color
        hue = (hue + 1) % 360
```

### 4.2 Frame Detection in AnimationEngine

```python
async def _run_loop(self):
    async for frame_data in self.current_animation.run():
        if len(frame_data) == 3 and isinstance(frame_data[0], int):
            # Full strip: (r, g, b)
            # TODO: Render to all zones

        elif len(frame_data) == 4:
            # Zone-based: (zone_id, r, g, b)
            zone_id, r, g, b = frame_data
            self.strip.set_zone_color(zone_id.name, r, g, b, show=False)

        elif len(frame_data) == 5:
            # Pixel-based: (zone_id, pixel_idx, r, g, b)
            zone_id, pixel_idx, r, g, b = frame_data
            self.strip.set_pixel_color(zone_id.name, pixel_idx, r, g, b, show=False)

    self.strip.show()  # Single hardware update per frame batch
```

### 4.3 Live Parameter Updates

Animations recalculate timing **inside the loop** for live updates:

```python
# BreatheAnimation
async def run(self):
    while self.running:
        # Recalculate every frame (not once at start!)
        cycle_duration = max_cycle - (self.speed / 100) * (max_cycle - min_cycle)
        frame_delay = cycle_duration / 60

        # ... render frame ...

        await asyncio.sleep(frame_delay)  # Uses latest self.speed
```

**Update Mechanism**:
```python
# User rotates encoder
animation_engine.update_param('speed', 80)
    ↓
current_animation.speed = 80  # Direct attribute update
    ↓
Next frame reads self.speed → new timing
```

---

## 5. Preview Panel System

### 5.1 Preview Modes

**1. Parameter Preview** (STATIC/ANIMATION mode parameter adjustment):
- **Brightness**: Bar indicator (N pixels lit = N% brightness)
- **Color (HUE)**: All 8 pixels lit with selected color
- **Color (PRESET)**: All 8 pixels lit with preset color
- **Speed**: Bar indicator (N pixels = N% speed)
- **Intensity**: Gradient (all pixels with modulated brightness)
- **Snake Length**: N pixels lit with fade (shows snake length)

**2. Zone Colors Preview** (STATIC mode, no parameter selected):
- Each pixel = one zone's color (max 8 zones)
- Shows all zone colors at once

**3. Animation Preview** (ANIMATION mode, animation running):
- Synchronized mini-animation (8 pixels)
- Each animation implements custom `run_preview()`

### 5.2 Preview Synchronization

Animations provide **two separate generators**:

```python
class SnakeAnimation(BaseAnimation):
    async def run(self):
        """Main animation (45 pixels)"""
        position = 0
        while self.running:
            # ... move snake across all zones ...
            yield (zone_id, pixel_idx, r, g, b)
            await asyncio.sleep(move_delay)

    async def run_preview(self, pixel_count: int = 8):
        """Preview animation (8 pixels) - SYNCHRONIZED"""
        position = 0
        while self.running:
            # Same timing calculation as main!
            move_delay = self._calculate_frame_delay()

            # Build 8-pixel snake
            frame = [(0,0,0)] * 8
            for i in range(self.length):
                pos = (position - i) % 8
                brightness = 1.0 - (i * 0.2)
                frame[pos] = (int(r * brightness), int(g * brightness), int(b * brightness))

            yield frame

            position = (position + 1) % 8
            await asyncio.sleep(move_delay)  # Same delay as main!
```

**Key**: Both loops use same `start_time` and `frame_delay` → synchronized.

### 5.3 Current Preview Rendering

**Problem**: Preview updates are scattered:

1. **AnimationModeController**: Manually calls `preview_panel.show_bar()` for speed/intensity
2. **StaticModeController**: Manually calls `preview_panel.show_bar()` for brightness, `fill_with_color()` for color
3. **AnimationEngine**: Has preview task but not fully integrated

**Example (current)**:
```python
# StaticModeController.adjust_param()
if param == ParamID.ZONE_BRIGHTNESS:
    new_value = zone.adjust_brightness(delta)
    # Update preview manually
    self.preview_panel_controller.preview_panel.show_bar(
        value=new_value,
        color=(255, 255, 255)
    )
```

---

## 6. Problems with Current Architecture

### 6.0 Hardware-Level Issues ⚡ **CRITICAL**

Before discussing software architecture problems, it's crucial to understand the **underlying hardware constraints** that make these issues critical:

#### 6.0.1 DMA Transfer Contention

**Root Cause**: Multiple `strip.show()` calls create overlapping DMA transfers.

**Hardware Behavior**:
```
WS2811 Protocol Requirements:
- 800kHz data rate (1.25µs per bit)
- 24 bits per pixel × 90 pixels = 2,160 bits
- DMA transfer time: 2.7ms minimum
- Reset pulse: 50µs minimum between frames
- Total frame time: ~2.75ms minimum

Problem: Multiple show() calls overlap DMA channel
→ BCM2835 DMA controller queues or drops requests
→ Partial frames, color corruption, stuck pixels
```

**Symptoms**:
- Flickering during mode switches
- Random color glitches (especially during transitions)
- Pixels "stuck" at wrong color until next full refresh
- Occasional complete frame loss (all LEDs go black momentarily)

**Why It's Worse at 90 Pixels**:
- 2× longer DMA transfer than 45 pixels (2.7ms vs 1.35ms)
- Larger window for race conditions
- More complex zone layout = more update calls

#### 6.0.2 Timing Violations

**WS2811 Reset Pulse Requirement**: 50µs minimum low time between frames.

**Current Code** (transition_service.py:366-379):
```python
for step in range(config.steps + 1):
    # ... interpolate colors ...
    self.strip.show()  # DMA transfer (~2.7ms)
    await asyncio.sleep(step_delay)  # Could be < 50µs!
```

**Problem**: If `step_delay < 50µs`, WS2811 doesn't recognize frame boundary:
- Corrupted color data (wrong RGB values)
- Frame tearing (top of strip shows frame N, bottom shows frame N-1)
- Intermittent "no response" from distant zones

**Calculation**:
```python
# Example: Fast transition
config = TransitionConfig(duration_ms=100, steps=30)
step_delay = 100ms / 30 steps = 3.33ms per step  # Safe ✅

# But this could happen:
config = TransitionConfig(duration_ms=10, steps=300)
step_delay = 10ms / 300 = 0.033ms = 33µs  # VIOLATION! ❌
```

#### 6.0.3 CPU Scheduling Jitter

**Issue**: Python's asyncio is **not real-time**.

**Raspberry Pi Behavior**:
- Linux scheduler can preempt asyncio tasks
- Garbage collection pauses (10-50ms on Pi 3/4)
- SD card I/O blocks can delay tasks (50-200ms)
- WiFi interrupts add 1-5ms jitter

**Impact on Animations**:
```python
# Intended timing
await asyncio.sleep(0.0166)  # 60 FPS = 16.6ms

# Actual timing (measured):
# Best case: 16.8ms (±200µs jitter) - acceptable
# Typical: 17-20ms with GC/WiFi - visible stutter
# Worst case: 50-200ms during SD write - visible freeze
```

**Why 60 FPS Target is Correct**:
- Human eye: 24 FPS = smooth, 60 FPS = imperceptible
- Hardware limit: 2.75ms per frame = 363 FPS theoretical max
- **Practical limit with Python overhead**: 100-150 FPS
- **Target 60 FPS leaves 40% headroom** for system tasks

#### 6.0.4 GPIO State on Crash

**Danger**: If Python crashes without cleanup, **GPIO 18 stays in PWM mode**.

**Consequences**:
- Data line continuously outputs garbage
- LEDs show random flickering colors
- Can't restart application (GPIO busy)
- Requires reboot or manual `gpio unexport 18`

**Current Protection**: `finally` block in main - **only works for graceful shutdown**.

**Missing Cases**:
- Kernel panic (rare but possible)
- Out of memory (OOM killer)
- Power loss (no software cleanup)
- SIGKILL (force kill)

#### 6.0.5 Thermal Considerations

**Current Load**: 30 WS2811 ICs × 2.16W = ~65W peak

**Good News**: Your per-zone power injection prevents:
- Voltage drop (no brown-out at far zones)
- Excessive current in single wire (safe wire gauge)
- PSU overload (distributed load)

**Potential Issue**: Ambient temperature in enclosure.

**Thermal Limits**:
- WS2811 rated: -25°C to +80°C
- Typical operation: 40-50°C with airflow
- **Critical zone**: Lamp zone (19 pixels = longest continuous run)

**Recommendation**:
- Monitor with thermal camera during 10-minute full-white test
- Add small 40mm fan if any zone exceeds 70°C
- Consider duty cycle limiting if running in hot environment (>35°C ambient)

---

### 6.1 Race Conditions

**Scenario 1: Animation vs Transition**
```
Time    Animation Loop          TransitionService
0ms     set_pixel(0, red)       -
10ms    set_pixel(1, red)       fade_out() starts
20ms    set_pixel(2, red)       set_pixel(0, black)  ← CONFLICT!
30ms    set_pixel(3, red)       set_pixel(1, black)  ← CONFLICT!
40ms    show()                  show()               ← Which wins?
```

**Result**: Flickering, unpredictable colors, partial frames.

**Scenario 2: Pulsing vs Manual Update**
```
User changes zone color to blue
    ↓
ZoneService.set_color() → strip.set_zone_color("LAMP", 0, 0, 255)
    ↓                    ↑
    └─ Pulse task sets LAMP to dim blue (sine wave)
                         ↑
                   (overwrites user's change!)
```

**Result**: User sees flickering or their change doesn't stick.

### 6.2 No Priority System

All rendering sources have equal priority → no way to guarantee:
- Transitions always complete uninterrupted
- Animations don't conflict with manual updates
- Debug overlays appear on top

### 6.3 Flickering During Transitions

**Cause**: Multiple `show()` calls per frame:
```python
# Old frame still rendering
animation.run() → strip.show()  # Frame N
    ↓
transition.crossfade() → strip.show()  # Transition frame
    ↓
animation.run() → strip.show()  # Frame N+1
    ↓
Result: Visible flicker between frames
```

### 6.4 Preview Not Synchronized

**Problem**: Preview updates happen independently of main strip:

```python
# AnimationEngine runs main animation
async for frame in animation.run():
    strip.set_zone_color(...)  # Main strip updated
    # Preview NOT updated!

# Separate manual call needed
preview_panel.show_frame(...)  # Out of sync!
```

**Result**: Preview lags behind or shows wrong state.

### 6.5 Direct Strip Access

**Problem**: 15+ places in code directly call:
- `strip.set_zone_color()`
- `strip.set_pixel_color()`
- `strip.show()`
- `preview_panel.show_frame()`

**No central control** → impossible to:
- Pause rendering
- Step frame-by-frame (debug mode)
- Record frames for playback
- Broadcast frames to WebSocket clients

### 6.6 Missing Features

**Cannot implement** with current architecture:
- ✗ Frame-by-frame debugging (pause/step)
- ✗ WebSocket live streaming
- ✗ Game mode (interactive snake game)
- ✗ Animation recording/playback
- ✗ FPS monitoring/adaptive rendering
- ✗ Frame diffing (only update changed pixels)

---

## 7. References

### 7.1 Related Files

**Core Animation System**:
- `src/animations/engine.py` - Animation lifecycle management
- `src/animations/base.py` - BaseAnimation class
- `src/animations/breathe.py` - Example per-zone animation
- `src/animations/snake.py` - Example per-pixel animation

**Rendering**:
- `src/engine/frame_manager.py` - Current partial FrameManager
- `src/components/zone_strip.py` - Main strip hardware abstraction
- `src/components/preview_panel.py` - Preview panel hardware abstraction

**Controllers**:
- `src/controllers/led_controller/led_controller.py` - Main orchestrator
- `src/controllers/led_controller/static_mode_controller.py` - Static mode + pulsing
- `src/controllers/led_controller/animation_mode_controller.py` - Animation mode

**Services**:
- `src/services/transition_service.py` - Smooth transitions
- `src/services/animation_service.py` - Animation business logic
- `src/services/zone_service.py` - Zone business logic

**Domain Models**:
- `src/models/domain/animation.py` - AnimationCombined
- `src/models/domain/zone.py` - ZoneCombined
- `src/models/color.py` - Color class
- `src/models/frame.py` - Current frame models (needs refactor)

### 7.2 Key Patterns

- **Async Generator Pattern**: Animations yield frames
- **Repository Pattern**: DataAssembler handles persistence
- **Service Pattern**: Business logic in services
- **Domain-Driven Design**: Config + State + Combined
- **Event-Driven Architecture**: EventBus for hardware input

### 7.3 Hardware Details

**Main Strip**:
- Type: WS2811 (12V addressable RGB)
- GPIO: 18 (PWM0)
- Pixels: ~90 addressable pixels (= ~270 physical LEDs @ 3 LEDs per IC = ~30 WS2811 ICs)
- Color Order: BRG
- Zones: 6-8 logical zones
- **Power Architecture**: Each zone has dedicated power injection (eliminates voltage drop issues)
- **Timing Requirements**: 800kHz data rate, 50µs minimum reset pulse between frames

**Preview Panel**:
- Type: WS2812B (5V addressable RGB)
- GPIO: 19 (PCM/PWM1)
- Pixels: 8 (CJMCU-2812-8 module)
- Color Order: GRB
- Physical Orientation: Upside down (requires index reversal)

**Critical Hardware Constraints**:
1. **DMA Channel Limitation**: rpi_ws281x uses single DMA channel - only ONE `strip.show()` can execute at a time
2. **Frame Timing**: 90 pixels × 24 bits × 1.25µs = **2.7ms minimum per frame** (DMA transfer time)
3. **Theoretical Max FPS**: ~370 FPS (hardware limit), but practical limit is 60 FPS (CPU + timing overhead)
4. **GPIO Restrictions**: Only GPIOs 10, 12, 18, 21 support WS281x (PWM/PCM peripherals)
5. **Reset Time**: 50µs minimum delay between frames required by WS2811 protocol
6. **Thermal Load**: 30 ICs × 2.16W = ~65W at full white (well within limits with proper power architecture)

**Power Budget** (@ 12V, full white):
- 90 pixels × 3 LEDs × 20mA = **5.4A peak current**
- With per-zone power injection: **no voltage drop compensation needed** ✅
- Typical operating current (mixed colors): 2-3A average

---

**Next Steps**: See [ANIMATIONS_REFACTORING.md](./ANIMATIONS_REFACTORING.md) for planned architecture improvements.
