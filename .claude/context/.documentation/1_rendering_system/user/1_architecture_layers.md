---
Last Updated: 2025-11-25
Type: User Documentation
Purpose: Detailed explanation of the 6-layer architecture
---

# Architecture Layers

The rendering system is organized into **6 clean layers**, each with specific responsibilities and clear boundaries. This layering enables hardware independence, testability, and maintainability.

## Layer Overview

```
┌─────────────────────────────────────────┐
│ Layer 6: Application                    │  Controllers, event routing, user input
├─────────────────────────────────────────┤
│ Layer 5: Services                       │  Transitions, animations, state management
├─────────────────────────────────────────┤
│ Layer 4: Animation System               │  Animation lifecycle, frame submission
├─────────────────────────────────────────┤
│ Layer 3: Engine (FrameManager)          │  Priority selection, atomic rendering
├─────────────────────────────────────────┤
│ Layer 2: Zone Layer                     │  Zone-to-pixel mapping, buffering
├─────────────────────────────────────────┤
│ Layer 1: Hardware Abstraction           │  LED communication, GPIO
└─────────────────────────────────────────┘
```

## Layer 1: Hardware Abstraction

**Responsibility**: Communicate with physical LED strips

**Key Features**:
- All hardware access isolated here
- Supports multiple LED strip types (WS2811, WS2812B, etc.)
- Handles GPIO-specific details (pins, data formats)
- Color order mapping (BGR vs RGB vs GRB)
- DMA buffer management for efficient transmission

**API**:
```
IPhysicalStrip (interface)
├── apply_frame(pixel_array)      # Load frame into DMA buffer
└── show()                         # DMA transfer to LEDs
```

**Constraints**:
- Physical timing (minimum time between frames)
- Color order varies by hardware/GPIO pin
- DMA buffer capacity (all pixels must fit)

**Key Principle**: This is the ONLY layer that directly touches hardware. All other code is completely hardware-agnostic.

---

## Layer 2: Zone Layer

**Responsibility**: Map logical zones to physical pixels

**Key Features**:
- Implements zone-to-pixel mapping
- Supports zone reversal (pixels rendered backwards)
- Maintains pixel buffer for atomic updates
- Zone color caching for performance
- Single entry point for all rendering

**API**:
```
ZoneStrip
├── show_full_pixel_frame(pixels)  # Render all zones
└── zone_pixel_mapper()            # Zone ID → pixel indices
```

**Key Abstraction**: Clients work with zones and colors; ZoneStrip converts to pixels internally.

**Example Use**:
```
Zone FLOOR has 15 pixels (indices 0-14)
Zone LEFT has 10 pixels (indices 15-24)

Application says: "Set FLOOR to red"
ZoneStrip translates to: pixels[0:15] = red
Then calls: hardware.apply_frame(all_pixels)
```

---

## Layer 3: Engine (FrameManager)

**Responsibility**: Select and render highest-priority frame

**Key Features**:
- **Dual priority queues** (main strip + preview panel)
- **Priority system** (0-100, higher = more important)
- **TTL-based expiration** (frames expire after ~100ms)
- **Type-specific selection** (ZoneFrame vs PixelFrame vs others)
- **Atomic rendering** (single `show()` per cycle)
- **Frame history** (for debugging and transitions)

**Frame Selection Process**:
```
1. Scan all submitted frames
2. Filter out expired frames (older than TTL)
3. Group by type (ZoneFrame, PixelFrame, etc.)
4. Select highest priority frame from each type
5. Render selected frames to zones
6. Call zone.show() for hardware
```

**Key Design**:
- Frame sources (animations, transitions, static modes) submit frames
- Frame manager handles conflict resolution via priority
- Sources don't coordinate with each other—pure decoupling

**Result**: When both animation and static mode submit frames:
- Animation priority (30) wins over static priority (10)
- Animation pixels are displayed
- Sources don't know about each other

---

## Layer 4: Animation System

**Responsibility**: Manage animation lifecycle and frame generation

**Key Features**:
- **Animation registry** (available animations and their metadata)
- **Generator-based** (animations are async generators)
- **Per-zone support** (animate one zone, exclude others)
- **Static zone merging** (static zones merge with animation)
- **Crossfading** (smooth transitions between animations)
- **Parameter updates** (live adjustment of speed, intensity, color)
- **Freeze/unfreeze** (frame-by-frame debugging)

**Animation Lifecycle**:
```
start(animation_id, excluded_zones, parameters)
    ↓
Create animation instance (async generator)
    ↓
_run_loop() consumes yields
    ↓
Each yield → convert to frame object
    ↓
Submit frame to FrameManager with ANIMATION priority
    ↓
Rendering loop displays frame
    ↓
stop() cleanly exits animation
```

**Generator Types**:
- **Zone-based**: Yield `(zone_id, r, g, b)` for single zone colors
- **Pixel-based**: Yield `(zone_id, pixel_idx, r, g, b)` for individual pixels
- **Full-strip**: Yield `(r, g, b)` array for all pixels

**Static Zone Merging**:
```
Animation running on FLOOR, LAMP is static red
    ↓
Animation yields: FLOOR colors
    ↓
Engine merges with: LAMP red
    ↓
Result: FLOOR animated, LAMP static red simultaneously
```

---

## Layer 5: Transition Service

**Responsibility**: Smooth transitions between LED states

**Key Features**:
- **Preset transitions** (startup, shutdown, mode switch)
- **Interpolation algorithms** (easing functions, crossfade)
- **Frame submission** (transitions also use priority system)
- **Locking** (prevents concurrent transitions)
- **Wait synchronization** (can wait for transition to complete)

**Transition Types**:
- **Fade in**: Black → target (gradually brighten)
- **Fade out**: Current → black (gradually dim)
- **Crossfade**: Current → target (smooth color transition)

**Implementation**:
```
Transition generates many intermediate frames:
Frame 0:   0% target
Frame 1:   5% target
Frame 2:  10% target
...
Frame 20: 100% target

Each frame submitted with TRANSITION priority (40)
FrameManager selects and displays each frame
Result: Smooth visual transition
```

**Key**: Transitions run through FrameManager like any other frames—they don't bypass normal rendering.

---

## Layer 6: Application (Controllers & Services)

**Responsibility**: Interpret user input and coordinate system behavior

**Key Components**:
- **LED Controller**: Main orchestrator, routes input to appropriate mode controller
- **Static Mode Controller**: Handle zone selection, color editing, pulsing effects
- **Animation Mode Controller**: Animation selection, parameter tuning
- **Zone Strip Controller**: High-level zone rendering interface
- **Power Toggle Controller**: Power on/off with transitions
- **Other Controllers**: Lamp mode, preview panel, etc.

**Event Flow**:
```
Keyboard/button/knob input
    ↓
ControlPanelController (hardware polling) publishes event
    ↓
EventBus routes to appropriate handler
    ↓
Handler updates state, calls appropriate service
    ↓
Service (animation engine, transition service) handles action
    ↓
Frames submitted to FrameManager
    ↓
Rendering happens
```

**Key Pattern**: Controllers don't render directly. They:
1. Update application state
2. Call services (AnimationEngine, TransitionService, etc.)
3. Services submit frames to FrameManager
4. FrameManager handles rendering

---

## Data Flow Example

**Scenario**: User wants to start a "Breathe" animation

```
1. User presses button (hardware event)
   ↓
2. ControlPanelController detects, publishes ButtonPressEvent
   ↓
3. LEDController routes to AnimationModeController
   ↓
4. AnimationModeController calls:
   animation_engine.start('BREATHE', excluded_zones=[...], speed=50)
   ↓
5. AnimationEngine starts breathing animation generator
   ↓
6. _run_loop() consumes yields:
   animation yields: (zone_id=FLOOR, r=255, g=100, b=50)
   ↓
7. Convert to frame object:
   ZoneFrame(zones={FLOOR: Color(255, 100, 50)}, priority=ANIMATION)
   ↓
8. Submit to FrameManager:
   frame_manager.submit_zone_frame(frame)
   ↓
9. FrameManager.render() cycle:
   - Select highest priority frame (ANIMATION=30)
   - Convert ZoneFrame to pixel array
   - Call led_channel.show_full_pixel_frame(pixels)
   ↓
10. ZoneStrip.show_full_pixel_frame():
    - Convert pixel array colors to RGB
    - Load into DMA buffer
    - Call hardware.show()
    ↓
11. Hardware:
    - DMA transfer to GPIO pin
    - LEDs update to show animation
```

---

## Layer Dependencies

```
Layer 6 (Application)
    ↓ uses
Layer 5 (Transition Service, Animation System)
    ↓ uses
Layer 4 (Animation Engine)
    ↓ uses
Layer 3 (FrameManager)
    ↓ uses
Layer 2 (Zone Layer)
    ↓ uses
Layer 1 (Hardware Abstraction)
```

**Important**: Each layer only knows about layers below it. No upward dependencies. This maintains architectural cleanliness.

---

## Clean Architecture Benefits

### Independence
- Each layer can be tested independently
- Hardware can be mocked or replaced
- Animation logic is separate from hardware

### Flexibility
- New animation types don't require hardware changes
- New hardware types don't require application changes
- Easy to add new features at appropriate layer

### Maintainability
- Clear responsibilities per layer
- Bugs are easier to locate and fix
- Changes don't ripple through entire system

### Type Safety
- Each layer uses appropriate domain types
- Hardware layer can validate types at boundary
- Impossible to pass pixel indices to animation code

---

**Next:** [Hardware Abstraction](2_hardware_abstraction.md)