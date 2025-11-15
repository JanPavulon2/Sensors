# Diuna Project Context

## Project Overview
Raspberry Pi LED control station with zone-based addressable RGB LED control, rotary encoder UI, and animation system. Runs asyncio event loop for non-blocking hardware polling.

**Hardware**: WS2811 (12V) addressable LEDs controlled via rpi_ws281x library. Two separate strips (preview panel + main strip), 2 rotary encoders, 4 buttons.

## Project Scope

**Primary codebase**: `src/` directory only

**Directory structure**:
```
src/
├── animations/       # Animation implementations (breathe, snake, color_fade, etc.)
├── components/       # Hardware components (ZoneStrip, PreviewPanel)
├── config/           # YAML configuration files (modular structure)
├── controllers/      # Business logic (LEDController, PreviewController)
├── managers/         # Configuration managers (ConfigManager, HardwareManager, etc.)
├── models/           # Data models and enums
├── services/         # NEW: Service layer (AnimationService, ZoneService, DataAssembler)
├── state/            # JSON state files (runtime state persistence)
├── utils/            # Utilities (logger, enum_helper, colors)
└── tests/            # Test files
```

**Excluded from context**:
- `/backups/` - old backups
- `/old_working/` - deprecated code
- `/samples/` - example files only
- `/diunaenv/` - virtual environment
- Root-level config files

## Architecture Principles

### 1. **Domain-Driven Design (NEW)**
   - **Domain Models** (`src/models/domain/`)
     - Strongly-typed dataclasses combining config + state
     - Separate concerns: Config (immutable) vs State (mutable) vs Combined (unified)
     - Files: `parameter.py`, `animation.py`, `zone.py`

   - **Service Layer** (`src/services/`)
     - `AnimationService` - High-level animation operations
     - `ZoneService` - High-level zone operations
     - `DataAssembler` - Builds domain objects from managers + state
     - `UISessionService` - UI state management (NEW)
     - `TransitionService` - State transitions (NEW)

### 2. **Modular YAML Configuration**
   - `config.yaml` - include-based main config
   - `hardware.yaml` - GPIO pins, encoders, buttons, LED strips
   - `zones.yaml` - Zone definitions (id, name, tag, pixel_count, order, reversed)
   - `animations.yaml` - Animation definitions and parameters
   - `colors.yaml` - Color preset definitions
   - `parameters.yaml` - Parameter definitions (type, min, max, step, wraps, etc.)
   - `factory_defaults.yaml` - Factory reset fallback

### 3. **Manager Pattern**
   - `ConfigManager` - Loads config via include system, initializes sub-managers
   - `HardwareManager` - Hardware configuration access
   - `AnimationManager` - Animation metadata (uses AnimationInfo dataclass)
   - `ColorManager` - Color preset management
   - `ParameterManager` - Parameter definitions and validation
   - `StateManager` - Async JSON state persistence (legacy, being replaced by services)

### 4. **Event-Driven Architecture (NEW - Pub-Sub Pattern)**
   - **EventBus** - Central event routing with pub-sub pattern
   - Hardware events → `ControlPanel` → `EventBus` (middleware) → `LEDController` (subscriber)
   - Features:
     - Priority-based handler execution
     - Per-handler filtering
     - Middleware pipeline (logging, rate limiting, guards)
     - Async/sync handler support
     - Fault tolerance
   - Files: `models/events.py`, `services/event_bus.py`, `services/middleware.py`
   - Non-blocking animations and pulsing
   - Two-mode system: STATIC (zone editing) ↔ ANIMATION (animation control)

### 5. **Type Safety with Enums**
   - `ZoneID` - Zone identifiers (FLOOR, LEFT, TOP, RIGHT, BOTTOM, LAMP, BACK, DESK)
   - `AnimationID` - Animation identifiers (BREATHE, COLOR_FADE, SNAKE, COLOR_SNAKE, etc.)
   - `ParamID` - Parameter identifiers (ZONE_COLOR_HUE, ANIM_SPEED, ANIM_INTENSITY, etc.)
   - `ParameterType` - Parameter types (COLOR, PERCENTAGE, RANGE_CUSTOM, BOOLEAN)
   - `ColorMode` - Color modes (HUE, PRESET, RGB, WHITE)

### 6. **State Persistence**
   - Location: `src/state/state.json`
   - Structure:
     ```json
     {
       "current_animation": {
         "id": "snake",
         "parameters": {
           "ANIM_SPEED": 50,
           "ANIM_PRIMARY_COLOR_HUE": 120,
           "ANIM_LENGTH": 5
         }
       },
       "zones": {
         "lamp": {
           "color": {"mode": "HUE", "hue": 0},
           "brightness": 100
         }
       },
       "ui_session": { ... }
     }
     ```

## Key Design Patterns

### Domain Model Pattern (NEW)
```python
# OLD WAY (dict-based)
speed = state["animation"]["speed"]
state["animation"]["speed"] = 80

# NEW WAY (domain objects)
snake = animation_service.get_animation(AnimationID.SNAKE)
speed = snake.get_param_value(ParamID.ANIM_SPEED)
animation_service.adjust_parameter(AnimationID.SNAKE, ParamID.ANIM_SPEED, delta=1)
```

### Service Layer Usage
```python
# Zone operations
zone = zone_service.get_zone(ZoneID.LAMP)
rgb = zone.get_rgb()  # Color with brightness applied
zone_service.set_brightness(ZoneID.LAMP, 50)

# Animation operations
anim = animation_service.get_current()
animation_service.start(AnimationID.SNAKE)
animation_service.adjust_parameter(AnimationID.SNAKE, ParamID.ANIM_SPEED, delta=1)
```

## Important Files

- `src/main_asyncio.py` - Main entry point
- `src/controllers/led_controller.py` - Central business logic
- `src/services/data_assembler.py` - Builds domain objects
- `src/models/domain/*.py` - Domain models
- `src/models/enums.py` - All enum definitions
- `src/models/color.py` - Color model implementation
- `CLAUDE.md` - Detailed technical documentation (being updated)

## Migration Status

**Completed Migrations**:

1. **Domain-Driven Design** (✅ Complete)
   - ✅ Domain models created
   - ✅ Service layer implemented
   - ✅ Services integrated into LEDController
   - ✅ Dict-based code replaced with domain objects

2. **Event-Driven Architecture** (✅ Complete - October 2024)
   - ✅ EventBus infrastructure created (events.py, event_bus.py, middleware.py)
   - ✅ ControlPanel refactored (callbacks → events)
   - ✅ LEDController integrated with event handlers
   - ✅ Hardware config updated (zone_selector → selector)
   - ✅ Comprehensive test suite (test_event_bus.py)
   - **Benefits**: Decoupled architecture, extensible for Web/MQTT, middleware pipeline, testable
   - **Note**: All existing methods unchanged - drop-in replacement for callbacks

## Development Focus

All development work focuses on the `src/` directory structure. See [CLAUDE.md](../CLAUDE.md) for detailed technical documentation and patterns.