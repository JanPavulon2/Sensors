---
Last Updated: 2025-11-25
Type: Agent Documentation
Purpose: All 9 controllers, relationships, and active status
---

# Controller Relationships

## The 9 Controllers

### 1. LEDController (Main Orchestrator)

**File**: `src/controllers/led_controller/led_controller.py`
**Lines**: 597
**Status**: ✅ ACTIVE (core system)

**Responsibilities**:
- Main event router and state machine
- Coordinates between all other controllers
- Owns AnimationEngine instance
- Routes keyboard/encoder input

**Dependencies**: ↓ (depends on)
- StaticModeController
- AnimationModeController
- ZoneStripController
- AnimationEngine

**Event Handlers**:
- `EncoderRotateEvent` (SELECTOR) → `change_zone()` or `select_animation()`
- `EncoderRotateEvent` (MODULATOR) → `adjust_parameter()` (routed by zone mode)
- `EncoderClickEvent` (SELECTOR) → `toggle_zone_mode()`
- `ButtonPressEvent` (BTN1-4) → Mode switches, lamp control, power

**Per-Zone Mode Logic**:
- Tracks selected zone
- Each zone has independent `ZoneRenderMode` (STATIC/ANIMATION/OFF)
- Routes input to appropriate controller based on zone mode

```python
# Example routing
if selected_zone.mode == ZoneRenderMode.STATIC:
    await self.static_controller.adjust_hue(delta)  # Adjust static color
elif selected_zone.mode == ZoneRenderMode.ANIMATION:
    await self.animation_controller.adjust_param(delta)  # Adjust animation
```

---

### 2. StaticModeController (Zone Editing)

**File**: `src/controllers/led_controller/static_mode_controller.py`
**Lines**: 241
**Status**: ✅ ACTIVE (per-zone static colors)

**Responsibilities**:
- Manage static zone colors
- Color editing (hue, saturation, presets)
- Brightness adjustment
- Pulsing effect (edit mode)

**Dependencies**: ↓
- ZoneStripController (submit frames)
- Zone state model

**Key Methods**:
- `render_zone(zone_id, color, brightness)` - Submit zone color to FrameManager
- `adjust_hue(delta)` - Rotate color hue
- `adjust_brightness(delta)` - Adjust zone brightness
- `cycle_preset(delta)` - Switch color presets
- `start_pulse()` / `stop_pulse()` - Pulsing effect
- `_pulse_task()` - Async pulsing loop (submits frames with PULSE priority)

**Frame Submission Pattern**:
```python
# Build zone colors dict
zone_colors = {selected_zone.config.id: (zone.state.color, zone.brightness)}

# Submit to FrameManager
await self.strip_controller.submit_all_zones_frame(zone_colors, priority=MANUAL)
```

**Pulsing Implementation**:
```python
async def _pulse_task(self):
    while self.pulse_active:
        brightness = compute_sine_wave()
        color = self.get_current_color().with_brightness(brightness)
        await self.strip_controller.submit_all_zones_frame({
            selected_zone: color
        }, priority=PULSE)  # Higher than MANUAL (20 > 10)
        await asyncio.sleep(1/60)
```

---

### 3. AnimationModeController (Animation Selection)

**File**: `src/controllers/led_controller/animation_mode_controller.py`
**Lines**: 255
**Status**: ✅ ACTIVE (per-zone animations)

**Responsibilities**:
- Animation selection (cycling through available)
- Parameter adjustment (speed, intensity, color)
- Start/stop animations
- Per-zone animation handling

**Dependencies**: ↓
- AnimationEngine (start/stop animations)
- Animation service (metadata)

**Key Methods**:
- `select_animation(delta)` - Cycle animations, auto-switch
- `adjust_param(delta)` - Live parameter updates
- `toggle_animation()` - Start/stop selected animation
- `_switch_to_selected_animation()` - Switch with transition

**Per-Zone Animation**:
```python
# When animation starts
excluded_zones = [
    zone.config.id for zone in self.zone_service.get_all()
    if zone.config.id != self.selected_zone.config.id
]

await self.animation_engine.start(
    anim_id=self.selected_animation_id,
    excluded_zones=excluded_zones,  # All except selected
    speed=self.speed,
    color=self.primary_color
)
```

**Parameter Tuning**:
```python
async def adjust_param(self, param_id: ParameterID, delta: int):
    if param_id == ParameterID.ANIM_SPEED:
        self.speed += delta
        await self.animation_engine.update_parameter('speed', self.speed)
```

---

### 4. ZoneStripController (Rendering Interface)

**File**: `src/controllers/zone_strip_controller.py`
**Lines**: 273
**Status**: ✅ ACTIVE (unified rendering entry point)

**Responsibilities**:
- High-level interface for zone rendering
- Translates domain types (Color, ZoneID) to frames
- Coordinates transitions
- Unified FrameManager integration point

**Dependencies**: ↓
- FrameManager (submit frames)
- TransitionService (transition coordination)

**Key Methods**:
- `submit_all_zones_frame(zones_colors, priority)` - Main rendering method
  - Converts Color objects to RGB
  - Applies zone brightness
  - Creates ZoneFrame
  - Submits to FrameManager
- `startup_fade_in(zone_service, config)` - Startup transition
- `fade_out_all(config)` - Fade to black
- `fade_in_all(target_frame, config)` - Fade from black

**Rendering Path** (complete):
```python
async def submit_all_zones_frame(self, zones_colors, priority):
    # zones_colors: {zone_id: Color, ...}

    # Convert colors with brightness
    zone_frames = {}
    for zone in self.zone_service.get_all():
        if zone.config.id in zones_colors:
            color = zones_colors[zone.config.id]
            r, g, b = color.to_rgb_with_brightness(zone.brightness)
            zone_frames[zone.config.id] = (r, g, b)

    # Create frame
    frame = ZoneFrame(zones=zone_frames, priority=priority)

    # Submit to FrameManager
    await self.frame_manager.submit_zone_frame(frame)
```

**Why This Controller?**
- Single point for all zone rendering
- No other controller calls FrameManager directly
- Ensures consistent color→RGB conversion
- Maintains abstraction boundary

---

### 5. PowerToggleController (Power Management)

**File**: `src/controllers/led_controller/power_toggle_controller.py`
**Lines**: ~150
**Status**: ✅ ACTIVE

**Responsibilities**:
- Power on/off toggling
- Fade out → off transition
- Fade in → on transition

**Dependencies**: ↓
- ZoneStripController (rendering)
- TransitionService (transitions)

**Flow**:
```
User presses power button
  ↓
PowerToggleController detects
  ↓
if powered_on:
  fade_out(all zones to black)  [TRANSITION priority]
  stop_animations()
  set powered_off
else:
  fade_in(restore previous state)  [TRANSITION priority]
  resume_animations()
  set powered_on
```

---

### 6. LampWhiteModeController (Lamp Mode)

**File**: `src/controllers/led_controller/lamp_white_mode_controller.py`
**Lines**: ~100
**Status**: ✅ ACTIVE

**Responsibilities**:
- Toggle LAMP zone to white mode
- Special mode for using LAMP as regular light

**Dependencies**: ↓
- ZoneStripController (rendering)

**Flow**:
```
User presses LAMP button (BTN2)
  ↓
if lamp_white_mode_on:
  disable_lamp_white_mode()
  restore_lamp_to_normal_mode()
else:
  enable_lamp_white_mode()
  set_lamp_to_white_color()
  brightness_100%
```

---

### 7. FramePlaybackController (Frame-by-Frame Debugging)

**File**: `src/controllers/led_controller/frame_playback_controller.py`
**Lines**: ~300
**Status**: ✅ IMPLEMENTED (ready for testing)

**Responsibilities**:
- Frame-by-frame debugging mode
- Preload animation frames offline
- Frame navigation and logging

**Dependencies**: ↓
- AnimationEngine (preload frames)
- FrameManager (render specific frames)

**Key Features**:
- Keyboard navigation: A/D (prev/next frame), SPACE (play/pause), Q (quit)
- Frame logging with RGB/hex output
- Play/pause toggle
- Integration with EventBus

**Status Note**: Implemented but untested with actual keyboard events. Needs verification that keyboard events properly trigger controller.

---

### 8. ControlPanelController (Hardware Input)

**File**: `src/controllers/control_panel_controller.py`
**Lines**: ~150
**Status**: ✅ ACTIVE

**Responsibilities**:
- Hardware input polling (encoders, buttons)
- Event publishing to EventBus
- Hardware abstraction

**Inputs**:
- Encoder SELECTOR (rotate left/right)
- Encoder MODULATOR (rotate left/right)
- Button 1 (edit mode)
- Button 2 (lamp white)
- Button 3 (power toggle)
- Button 4 (zone mode toggle)

**Flow**:
```
Poll GPIO inputs continuously
  ↓
Detect rotation/press/release
  ↓
Publish event to EventBus:
  EncoderRotateEvent(encoder, direction, amount)
  ButtonPressEvent(button)
  ButtonReleaseEvent(button)
  ↓
EventBus routes to subscribers (controllers)
```

---

### 9. PreviewPanelController (Preview Visualization)

**File**: `src/controllers/preview_panel_controller.py`
**Lines**: ~200
**Status**: ⚠️ DISABLED (not integrated with FrameManager)

**Responsibilities**:
- 8-LED preview panel control
- Animation preview rendering
- Parameter visualization (brightness bar, color fill)

**Current Issue**:
- PreviewPanelController exists but disabled in main_asyncio.py (line 237-259)
- Not integrated with FrameManager
- Needs `PreviewService` to consume `animation.run_preview()` generators

**Integration Plan**:
```python
# Create PreviewService
class PreviewService:
    async def start_preview(self, animation_id, **params):
        # Create animation generator
        gen = animation(zone=PREVIEW, **params)

        # Consume yields
        async for (pixel_idx, color) in gen:
            frame = PreviewFrame(pixels=[...])
            await frame_manager.submit_preview_frame(frame)

# Then PreviewPanelController can use it
```

---

## Controller Dependency Graph

```
User Input (Keyboard, Encoders, Buttons)
     ↓
ControlPanelController (polls hardware)
     ↓ publishes events
EventBus (pub/sub)
     ↓ routes to
LEDController (main orchestrator)
     │
     ├─→ StaticModeController
     │     ↓
     │     ZoneStripController
     │           ↓
     │           FrameManager (submit frame)
     │
     ├─→ AnimationModeController
     │     ↓
     │     AnimationEngine (start/stop/param)
     │           ↓
     │           (engine submits frames to FrameManager)
     │
     ├─→ PowerToggleController
     │     ↓
     │     TransitionService (fade out/in)
     │           ↓
     │           FrameManager (submit transition frames)
     │
     ├─→ LampWhiteModeController
     │     ↓
     │     ZoneStripController
     │
     └─→ FramePlaybackController
           ↓
           FrameManager (direct frame submission for debugging)

FrameManager (central hub)
     ↓ receives frames from
     ├─ AnimationEngine (animations)
     ├─ StaticModeController (via ZoneStripController)
     ├─ TransitionService (transitions)
     ├─ FramePlaybackController (debugging)
     └─ PreviewService (preview, when implemented)
```

---

## Active Controller Status

✅ **7 Controllers Fully Active**:
1. LEDController - Main orchestrator
2. StaticModeController - Zone editing
3. AnimationModeController - Animations
4. ZoneStripController - Rendering interface
5. PowerToggleController - Power control
6. LampWhiteModeController - Lamp mode
7. ControlPanelController - Hardware input

✅ **1 Controller Implemented, Needs Testing**:
8. FramePlaybackController - Frame debugging (needs keyboard integration testing)

⚠️ **1 Controller Disabled, Needs Integration**:
9. PreviewPanelController - Preview panel (disabled, needs PreviewService)

---

## Per-Zone Mode Handling

The system supports **independent per-zone modes**:

```python
# Zone state
class ZoneState:
    mode: ZoneRenderMode  # STATIC, ANIMATION, or OFF

# Each zone has its own mode
FLOOR: ZoneState(mode=ANIMATION)  # Running animation
LEFT: ZoneState(mode=STATIC)       # Static color
TOP: ZoneState(mode=OFF)           # Disabled
```

**How It Works**:

1. **User selects zone** (via encoder):
   ```python
   selected_zone = FLOOR
   ```

2. **User toggles mode**:
   ```python
   # Before
   FLOOR.mode = STATIC (was static red)

   # User presses mode button
   # After
   FLOOR.mode = ANIMATION (now animating)
   ```

3. **LEDController routes to correct controller**:
   ```python
   if selected_zone.mode == ANIMATION:
       await animation_controller.toggle_animation()
   elif selected_zone.mode == STATIC:
       await static_controller.render_zone(...)
   ```

4. **Result**: Each zone can independently animate or stay static

---

## Key Design Patterns

### 1. Single Responsibility
- Each controller handles one concern
- LEDController routes, doesn't implement logic
- ZoneStripController centralizes rendering

### 2. Dependency Injection
- Controllers receive dependencies in `__init__`
- No global singletons
- Easy to test with mocks

### 3. Frame Submission
- All controllers submit to FrameManager
- Never call hardware directly
- Use appropriate priority levels

### 4. Event-Driven
- Input published as events
- Controllers subscribe to events
- Loose coupling

### 5. Per-Zone Independence
- Each zone has own state and mode
- Selected zone gets modified
- Other zones unaffected
- Enables rich multi-effect scenes

---

**Next**: [Rendering Pipeline Details](4_rendering_pipeline_details.md)
