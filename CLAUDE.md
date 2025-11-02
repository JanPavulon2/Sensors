# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Raspberry Pi LED control station with zone-based addressable RGB LED control, rotary encoder UI, and animation system. Runs asyncio event loop for non-blocking hardware polling.

**Hardware**: WS2811 (12V) addressable LEDs controlled via rpi_ws281x library. Two separate strips (preview panel + main strip), 2 rotary encoders, 4 buttons.

## Git Branching Strategy

This project uses a **version-based branching strategy**. See [BRANCHING.md](BRANCHING.md) for full details.

**Quick reference**:
- `main` - Production-ready releases only
- `version/X.Y` - Version in development (e.g., `version/0.1`)
- `feature/name` - Individual features (merged to version branch)

**Workflow**: Create feature branches from `version/X.Y`, merge features to version branch, merge completed versions to `main`.

## Running the Application

```bash
# Activate virtual environment
source diunaenv/bin/activate  # or: source venv/bin/activate

# Run main application (requires sudo for GPIO/WS281x access)
sudo diunaenv/bin/python3 src/main_asyncio.py

# Exit: Ctrl+C (gracefully saves state and cleans up GPIO)
```

**Important**: Must run with sudo because rpi_ws281x requires root permissions for PWM DMA access.

## Architecture Overview

### Event-Driven State Machine

The system uses an asyncio-based event-driven architecture with a central state machine (`LEDController`) that responds to hardware inputs:

```
Hardware Input (encoders/buttons)
    ↓
ControlModule (event callbacks)
    ↓
LEDController (state machine + business logic)
    ↓
Components (ZoneStrip, PreviewPanel, AnimationEngine)
    ↓
rpi_ws281x (hardware driver)
```

### Key Architecture Principles

1. **Color Model**: Uses `Color` class from `models/color.py`. Each zone has a `Color` object (single source of truth). Supports HUE, PRESET, RGB, and WHITE modes.

2. **Modular Configuration**: Config split into separate YAML files (hardware.yaml, zones.yaml, colors.yaml, animations.yaml, parameters.yaml) loaded via ConfigManager include system.

3. **Asyncio Everywhere**: All long-running operations (animations, pulsing, hardware polling) use `asyncio.create_task()` and `await`. No blocking sleeps.

4. **State Persistence**: `StateManager` auto-saves state after every user interaction. Brightness is 0-100%, colors use Color.to_dict() format.

5. **Animation Engine**: All animation lifecycle managed through `AnimationEngine`. No manual animation state flags - use `animation_engine.is_running()`.

6. **ParamID System**: Universal parameter identifiers (ZONE_COLOR_HUE, ZONE_COLOR_PRESET, ZONE_BRIGHTNESS, ANIM_SPEED, ANIM_INTENSITY) defined in `models/enums.py`.

7. **Zone-Based Control**: LEDs grouped into logical zones (lamp, top, right, bottom, left, strip). Each zone has independent color/brightness.

8. **Two-Mode System**:
   - **STATIC mode**: Zone editing (default). Cycle zones with upper encoder, adjust zone params with lower encoder.
   - **ANIMATION mode**: Animation control. Select animation with upper encoder, adjust anim params with lower encoder.
   - **Toggle**: BTN4 switches between modes. Automatically starts/stops animations.
   - **Edit mode**: BTN1 toggles ON/OFF. When OFF, encoders disabled.

### Critical Components

#### LEDController (`src/led_controller.py`)
Central state machine. Owns all LED state and business logic.

**Key State**:
- `zone_colors`: Dict[str, Color] - Color objects for each zone (SINGLE SOURCE OF TRUTH)
- `zone_brightness`: Dict[str, int] - brightness 0-100%
- `main_mode`: MainMode.STATIC or MainMode.ANIMATION
- `current_param`: ParamID (e.g., ZONE_COLOR_HUE, ANIM_SPEED)
- `current_zone_index`: Index into zone_names list
- `edit_mode`: Global enable/disable for editing
- `lamp_white_mode`: Special mode where lamp is locked to warm white and excluded from all operations
- `animation_engine`: AnimationEngine instance - manages all animation lifecycle

**Key Methods**:
- `_get_zone_color(zone_name)`: Renders Color object to RGB with brightness applied
- `handle_upper_rotation(delta)`: Context-sensitive (change zone in STATIC, select animation in ANIMATION)
- `handle_upper_click()`: Start/stop animation in ANIMATION mode
- `handle_lower_rotation(delta)`: Adjust current parameter value
- `handle_lower_click()`: Cycle parameters
- `_start_pulse()` / `_stop_pulse()`: Async pulsing animation (1s cycle, fixed)
- `toggle_main_mode()`: Switch STATIC ↔ ANIMATION, auto-start/stop animations
- `animation_engine.is_running()`: Check animation state (NOT a manual flag)

#### ZoneStrip (`src/components/zone_strip.py`)
Hardware abstraction for WS2811 LED strips divided into zones.

**Important**: `zones` dict format is `{"zone_name": [start_index, end_index]}` where indices are 0-based pixel positions.

**PixelStrip constructor params**:
```python
PixelStrip(
    num,           # total pixel count
    pin,           # GPIO number (18=PWM0, 19=PCM/PWM1)
    freq_hz,       # 800000 = 800kHz for WS2811
    dma,           # DMA channel (10 is safe)
    invert,        # False = normal signal
    brightness,    # 0-255 global brightness
    channel,       # PWM channel (0 or 1)
    strip_type     # ws.WS2811_STRIP_BRG for main strip
)
```

#### AnimationEngine (`src/animations/engine.py`)
Manages animation lifecycle. Each animation is an async task that yields frames.

**Key**: `excluded_zones` parameter - zones to skip (used for `lamp_white_mode`).

**Animations**:
- `breathe`: Sine wave breathing effect
- `color_fade`: Rainbow hue cycling
- `snake`: Sequential zone chase effect

All animations recalculate frame timing parameters **inside the loop** to support live speed updates.

#### StateManager (`src/managers/state_manager.py`)
Async JSON persistence. Saves to `src/config/state.json` after every user action (no autosave loop needed).

### Color System Architecture

**Critical**: Uses `Color` class (models/color.py) as single source of truth.

**Color class supports 4 modes**:
1. **HUE**: Hue value (0-360°) with full saturation
2. **PRESET**: Named presets from ColorManager (e.g., "red", "ocean", "warm_white")
3. **RGB**: Direct RGB values (0-255)
4. **WHITE**: Special white mode (warm/cool/neutral)

**Color Flow**:
```
User adjusts color (HUE or PRESET)
    ↓
handle_lower_rotation()
    ↓
Color.adjust_hue(delta) OR Color.next_preset(delta, color_manager)
    ↓
Returns NEW Color object (immutable pattern)
    ↓
zone_colors[zone] = new_color
    ↓
Pulsing/rendering: color.to_rgb() → (r, g, b)
```

**State Persistence**:
- Save: `Color.to_dict()` → `{"mode": "PRESET", "preset_name": "red"}`
- Load: `Color.from_dict(data, color_manager)` → Color object

**Key Methods**:
- `color.to_rgb()`: Render to (r, g, b) tuple
- `color.to_hue()`: Get hue value (0-360)
- `color.adjust_hue(delta)`: Return new Color with adjusted hue
- `color.next_preset(delta, mgr)`: Return new Color with next/prev preset

### lamp_white_mode System

Special mode activated by BTN2 (quick_lamp_white function):

**When lamp_white_mode=True**:
- Lamp excluded from zone selector (`change_zone()` skips it)
- Lamp excluded from pulsing (`_pulse_zone_task()` skips it)
- Lamp excluded from animations (`start_animation()` passes `excluded_zones=["lamp"]`)
- Lamp color locked to warm_white preset
- If lamp was current_zone, auto-switches to next zone

**State saved**: Previous hue, brightness, preset, color_mode, actual RGB
**Toggle behavior**: BTN2 toggles ON→OFF→ON

**Critical**: When restoring power after power_toggle, must check `lamp_white_mode` and apply warm_white RGB directly (not from zone_hues).

### Pulsing System

Edit mode indicator - currently selected zone pulses at 1Hz sine wave (10%→100% brightness).

**Key Details**:
- Fixed 1.0s cycle (independent from `animation_speed`)
- Runs in async task: `_pulse_zone_task()`
- Always reads `zone_hues[current_zone]` dynamically (no caching)
- Skips lamp when `lamp_white_mode=True`
- Stops during animations, restarts when animation stops

**Why fixed 1s**: Pulsing indicates edit mode, not animation speed. User reported strobing when pulsing used `animation_speed`.

## Hardware Configuration

### GPIO Mapping (config.yaml)

```yaml
hardware:
  encoders:
    zone_selector: { clk: 5, dt: 6, sw: 13 }   # Zone selection + mode switch
    modulator: { clk: 16, dt: 20, sw: 21 }      # Parameter adjustment

  buttons: [22, 26, 23, 24]                      # BTN1-4 left to right

  leds:
    preview:
      gpio: 19              # Preview panel (8 LEDs)
      color_order: GRB      # CJMCU-2812-8
    strip:
      gpio: 18              # Main strip (45 pixels = 15 WS2811 ICs)
      color_order: BRG      # WS2811 hardware
```

**Critical**: GPIO 19 does NOT support WS281x (attempted swap failed). Only GPIOs 10, 12, 18, 21 work for WS281x. Preview uses GPIO 19 only because it works in testing (may be library version specific).

### Button Mapping

- **BTN1** (GPIO 22): Toggle edit_mode ON/OFF
- **BTN2** (GPIO 26): Quick lamp white mode toggle
- **BTN3** (GPIO 23): Power toggle (all zones ON/OFF)
- **BTN4** (GPIO 24): Reserved (currently no-op)

### Physical LED Layout

Main strip is **12V WS2811** (not 5V WS2812B):
- Each WS2811 IC controls 3 physical LEDs (RGB triplet)
- 45 "pixels" in software = 15 ICs × 3 LEDs each = 45 physical LEDs total

**Zone mapping** (from config, automatically calculated):
```
strip:  0-11   (12 pixels = 36 LEDs)
lamp:   12-30  (19 pixels = 57 LEDs)
top:    31-34  (4 pixels = 12 LEDs)
right:  35-37  (3 pixels = 9 LEDs)
bottom: 38-41  (4 pixels = 12 LEDs)
left:   42-44  (3 pixels = 9 LEDs)
```

**Physical order for snake animation**: lamp → top → right → bottom → left → strip (sorted by start_index).

## Common Patterns

### Adding New Animation

1. Create `src/animations/new_animation.py` inheriting from `BaseAnimation`
2. Implement `__init__()` with `super().__init__(zones, speed, excluded_zones, **kwargs)`
3. Implement async `run()` method that yields frames in infinite loop
4. Recalculate timing parameters **inside loop** for live speed updates:
   ```python
   while self.running:
       frame_delay = self._calculate_frame_delay()  # Uses self.speed
       # ... render frame ...
       await asyncio.sleep(frame_delay)
   ```
5. Filter `self.active_zones` to exclude `self.excluded_zones`
6. Register in `src/animations/__init__.py`
7. Add to `available_animations` list in `LEDController.__init__()`

### Modifying Hardware Pins

**GPIO changes**: Update `src/config/config.yaml` only. Code reads from config.

**WS281x restrictions**: Only GPIOs 10, 12, 18, 21 support WS281x. Attempting other pins will fail with `RuntimeError: ws2811_init failed with code -11`.

### State Persistence

State auto-saves after every user action. To add new state:

1. Add attribute to `LEDController`
2. Update `get_status()` method to include new state
3. Update `StateManager.update_from_led()` to sync new state
4. Update `src/config/state.json` structure if needed

No migration system - just add new keys with defaults in `state.get("key", default)`.

### Color Handling

**Always use HUE as source of truth**:
```python
# CORRECT - render from zone_hues
hue = self.zone_hues[zone_name]
r, g, b = hue_to_rgb(hue)

# WRONG - don't render from presets
preset_idx = self.zone_preset_indices[zone_name]
_, (r, g, b) = get_preset_by_index(preset_idx)  # This loses HUE adjustment!
```

**Exception**: `lamp_white_mode` applies preset RGB directly to preserve exact warm_white color (255, 200, 150).

## Critical Bugs Fixed (Don't Reintroduce)

1. **pulse_task initialization**: Must initialize `self.pulse_task = None` in `__init__()` before `_start_pulse()`. Otherwise AttributeError on cleanup.

2. **Edit mode pulsing**: Only start pulsing if `edit_mode=ON` at startup. Check `if self.edit_mode: self._start_pulse()`.

3. **PRESET mode color changing**: Never use `zone_preset_indices` for rendering. Always render from `zone_hues`. PRESET mode converts RGB→HUE on selection.

4. **Pulsing speed**: Pulsing must be fixed 1.0s cycle, not dependent on `animation_speed`. Separate concerns: pulsing indicates edit mode, not animation speed.

5. **lamp_white_mode persistence**: When restoring power after `power_toggle()`, check `lamp_white_mode` and apply warm_white RGB directly (not from zone_hues which may have different hue stored).

6. **Snake zone order**: Sort zones by `start_index` (physical position), not alphabetically. Otherwise sequence is wrong.

7. **Live animation speed**: Recalculate frame timing **inside animation loop**, not once at start. Otherwise speed changes require animation restart.

## Development Notes

### Type Hints

Type stubs don't exist for `rpi_ws281x`. Added inline type annotations and detailed docstrings with parameter explanations for intellisense support.

Example: `PixelStrip()` constructor has inline comments explaining each parameter (800000 = 800kHz, etc.).

### Testing Without Hardware

Most development requires actual Raspberry Pi hardware with WS281x LEDs. No mock/simulation layer exists. For testing logic changes, consider:
- Comment out `self.strip.begin()` and hardware setup
- Mock `PixelStrip` and `Color` with dummy classes
- Test state machine logic in isolation

### Debugging Animations

Animations run in background asyncio tasks. To debug:
```python
# Add prints inside animation loop
print(f"[ANIM] Frame {step}: zone={zone_name}, color=({r},{g},{b})")
```

**Common issue**: If animation appears "stuck", check if `self.running` flag is being set correctly and `while self.running:` loop is exiting.

### GPIO Cleanup

Always cleanup GPIO on exit to avoid "channel already in use" errors:
```python
finally:
    led.clear_all()
    module.cleanup()  # Calls GPIO.cleanup()
```

If error persists after crash, run: `sudo systemctl restart pigpiod` or reboot Pi.
