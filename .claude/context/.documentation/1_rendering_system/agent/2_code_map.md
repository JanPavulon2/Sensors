---
Last Updated: 2025-11-25
Type: Agent Documentation
Purpose: File locations, entry points, and key line numbers
---

# Code Map

## Entry Points

### Application Entry
- **File**: `src/main_asyncio.py`
- **Lines**: 364 total
- **Purpose**: Application initialization and main event loop
- **Key functions**:
  - `main()` - Application entry point
  - `_create_frame_manager()` - Creates FrameManager instance
  - `_create_zone_strips()` - Creates WS281xStrip per GPIO
  - `_create_services()` - Initializes all services
  - `_create_controllers()` - Initializes all controllers
  - `_run_event_loop()` - Main async event loop

### Hardware Layer Entry
- **File**: `src/hardware/led/ws281x_strip.py`
- **Lines**: 200+
- **Purpose**: GPIO-level LED control
- **Key class**: `WS281xStrip` - Implements `IPhysicalStrip`

---

## Rendering System Core

### FrameManager (Engine)
- **File**: `src/engine/frame_manager.py`
- **Lines**: 800+
- **Purpose**: Priority-based frame selection and rendering

**Key Methods**:
- `submit_zone_frame(frame)` - Line ~150 - Submit ZoneFrame
- `submit_pixel_frame(frame)` - Line ~165 - Submit PixelFrame
- `_render()` - Line ~200 - Render cycle (60 FPS)
- `_select_frame()` - Line ~250 - Priority selection logic
- `_render_zone_frame()` - Line ~350 - Zone frame rendering
- `_render_pixel_frame()` - Line ~433 - Pixel frame rendering

**Data Structures**:
- `_zone_frame_queue` - Priority queue for ZoneFrames
- `_pixel_frame_queue` - Priority queue for PixelFrames
- `_frame_history` - Recent frames (debugging)

### Animation Engine
- **File**: `src/animations/engine.py`
- **Lines**: 700+
- **Purpose**: Animation lifecycle management

**Key Methods**:
- `start(animation_id, excluded_zones, **params)` - Line ~100 - Start animation
- `stop(skip_fade)` - Line ~180 - Stop animation
- `_run_loop()` - Line ~250 - Animation generator consumer loop
- `_get_first_frame()` - Line ~330 - Build initial frame offline
- `_update_parameter()` - Line ~500 - Live parameter updates

**Key Classes**:
- `AnimationEngine` - Main class
- `AnimationFrame` - Internal frame structure

### Transition Service
- **File**: `src/services/transition_service.py`
- **Lines**: 350+
- **Purpose**: Smooth state transitions

**Key Methods**:
- `fade_out(config)` - Line ~80 - Fade to black
- `fade_in(target_frame, config)` - Line ~130 - Fade from black
- `crossfade(from_frame, to_frame, config)` - Line ~180 - Smooth transition
- `wait_for_idle()` - Line ~250 - Wait for completion

### Zone Layer
- **File**: `src/zone_layer/zone_strip.py`
- **Lines**: 250+
- **Purpose**: Zone-to-pixel mapping and rendering

**Key Methods**:
- `show_full_pixel_frame(pixels)` - Line ~120 - Main rendering method
- `apply_brightness()` - Line ~180 - Zone brightness adjustment
- `get_zone_pixels()` - Line ~200 - Get pixels for zone

**Key Class**: `ZonePixelMapper` - Maps zone IDs to pixel indices

---

## Controllers

### Main Orchestrator
- **File**: `src/controllers/led_controller/led_controller.py`
- **Lines**: 597
- **Key Methods**:
  - `change_zone(delta)` - Line ~80 - Select different zone
  - `toggle_zone_mode()` - Line ~150 - Switch STATIC/ANIMATION
  - `select_animation(delta)` - Line ~200 - Choose animation
  - `adjust_parameter(param_id, delta)` - Line ~280 - Tweak settings
  - `_handle_encoder_rotate()` - Line ~400 - Encoder input handling

### Static Mode Controller
- **File**: `src/controllers/led_controller/static_mode_controller.py`
- **Lines**: 241
- **Key Methods**:
  - `render_zone(zone_id, color, brightness)` - Line ~80 - Render static color
  - `adjust_hue(delta)` - Line ~120 - Rotate hue
  - `start_pulse()` - Line ~160 - Start pulsing effect
  - `stop_pulse()` - Line ~180 - Stop pulsing

### Animation Mode Controller
- **File**: `src/controllers/led_controller/animation_mode_controller.py`
- **Lines**: 255
- **Key Methods**:
  - `select_animation(delta)` - Line ~70 - Cycle animations
  - `adjust_param(param_id, delta)` - Line ~140 - Update parameters
  - `toggle_animation()` - Line ~190 - Start/stop animation
  - `_switch_to_selected_animation()` - Line ~220 - Switch with transition

### Zone Strip Controller
- **File**: `src/controllers/zone_strip_controller.py`
- **Lines**: 273
- **Key Methods**:
  - `submit_all_zones_frame(zones_colors, priority)` - Line ~80 - Core rendering
  - `startup_fade_in()` - Line ~140 - Startup transition
  - `fade_out_all()` - Line ~180 - Fade to black

### Other Controllers
- **PowerToggleController** - `power_toggle_controller.py` (~150 lines)
- **LampWhiteModeController** - `lamp_white_mode_controller.py` (~100 lines)
- **FramePlaybackController** - `frame_playback_controller.py` (~300 lines)
- **ControlPanelController** - `control_panel_controller.py` (~150 lines)
- **PreviewPanelController** - `preview_panel_controller.py` (~200 lines)

---

## Data Models

### Color Model
- **File**: `src/models/domain/color.py`
- **Purpose**: Color representation and conversions
- **Key Methods**:
  - `to_rgb()` - Convert to (r, g, b) tuple
  - `to_rgb_with_brightness()` - Apply brightness
  - `with_brightness()` - Create adjusted copy
  - `with_hue_adjustment()` - Rotate hue
  - `from_preset()` - Load from color presets

### Zone Models
- **File**: `src/models/domain/zone.py`
- **Purpose**: Zone configuration and state
- **Key Classes**:
  - `ZoneConfig` - Configuration (id, name, pixel_count)
  - `ZoneState` - Runtime state (color, brightness, mode)

### Enums
- **File**: `src/models/enums.py`
- **Purpose**: Typed constants
- **Key Enums**:
  - `ZoneID` - Zone identifiers
  - `AnimationID` - Available animations
  - `ColorOrder` - LED color byte order
  - `MainMode` - Top-level modes (STATIC, ANIMATION, OFF)
  - `ZoneRenderMode` - Per-zone modes

### Frames
- **File**: `src/engine/frame_manager.py` (or `src/models/domain/frame.py`)
- **Purpose**: Frame objects for rendering
- **Key Classes**:
  - `ZoneFrame` - Zones with colors
  - `PixelFrame` - Individual pixel colors
  - `PreviewFrame` - Preview panel pixels

---

## Services

### Event Bus
- **File**: `src/services/event_bus.py`
- **Purpose**: Pub/sub event system
- **Key Methods**:
  - `subscribe(event_type, handler)` - Line ~50 - Register handler
  - `publish(event)` - Line ~100 - Send event

### Zone Service
- **File**: `src/services/zone_service.py`
- **Purpose**: Zone state management
- **Key Methods**:
  - `get_all()` - Get all zones
  - `get_by_id(zone_id)` - Get specific zone
  - `get_selected_zone()` - Get currently selected zone

### Animation Service
- **File**: `src/services/animation_service.py`
- **Purpose**: Animation registry and metadata
- **Key Methods**:
  - `get_available()` - List animations
  - `get_metadata()` - Animation parameters

---

## Configuration

### Config Files (src/config/)
- `config.yaml` - Main application config
- `zones.yaml` - Zone definitions
- `hardware.yaml` - GPIO and hardware specs
- `zone_mapping.yaml` - Zone → hardware mapping
- `animations.yaml` - Animation presets
- `colors.yaml` - Color presets
- `parameters.yaml` - Animation parameters

### ConfigManager
- **File**: `src/managers/config_manager.py`
- **Lines**: 300+
- **Key Methods**:
  - `load()` - Load all configs
  - `_parse_zones()` - Parse zones and assign GPIO
  - `_parse_hardware()` - Parse hardware specs

---

## Testing

### Test Directory
- **Location**: `src/tests/`
- **Structure**:
  - `test_frame_manager.py` - FrameManager tests
  - `test_animations.py` - Animation tests
  - `test_color.py` - Color model tests
  - `domain_models/` - Domain model tests

### Running Tests
```bash
pytest src/tests/
pytest src/tests/test_frame_manager.py
```

---

## Key File Relationships

```
main_asyncio.py (entry point)
  ├─ creates ConfigManager
  ├─ creates FrameManager
  ├─ creates WS281xStrip instances
  ├─ creates ZoneStrip instances
  ├─ creates Services (AnimationEngine, TransitionService)
  └─ creates Controllers (LEDController, etc.)

LEDController (main orchestrator)
  ├─ owns AnimationEngine
  ├─ routes to StaticModeController
  ├─ routes to AnimationModeController
  └─ uses ZoneStripController

AnimationEngine
  ├─ creates animation instances
  └─ submits frames to FrameManager

FrameManager
  ├─ owns frame queues
  ├─ receives frames from (animations, transitions, static)
  ├─ selects highest priority
  └─ calls ZoneStrip.show_full_pixel_frame()

ZoneStrip
  ├─ converts zones to pixels
  ├─ calls WS281xStrip.apply_frame()
  └─ calls WS281xStrip.show()

WS281xStrip
  └─ GPIO access via rpi_ws281x library
```

---

## Quick Navigation

### I want to understand...

| Topic | Start Here |
|-------|-----------|
| How rendering works | FrameManager (frame_manager.py:200) |
| How animations run | AnimationEngine._run_loop() (engine.py:250) |
| How frames are selected | FrameManager._select_frame() (frame_manager.py:250) |
| How hardware gets data | ZoneStrip.show_full_pixel_frame() (zone_strip.py:120) |
| How GPIO works | WS281xStrip.show() (ws281x_strip.py:180) |
| How zones map to pixels | ZonePixelMapper (zone_pixel_mapper.py) |
| How transitions work | TransitionService._crossfade() (transition_service.py:180) |
| How static modes work | StaticModeController.render_zone() (static_mode_controller.py:80) |
| How input is handled | ControlPanelController (control_panel_controller.py) |
| How colors work | Color.to_rgb_with_brightness() (color.py) |

### I want to fix...

| Issue | Check |
|-------|-------|
| Animation won't start | AnimationEngine.start() (engine.py:100) + LEDController routing |
| Colors look wrong | Color.to_rgb() (color.py) + hardware color order mapping (ws281x_strip.py) |
| Frame rate dropping | FrameManager._render() cycle time (frame_manager.py:200) |
| LEDs not responding | WS281xStrip.show() (ws281x_strip.py) + GPIO initialization |
| Priority conflicts | FrameManager._select_frame() (frame_manager.py:250) |
| Zone selection broken | LEDController.change_zone() (led_controller.py:80) |

---

**Next**: [Controller Relationships](3_controller_relationships.md)
