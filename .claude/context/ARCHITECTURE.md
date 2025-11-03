# Diuna LED Control System - Architecture Documentation

**Version**: 0.1
**Last Updated**: 2025-11-02
**Target Audience**: AI Agents & Developers

This document provides a comprehensive overview of the Diuna LED control system architecture. Read this before starting any development work to understand the codebase structure, design patterns, and architectural decisions.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Layers](#2-architecture-layers)
3. [Directory Structure](#3-directory-structure)
4. [Core Components](#4-core-components)
5. [Design Patterns](#5-design-patterns)
6. [Data Flow](#6-data-flow)
7. [State Management](#7-state-management)
8. [Configuration System](#8-configuration-system)
9. [Animation System](#9-animation-system)
10. [Hardware Integration](#10-hardware-integration)
11. [Critical Constraints](#11-critical-constraints)
12. [Extension Points](#12-extension-points)

---

## 1. System Overview

### 1.1 Project Description
Raspberry Pi LED control station with zone-based addressable RGB LED control, rotary encoder UI, and animation system. Runs asyncio event loop for non-blocking hardware polling.

### 1.2 Key Statistics
- **Total Lines**: 8,301 lines of Python (excluding tests)
- **Main Controller**: 1,181 lines (LEDController)
- **Modules**: 50+ Python files
- **Animations**: 6 built-in animations
- **LED Zones**: 8 configurable zones (89 pixels total)

### 1.3 Technologies
- **Runtime**: Python 3 + asyncio
- **LED Control**: rpi_ws281x (WS2811/WS2812B)
- **GPIO**: RPi.GPIO
- **Config**: YAML (modular includes)
- **State**: JSON persistence

---

## 2. Architecture Layers

The system follows a **5-layer architecture** with clear separation of concerns:

```
┌──────────────────────────────────────────────────────┐
│  Layer 4: Infrastructure (Config, Events, Logging)   │
├──────────────────────────────────────────────────────┤
│  Layer 3: Application (Controllers, Orchestration)   │
├──────────────────────────────────────────────────────┤
│  Layer 2: Domain (Models, Services, Business Logic)  │
├──────────────────────────────────────────────────────┤
│  Layer 1: Hardware Abstraction (Components)          │
├──────────────────────────────────────────────────────┤
│  Layer 0: GPIO Infrastructure (Pin Management)       │
└──────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────┐
│  Hardware Drivers (RPi.GPIO, rpi_ws281x)             │
└──────────────────────────────────────────────────────┘
```

### 2.0 Layer 0: GPIO Infrastructure Layer
**Location**: `managers/GPIOManager.py`

**Purpose**: Centralized GPIO resource management and conflict detection.

**Component**: `GPIOManager`

**Responsibilities**:
- Initialize RPi.GPIO library (BCM mode, disable warnings)
- Track all registered GPIO pins (prevent conflicts)
- Provide pin registration API for HAL components
- Clean up all GPIO pins on shutdown

**Key Features**:
- **Pin Registry**: Dict mapping pin number → component name
- **Conflict Detection**: Raises `ValueError` if pin already registered
- **Logging**: Comprehensive logging of all pin allocations
- **Typed API**: Uses `GPIOPullMode` and `GPIOInitialState` enums (no RPi.GPIO types exposed)

**API Methods**:
```python
gpio_manager = GPIOManager()

# Register input pins (buttons, encoders)
gpio_manager.register_input(
    pin=22,
    component="Button(22)",
    pull_mode=GPIOPullMode.PULL_UP
)

# Register output pins (generic digital outputs)
gpio_manager.register_output(
    pin=17,
    component="StatusLED",
    initial=GPIOInitialState.LOW
)

# Register WS281x pins (DMA-based, tracking only)
gpio_manager.register_ws281x(
    pin=18,
    component="ZoneStrip(GPIO18,45px)"
)

# Get registry for debugging
registry = gpio_manager.get_registry()  # {22: "Button(22)", ...}

# Log all pin allocations
gpio_manager.log_registry()

# Cleanup all pins on shutdown
gpio_manager.cleanup()
```

**Why This Layer Exists**:
- **Before**: Each component directly called `GPIO.setup()`, no conflict detection
- **After**: Centralized registration prevents pin conflicts, provides debugging visibility
- **Architecture**: Infrastructure concern, not domain or HAL logic

**Initialization Order** (critical):
```python
# In main_asyncio.py
gpio_manager = GPIOManager()  # 1. FIRST - initialize GPIO library
led = LEDController(..., gpio_manager)  # 2. Register LED strips
control_panel = ControlPanel(..., gpio_manager)  # 3. Register encoders/buttons
gpio_manager.log_registry()  # 4. Log all pin allocations
```

---

### 2.1 Layer 1: Hardware Abstraction Layer (HAL)
**Location**: `components/`

**Purpose**: Abstract GPIO hardware into clean, testable interfaces.

**Components**:
- `Button`: Debounced button input
- `RotaryEncoder`: Rotation + click detection
- `ControlPanel`: Hardware physical entity containing: 2x encoders with click (selector and modulator), 4x buttons, preview panel
- `ZoneStrip`: WS281x LED strip with zone-based addressing
- `PreviewPanel`: 8-LED preview strip controller
- `KeyboardInputAdapter`: Computer keyboard input (dual backend: evdev/stdin)

**Key Pattern**: **Facade** - Simplifies complex hardware APIs

**Rule**: This layer contains NO business logic, only hardware abstraction.

**GPIO Registration**: All components receive `GPIOManager` via constructor and register their pins during initialization.

#### ControlPanel - Physical & Logical Entity
The hardware components (2 encoders + 4 buttons + preview panel (cjmcu-8)) are assembled in a physical box/case and are inseparable and unmodifiable.

**Implication**: If you need to add new input hardware (e.g., another button or encoder for a different purpose), its events will **NOT** be handled inside ControlPanel code. ControlPanel is a fixed, closed system representing the physical control panel.

**New input sources** should publish events directly to EventBus from their own modules, not through ControlPanel.

#### KeyboardInputAdapter - Dual Backend Architecture
**Location**: `components/keyboard/`

**Purpose**: Provide computer keyboard input as an alternative/additional input source. Does NOT extend ControlPanel (which represents fixed physical hardware).

**Dual Backend Strategy**:
1. **EvdevKeyboardAdapter** - Physical keyboard via Linux evdev (`/dev/input/event*`)
   - Direct hardware access
   - Full modifier key support (Ctrl, Shift, Alt)
   - Async event reading
   - **STATUS**: Currently NOT working - has race condition in evdev library's async_read_loop(). Needs fixing.

2. **StdinKeyboardAdapter** - Terminal stdin input (SSH/VSCode/local terminal)
   - Works over SSH without X11
   - Escape sequence handling (arrow keys)
   - Ctrl+Key detection via control codes
   - Shift detection via uppercase characters
   - **STATUS**: WORKING - fully functional for development/testing

**Auto-Selection Logic**:
```python
# Try evdev first (1 second timeout)
# If timeout → keyboard found → continue with evdev
# If returns False → no device → fallback to stdin
```

**Event Publishing**:
```python
# Publishes KeyboardKeyPressEvent to EventBus
event = KeyboardKeyPressEvent(
    key="A",                    # Normalized key name
    modifiers=["CTRL", "SHIFT"] # Optional modifiers list
)
await event_bus.publish(event)
```

**Key Features**:
- Modifier tracking (Ctrl, Shift, Alt)
- Arrow key support (UP, DOWN, LEFT, RIGHT)
- Special keys (ENTER, TAB, SPACE, BACKSPACE, ESCAPE)
- Async-native (non-blocking)

**Known Limitations**:
- **Evdev**: Race condition bug in library, currently disabled
- **Stdin**: Requires 2x Ctrl+C to exit (executor thread limitation)
- **Stdin**: Alt key not reliably detected (terminal limitation)
- **Stdin**: VSCode keyboard shortcuts override Ctrl combinations
- **Stdin**: Shift detection based on uppercase (won't work with Caps Lock)

**File Structure**:
```
components/keyboard/
├── __init__.py                    # Exports KeyboardInputAdapter
├── keyboard_input_adapter.py      # Main adapter with auto-selection
├── evdev_keyboard_adapter.py      # Physical keyboard backend (NOT WORKING)
└── stdin_keyboard_adapter.py      # Terminal stdin backend (WORKING)
```

**Usage**:
```python
# In main_asyncio.py
keyboard_adapter = KeyboardInputAdapter(event_bus)
keyboard_task = asyncio.create_task(keyboard_adapter.run())

# In LEDController
event_bus.subscribe(
    EventType.KEYBOARD_KEYPRESS,
    self.handle_keyboard_keypress,
    priority=10
)
```

---

### 2.2 Layer 2: Domain Layer
**Location**: `models/domain/`, `services/`

**Purpose**: Core business entities, rules, and domain services.

**Architecture**: **Domain-Driven Design (DDD)**

#### Domain Model Pattern
Each domain entity has 3 representations:

1. **Config** (frozen dataclass) - Immutable configuration from YAML
2. **State** (mutable dataclass) - Runtime state from JSON
3. **Combined** (aggregate root) - Config + State + operations

**Example: Zone Domain**
```python
@dataclass(frozen=True)
class ZoneConfig:
    """Immutable zone configuration from zones.yaml"""
    id: ZoneID
    display_name: str
    pixel_count: int
    enabled: bool
    start_index: int
    end_index: int

@dataclass
class ZoneState:
    """Mutable zone state from state.json"""
    id: ZoneID
    color: Color

class ZoneCombined:
    """Aggregate root - combines config + state"""
    def __init__(self, config: ZoneConfig, state: ZoneState):
        self.config = config
        self.state = state
        self.parameters: Dict[ParamID, ParameterCombined]

    def get_rgb(self) -> Tuple[int, int, int]:
        """Returns RGB with brightness applied"""
        brightness = self.parameters[ParamID.ZONE_BRIGHTNESS].value
        return self.state.color.to_rgb_with_brightness(brightness)
```

#### Domain Services
Services provide CRUD operations with automatic persistence using the **Service Pattern**:

- `ZoneService`: Zone operations with auto-save
- `AnimationService`: Animation operations with auto-save
- `UISessionService`: UI state management
- `TransitionService`: LED transition orchestration

**Key Pattern**: **Service Pattern** - Business logic services that coordinate domain objects and persistence

**Example**:
```python
class ZoneService:
    def set_color(self, zone_id: ZoneID, color: Color):
        """Update zone color and auto-save"""
        zone = self._by_id[zone_id]
        zone.state.color = color
        self.save()  # Auto-save via DataAssembler
```

#### DataAssembler - Repository Pattern
**DataAssembler** implements the **Repository Pattern** - it's the **only component** responsible for:
- Loading raw state from JSON files
- Saving state back to JSON files
- Building domain objects from config + state
- Persisting domain object state

**See section 4.6 for detailed DataAssembler documentation.**

---

### 2.3 Layer 3: Application Layer
**Location**: `controllers/`

**Purpose**: Orchestrate domain services and implement use cases.

**Main Controller**: `LEDController` (1,181 lines)

#### State Machine Architecture
The system operates in **two main modes**:

1. **STATIC Mode** (default)
   - Zone editing
   - Selector encoder → change zone
   - Modulator encoder → adjust parameter (hue, preset, brightness)

2. **ANIMATION Mode**
   - Animation control
   - Selector encoder → select animation
   - Modulator encoder → adjust animation parameter (speed, intensity)

**Mode Toggle**: BTN4 switches between modes

#### Key State Variables
```python
class LEDController:
    # Mode state
    main_mode: MainMode              # STATIC or ANIMATION
    edit_mode: bool                  # Enable/disable editing
    lamp_white_mode: bool            # Desk lamp mode

    # Selection state
    current_zone_index: int          # Selected zone (STATIC mode)
    current_param: ParamID           # Active parameter

    # Services (from domain layer)
    zone_service: ZoneService
    animation_service: AnimationService
    ui_session: UISessionService
```

#### Critical Methods
- `handle_selector_rotation(delta)`: Context-sensitive zone/animation selection
- `handle_modulator_rotation(delta)`: Context-sensitive parameter adjustment
- `toggle_main_mode()`: Switch STATIC ↔ ANIMATION
- `quick_lamp_white()`: Desk lamp toggle (BTN2)
- `power_toggle()`: All zones ON/OFF with smooth transitions
- `start_animation()`, `stop()`: Animation lifecycle

---

### 2.4 Layer 4: Infrastructure Layer
**Location**: `managers/`, `services/event_bus.py`, `utils/`

**Purpose**: Configuration, event routing, persistence, utilities.

**Key Components**:

#### ConfigManager
- Loads modular YAML files via include system
- Initializes sub-managers (HardwareManager, ColorManager, etc.)
- Calculates zone pixel indices

#### DataAssembler (see section 4.6)
- Implements Repository Pattern
- Loads/saves state.json
- Builds domain objects from config + state
- Single source of truth for persistence

#### EventBus
- Pub-sub event routing
- Priority-based handler execution
- Per-handler filtering
- Middleware support (logging, rate limiting)
- Fault tolerance (handler crashes don't stop others)

---

## 3. Directory Structure

```
src/
├── main_asyncio.py              # Entry point
│
├── animations/                  # Animation implementations
│   ├── base.py                 # BaseAnimation abstract class
│   ├── engine.py               # AnimationEngine (lifecycle manager)
│   ├── breathe.py              # Sine wave breathing
│   ├── color_fade.py           # Rainbow cycling
│   ├── snake.py                # Sequential chase
│   ├── color_snake.py          # Rainbow snake
│   ├── matrix.py               # Matrix-style drops
│   └── color_cycle.py          # Color cycling
│
├── components/                  # Hardware abstraction layer
│   ├── button.py
│   ├── rotary_encoder.py
│   ├── control_module.py       # Hardware event publisher (PHYSICAL + LOGICAL)
│   ├── zone_strip.py           # Main LED strip
│   ├── preview_panel.py        # Preview strip
│   └── keyboard/               # Keyboard input adapters
│       ├── __init__.py
│       ├── keyboard_input_adapter.py
│       ├── evdev_keyboard_adapter.py    # NOT WORKING
│       └── stdin_keyboard_adapter.py    # WORKING
│
├── config/                      # YAML configuration
│   ├── config.yaml             # Main (with includes)
│   ├── hardware.yaml           # GPIO pins, LEDs
│   ├── zones.yaml              # Zone definitions
│   ├── colors.yaml             # Color presets
│   ├── animations.yaml         # Animation metadata
│   ├── parameters.yaml         # Parameter definitions
│   └── factory_defaults.yaml  # Fallback defaults
│
├── controllers/                 # Application layer
│   ├── led_controller.py       # Main state machine
│   └── preview_controller.py   # Preview orchestration
│
├── managers/                    # Configuration management
│   ├── config_manager.py       # Central config loader
│   ├── hardware_manager.py
│   ├── animation_manager.py
│   ├── color_manager.py
│   └── parameter_manager.py
│
├── models/                      # Data models
│   ├── color.py                # Color class (HUE/PRESET/RGB)
│   ├── enums.py                # System-wide enums (includes LogCategory.EVENT)
│   ├── events.py               # Event classes (includes KeyboardKeyPressEvent)
│   ├── transition.py           # Transition configs
│   │
│   └── domain/                 # Domain models (DDD)
│       ├── zone.py
│       ├── animation.py
│       └── parameter.py
│
├── services/                    # Domain services
│   ├── event_bus.py            # Pub-sub system
│   ├── data_assembler.py       # Repository pattern (state persistence)
│   ├── zone_service.py         # Service pattern (zone business logic)
│   ├── animation_service.py    # Service pattern (animation business logic)
│   ├── ui_session_service.py   # Service pattern (UI state management)
│   ├── transition_service.py   # Service pattern (transition orchestration)
│   └── middleware.py
│
├── state/
│   └── state.json              # Persisted runtime state
│
└── utils/                       # Utilities
    ├── logger.py               # Structured logging
    ├── colors.py               # Color conversions
    ├── enum_helper.py
    └── cleanup.py
```

---

## 4. Core Components

### 4.1 LEDController (State Machine)

**Responsibility**: Central orchestrator for all LED operations.

**Key Responsibilities**:
1. Handle hardware events (encoders, buttons)
2. Manage mode transitions (STATIC ↔ ANIMATION)
3. Coordinate domain services
4. Control animation lifecycle
5. Manage edit mode pulsing
6. Handle power toggle with transitions

**Event Handling Pattern**:
```python
# Registration (in __init__)
event_bus.subscribe(
    EventType.ENCODER_ROTATE,
    lambda e: self.handle_selector_rotation(e.delta),
    filter_fn=lambda e: e.source == EncoderSource.SELECTOR
)

# Handler
async def handle_selector_rotation(self, delta: int):
    if not self.edit_mode:
        return

    if self.main_mode == MainMode.STATIC:
        self.change_zone(delta)
    elif self.main_mode == MainMode.ANIMATION:
        self.change_animation(delta)
```

---

### 4.2 EventBus (Pub-Sub System)

**Responsibility**: Decouple hardware events from business logic.

**Features**:
- Priority-based handler execution
- Per-handler event filtering
- Middleware pipeline
- Fault isolation (one handler crash doesn't affect others)

**Usage**:
```python
# Publish
event_bus.publish(EncoderRotateEvent(
    source=EncoderSource.SELECTOR,
    delta=1
))

# Subscribe with filter
event_bus.subscribe(
    EventType.ENCODER_ROTATE,
    handler=my_handler,
    filter_fn=lambda e: e.source == EncoderSource.MODULATOR,
    priority=10
)

# Middleware
def log_middleware(event: Event, next_handler):
    log.debug(f"Event: {event.type}")
    return next_handler(event)

event_bus.add_middleware(log_middleware)
```

---

### 4.3 Color System

**Responsibility**: Unified color representation across the system.

**Color Modes**:
1. **HUE** - Hue value (0-360°) with full saturation
2. **PRESET** - Named presets (e.g., "warm_white", "ocean")
3. **RGB** - Direct RGB values (0-255)
4. **WHITE** - Special white mode

**Immutable Pattern**:
```python
# Adjustment returns NEW Color instance
color = Color.from_hue(180)
new_color = color.adjust_hue(10)  # Returns new Color with hue=190

# Rendering
r, g, b = color.to_rgb()
```

**State Persistence**:
```python
# Save
color_dict = color.to_dict()
# {"mode": "PRESET", "preset_name": "warm_white"}

# Load
color = Color.from_dict(color_dict, color_manager)
```

**CRITICAL RULE**: Always use `Color.to_rgb()` for rendering. Never render from preset indices directly (loses hue adjustments).

---

### 4.4 AnimationEngine

**Responsibility**: Manage animation lifecycle and frame consumption.

**Architecture**: Async generator pattern

**Animation Base Class**:
```python
class BaseAnimation(ABC):
    def __init__(self, zones: Dict, speed: int, excluded_zones: List[str]):
        self.zones = zones
        self.speed = speed  # 1-100
        self.running = True
        self.active_zones = [z for z in zones if z not in excluded_zones]

    @abstractmethod
    async def run(self) -> AsyncIterator[Tuple[str, int, int, int]]:
        """Yield (zone_name, r, g, b) frames"""
        while self.running:
            # CRITICAL: Recalculate timing INSIDE loop
            frame_delay = self._calculate_frame_delay()

            for zone_name in self.active_zones:
                r, g, b = calculate_color(...)
                yield (zone_name, r, g, b)

            await asyncio.sleep(frame_delay)
```

**Engine Usage**:
```python
# Start animation
await animation_engine.start(
    animation_tag="breathe",
    zones=zones_dict,
    speed=50,
    excluded_zones=["lamp"]
)

# Update parameter (live)
animation_engine.update_param("speed", 80)

# Stop animation
await animation_engine.stop()
```

---

### 4.5 ZoneStrip (Hardware Facade)

**Responsibility**: Simplify WS281x LED strip control with zone-based API.

**Underlying Complexity**:
```python
# Raw rpi_ws281x API
strip = PixelStrip(
    num=89,                      # Total pixels
    pin=18,                      # GPIO number
    freq_hz=800000,              # 800kHz
    dma=10,                      # DMA channel
    invert=False,                # Signal polarity
    brightness=255,              # Global brightness
    channel=0,                   # PWM channel
    strip_type=ws.WS2811_STRIP_BRG  # Color order
)
for i in range(89):
    strip.setPixelColor(i, Color(r, g, b))
strip.show()
```

**Simplified Facade**:
```python
# ZoneStrip API
zone_strip.set_zone_color("lamp", 255, 200, 150)
zone_strip.set_multiple_zones({
    "lamp": (255, 200, 150),
    "top": (0, 150, 255)
})
zone_strip.clear_zone("lamp")
zone_strip.clear_all()
```

**CRITICAL**: Zone dict format is `{"zone_name": [start_index, end_index]}` where indices are 0-based pixel positions.

---

### 4.6 DataAssembler (Repository Pattern)

**Location**: `services/data_assembler.py`

**Pattern**: **Repository Pattern** - The single source of truth for data persistence

**Responsibility**: DataAssembler is the **ONLY** component that:
- Reads/writes state.json file directly
- Knows about JSON structure and serialization
- Builds domain objects from raw config + state data
- Persists domain object state back to JSON

**Architecture**:
```python
class DataAssembler:
    def __init__(self, config_manager: ConfigManager, state_path: Path):
        self.config_manager = config_manager
        self.state_path = state_path
        self.color_manager = config_manager.color_manager
        self.parameter_manager = config_manager.parameter_manager
        self.animation_manager = config_manager.animation_manager
```

**Key Methods**:

#### Loading State
```python
def load_state(self) -> dict:
    """Load raw state from JSON file"""
    # Returns dict with structure:
    # {
    #   "zones": {...},
    #   "current_animation": {...},
    #   "ui_session": {...}
    # }
```

#### Building Domain Objects
```python
def build_zones(self) -> List[ZoneCombined]:
    """
    Build zone domain objects from config + state

    Process:
    1. Load state.json → get zone state data
    2. Load zones.yaml via ConfigManager → get zone configs
    3. For each zone:
       a. Extract ZoneConfig from YAML (id, name, pixel_count, enabled, indices)
       b. Extract ZoneState from JSON (color, brightness)
       c. Build ParameterCombined objects (with defaults if missing)
       d. Create ZoneCombined(config, state, parameters)
    4. Return list of ZoneCombined objects

    CRITICAL: Uses config_manager.get_all_zones() to include disabled zones
              (preserves pixel indices for hardware mapping)
    """

def build_animations(self) -> List[AnimationCombined]:
    """
    Build animation domain objects from config + state

    Process:
    1. Load state.json → get current animation + parameters
    2. Load animations.yaml → get available animations
    3. For each animation:
       a. Create AnimationConfig (id, tag, parameters list)
       b. Create AnimationState (enabled, parameter values)
       c. Build ParameterCombined objects for all anim parameters
       d. Create AnimationCombined(config, state, parameters)
    4. Return list (one AnimationCombined marked as enabled)
    """
```

#### Saving Domain State
```python
def save_zone_state(self, zones: List[ZoneCombined]) -> None:
    """
    Save zone state to state.json

    Process:
    1. Load current state.json
    2. For each ZoneCombined:
       - Extract tag (lowercase zone ID)
       - Serialize color via color.to_dict()
       - Extract brightness from parameters
       - Update state["zones"][tag] = {...}
    3. Write entire state.json back to disk
    """

def save_animation_state(self, animations: List[AnimationCombined]) -> None:
    """
    Save current animation state to state.json

    Process:
    1. Find enabled animation (state.enabled = True)
    2. Extract parameter values from parameters dict
    3. Update state["current_animation"] = {id, parameters}
    4. Write state.json
    """

def save_partial_state(self, updates: dict) -> None:
    """
    Update ui_session section without touching zones/animations

    Used by UISessionService for:
    - edit_mode_on
    - lamp_white_mode_on
    - selected_zone_index
    - active_parameter
    - main_mode
    """
```

**Why Repository Pattern?**
- **Single Responsibility**: Only DataAssembler knows about JSON structure
- **Testability**: Easy to mock for testing services
- **Consistency**: All persistence logic in one place
- **Flexibility**: Easy to swap JSON for SQLite/database later

**Service Pattern vs Repository Pattern**:
- **Services** (`ZoneService`, `AnimationService`) contain **business logic** and coordinate domain operations
- **DataAssembler** (Repository) contains **persistence logic** and handles data storage/retrieval
- Services **use** DataAssembler for persistence, never access state.json directly

**Example Interaction**:
```python
# Service uses Repository for persistence
class ZoneService:
    def __init__(self, assembler: DataAssembler):
        self.assembler = assembler  # Repository
        self.zones = assembler.build_zones()  # Load via Repository

    def set_color(self, zone_id: ZoneID, color: Color):
        zone = self._by_id[zone_id]
        zone.state.color = color  # Business logic
        self.save()  # Delegate to Repository

    def save(self):
        self.assembler.save_zone_state(self.zones)  # Repository handles JSON
```

---

## 5. Design Patterns

### 5.1 Event-Driven Architecture
**Implementation**: EventBus + ControlPanel

**Flow**:
```
Hardware GPIO → ControlPanel.poll() → Publish Event
    ↓
EventBus (with middleware)
    ↓
LEDController handlers
    ↓
Domain Services (with auto-save)
    ↓
Hardware Output (ZoneStrip)
```

**Benefits**:
- Decoupled components
- Easy to add new input sources (web API, MQTT) - publish directly to EventBus
- Testable in isolation
- Cross-cutting concerns via middleware

---

### 5.2 Domain-Driven Design (DDD)
**Pattern**: Config + State + Combined

**Separation of Concerns**:
- **Config** (immutable) - from YAML files
- **State** (mutable) - from state.json
- **Combined** (aggregate root) - config + state + operations

**Benefits**:
- Clear ownership of data
- Type-safe operations (enums for IDs)
- Validation at domain layer
- Single source of truth for each concern

---

### 5.3 Repository Pattern
**Implementation**: DataAssembler

**Responsibilities**:
- Abstract data persistence details
- Build domain objects from raw data
- Save domain object state
- Single point of access to state.json

**Benefits**:
- Centralized persistence logic
- Easy to swap storage backend
- Testable (mock the repository)

---

### 5.4 Service Pattern
**Implementation**: ZoneService, AnimationService, UISessionService, TransitionService

**Responsibilities**:
- Coordinate domain objects
- Implement business logic
- Delegate persistence to Repository
- Provide high-level operations

**Benefits**:
- Separation of business logic from persistence
- Automatic save after operations
- Clear API for controllers

---

### 5.5 Strategy Pattern (Color Modes)
**Implementation**: Color class with multiple modes

```python
class Color:
    mode: ColorMode  # HUE, PRESET, RGB, WHITE

    def to_rgb(self) -> Tuple[int, int, int]:
        if self.mode == ColorMode.HUE:
            return hue_to_rgb(self._hue)
        elif self.mode == ColorMode.PRESET:
            return self.color_manager.get_preset_rgb(self._preset_name)
        elif self.mode == ColorMode.RGB:
            return self._rgb
        elif self.mode == ColorMode.WHITE:
            return self._get_white_rgb()
```

**Benefits**:
- Flexible color representation
- Automatic conversions
- Immutable pattern (returns new instances)

---

### 5.6 Async Generator Pattern (Animations)
**Implementation**: BaseAnimation.run()

```python
async def run(self) -> AsyncIterator[Tuple[str, int, int, int]]:
    while self.running:
        frame_delay = self._calculate_frame_delay()

        for zone_name in self.active_zones:
            r, g, b = calculate_color(...)
            yield (zone_name, r, g, b)

        await asyncio.sleep(frame_delay)
```

**Consumption**:
```python
async for zone_name, r, g, b in animation.run():
    strip.set_zone_color(zone_name, r, g, b)
```

**Benefits**:
- Non-blocking frame generation
- Clean separation (animation logic vs rendering)
- Live parameter updates

---

### 5.7 Facade Pattern (Hardware Abstraction)
**Implementation**: ZoneStrip, PreviewPanel, ControlPanel

**Benefits**:
- Simplifies complex APIs
- Hides implementation details
- Testable (mock the facade)

---

## 6. Data Flow

### 6.1 User Input Flow
```
User Rotates Encoder
    ↓
GPIO pins change (CLK/DT)
    ↓
RotaryEncoder.read() → delta (-1 or +1)
    ↓
ControlPanel.poll() detects change
    ↓
Publish EncoderRotateEvent(SELECTOR, delta=1)
    ↓
EventBus routes to LEDController.handle_selector_rotation(1)
    ↓
[STATIC mode] change_zone(1)
    ↓
ZoneService.get_zone(new_zone_id)
    ↓
Update preview panel
    ↓
UISessionService.save(current_zone_index=...)
    ↓
DataAssembler.save_partial_state({"selected_zone_index": ...})
```

### 6.2 Color Update Flow
```
User Rotates Modulator (delta=10)
    ↓
LEDController.handle_modulator_rotation(10)
    ↓
[current_param = ZONE_COLOR_HUE]
    ↓
_adjust_zone_parameter(zone_id, 10)
    ↓
zone.state.color.adjust_hue(10) → new Color
    ↓
ZoneService.set_color(zone_id, new_color)
    ↓
ZoneService.save() → DataAssembler.save_zone_state()
    ↓
DataAssembler writes to state.json
    ↓
zone_service.get_rgb(zone_id)
    ↓
strip.set_zone_color(zone_tag, r, g, b)
    ↓
Hardware shows updated color
```

### 6.3 Animation Flow
```
User Clicks Selector (ANIMATION mode)
    ↓
LEDController.handle_selector_click()
    ↓
start_animation()
    ↓
animation_service.get_current().build_params_for_engine()
    ↓
AnimationEngine.start(anim_tag, **params)
    ↓
Create instance: BreatheAnimation(zones, speed=50)
    ↓
Launch task: asyncio.create_task(_run_loop())
    ↓
Consume frames: async for (zone, r, g, b) in animation.run()
    ↓
strip.set_zone_color(zone, r, g, b)
    ↓
[Live update] user rotates modulator
    ↓
animation.update_param('speed', 80)
    ↓
Animation reads self.speed in next frame
```

### 6.4 State Persistence Flow
```
User changes brightness
    ↓
ZoneService.adjust_parameter(zone_id, ZONE_BRIGHTNESS, delta)
    ↓
zone.parameters[ZONE_BRIGHTNESS].adjust(delta)
    ↓
ZoneService.save()
    ↓
DataAssembler.save_zone_state(zones)
    ↓
DataAssembler.load_state() → read current JSON
    ↓
Build JSON: {"zones": {"lamp": {"brightness": 75}}}
    ↓
DataAssembler.save_state(updated_json)
    ↓
Write to state/state.json
    ↓
[On restart] DataAssembler.load_state()
    ↓
DataAssembler.build_zones() → reconstruct domain objects
    ↓
ZoneService initialized with restored state
```

---

## 7. State Management

### 7.1 State File Structure
**Location**: `state/state.json`

```json
{
  "zones": {
    "lamp": {
      "color": {"mode": "PRESET", "preset_name": "warm_white"},
      "brightness": 100
    },
    "top": {
      "color": {"mode": "HUE", "hue": 240},
      "brightness": 75
    }
  },
  "current_animation": {
    "id": "BREATHE",
    "parameters": {
      "ANIM_SPEED": 50,
      "ANIM_INTENSITY": 80
    }
  },
  "ui_session": {
    "main_mode": "STATIC",
    "edit_mode_on": true,
    "lamp_white_mode_on": false,
    "active_parameter": "ZONE_COLOR_HUE",
    "selected_zone_index": 1
  }
}
```

### 7.2 Persistence Strategy
**Auto-save on every user action**:
- No periodic save loop
- Services handle persistence transparently via DataAssembler
- Three state categories:
  1. Zone state → `ZoneService.save()` → `DataAssembler.save_zone_state()`
  2. Animation state → `AnimationService.save()` → `DataAssembler.save_animation_state()`
  3. UI session → `UISessionService.save()` → `DataAssembler.save_partial_state()`

### 7.3 State Loading
```python
# Application startup
1. ConfigManager.load() → load all YAML files
2. DataAssembler.build_zones() → ZoneCombined objects
3. DataAssembler.build_animations() → AnimationCombined objects
4. Services initialized with domain objects
5. LEDController restores UI session state
```

---

## 8. Configuration System

### 8.1 Modular YAML Architecture
**Main file**: `config/config.yaml`
```yaml
include:
  - hardware.yaml
  - zones.yaml
  - colors.yaml
  - animations.yaml
  - parameters.yaml
```

**ConfigManager** loads and merges all files into single config dict.

### 8.2 Configuration Sections

#### hardware.yaml
```yaml
hardware:
  encoders:
    selector: {clk: 5, dt: 6, sw: 13}
    modulator: {clk: 16, dt: 20, sw: 21}
  buttons: [22, 26, 23, 24]
  leds:
    preview: {gpio: 19, count: 8, color_order: GRB}
    strip: {gpio: 18, count: 89, color_order: BRG}
```

#### zones.yaml (Current Configuration)
```yaml
zones:
  - id: FLOOR
    name: Floor
    tag: floor
    pixel_count: 18
    enabled: true
    order: 1
    reversed: false

  - id: LEFT
    name: Left
    tag: left
    pixel_count: 4
    enabled: false
    order: 2

  - id: TOP
    name: Top
    tag: top
    pixel_count: 3
    enabled: true
    order: 3

  - id: RIGHT
    name: Right
    tag: right
    pixel_count: 4
    enabled: true
    order: 4

  - id: BOTTOM
    name: Bottom
    tag: bottom
    pixel_count: 3
    enabled: true
    order: 5

  - id: LAMP
    name: Lamp
    tag: lamp
    pixel_count: 19
    enabled: true
    order: 6

  - id: DESK
    name: Desk
    tag: desk
    pixel_count: 26
    enabled: true
    order: 7
    reversed: false

  - id: BACK
    name: Back
    tag: back
    pixel_count: 12
    enabled: true
    order: 8
    reversed: true
```

**Total pixels**: 89 (18+4+3+4+3+19+26+12)

**Index Calculation** (automatic by ConfigManager):
- FLOOR: [0-17] (18 pixels)
- LEFT: [18-21] (4 pixels, disabled → renders black)
- TOP: [22-24] (3 pixels)
- RIGHT: [25-28] (4 pixels)
- BOTTOM: [29-31] (3 pixels)
- LAMP: [32-50] (19 pixels)
- DESK: [51-76] (26 pixels)
- BACK: [77-88] (12 pixels, reversed)

#### colors.yaml
```yaml
presets:
  warm_white: [255, 200, 150]
  red: [255, 0, 0]
  ocean: [0, 150, 255]

preset_order:
  - warm_white
  - red
  - orange
```

#### parameters.yaml
```yaml
zone_parameters:
  ZONE_BRIGHTNESS:
    type: PERCENTAGE
    default: 100
    min: 0
    max: 100
    step: 5
    unit: "%"
    wraps: false

animation_base_parameters:
  ANIM_SPEED:
    type: PERCENTAGE
    default: 50
    min: 1
    max: 100
    step: 5
```

---

## 9. Animation System

### 9.1 Available Animations
1. **Breathe**: Sine wave brightness pulsing (per-zone colors)
2. **ColorFade**: Rainbow hue cycling (all zones sync)
3. **Snake**: Sequential zone chase (solid color)
4. **ColorSnake**: Sequential chase with rainbow gradient
5. **Matrix**: Matrix-style rain drops
6. **ColorCycle**: Smooth color cycling

### 9.2 Animation Parameters
**Base parameters** (all animations):
- `ANIM_SPEED`: 1-100 (affects frame delay)

**Optional parameters**:
- `ANIM_INTENSITY`: 1-100 (breathe depth, matrix brightness)
- `ANIM_LENGTH`: Pixels (snake length, matrix tail)
- `ANIM_PRIMARY_COLOR_HUE`: 0-360° (starting hue)
- `ANIM_HUE_OFFSET`: 0-360° (rainbow spacing)

### 9.3 Live Parameter Updates
**CRITICAL**: Animations must recalculate frame timing **inside the loop**:

```python
# CORRECT ✓
async def run(self):
    while self.running:
        frame_delay = self._calculate_frame_delay()  # Uses self.speed
        # ... render frame ...
        await asyncio.sleep(frame_delay)

# WRONG ✗
async def run(self):
    frame_delay = self._calculate_frame_delay()  # Only once!
    while self.running:
        # ... render ...
        await asyncio.sleep(frame_delay)  # Stale value
```

### 9.4 Preview System
**Dual rendering**:
- `run()`: Full strip animation (89 pixels)
- `run_preview()`: Simplified 8-pixel preview

**PreviewController** handles:
- Animation preview playback
- Crossfade transitions between previews
- Static displays (color, bar indicator)

---

## 10. Hardware Integration

### 10.1 LED Hardware
**Main Strip**: 12V WS2811 (BRG color order)
- 89 pixels in software
- GPIO 18 (PWM0)
- 800kHz signal frequency

**Preview Panel**: 5V WS2812B (GRB color order)
- 8 individual LEDs (CJMCU-2812-8)
- GPIO 19 (PCM - special case)

### 10.2 Input Hardware
**2 Rotary Encoders**:
- **Selector** (GPIO 5/6/13): Zone/animation selection + mode switch
- **Modulator** (GPIO 16/20/21): Parameter adjustment

**4 Buttons**:
- **BTN1** (GPIO 22): Toggle edit mode ON/OFF
- **BTN2** (GPIO 26): Quick lamp white mode
- **BTN3** (GPIO 23): Power toggle (all zones)
- **BTN4** (GPIO 24): STATIC ↔ ANIMATION mode

### 10.3 GPIO Limitations
**WS281x Support**: Only GPIOs 10, 12, 18, 21
- Attempting other pins fails with RuntimeError code -11
- Preview on GPIO 19 works (library version specific)

### 10.4 Physical LED Layout (Current Configuration)
**Zone mapping** (from zones.yaml):
```
FLOOR:   [0-17]    (18 pixels, enabled)
LEFT:    [18-21]   (4 pixels, DISABLED → black)
TOP:     [22-24]   (3 pixels, enabled)
RIGHT:   [25-28]   (4 pixels, enabled)
BOTTOM:  [29-31]   (3 pixels, enabled)
LAMP:    [32-50]   (19 pixels, enabled)
DESK:    [51-76]   (26 pixels, enabled)
BACK:    [77-88]   (12 pixels, enabled, reversed)
```

**Total**: 89 pixels (8 zones, 1 disabled)

**Physical order for snake**: floor → top → right → bottom → lamp → desk → back (sorted by start_index, skipping disabled zones).

---

## 11. Critical Constraints

### 11.1 Color as Single Source of Truth
**ALWAYS use `Color.to_rgb()` for rendering**:

```python
# CORRECT ✓
color = zone.state.color
r, g, b = color.to_rgb()

# WRONG ✗ - loses hue adjustments
preset_idx = zone.preset_index
_, (r, g, b) = get_preset_by_index(preset_idx)
```

### 11.2 Zone Indexing with Disabled Zones
**Include ALL zones (enabled + disabled) in ZoneStrip**:

```python
# CORRECT ✓ - preserves pixel indices
all_zones = config_manager.get_all_zones()
strip = ZoneStrip(gpio=18, zones=all_zones)

# WRONG ✗ - shifts physical LEDs
enabled_zones = config_manager.get_enabled_zones()
strip = ZoneStrip(gpio=18, zones=enabled_zones)  # BUG!
```

Disabled zones render as black (0,0,0) via `ZoneCombined.get_rgb()`.

### 11.3 Animation Speed Updates
**Recalculate frame timing INSIDE animation loop** (see section 9.3).

### 11.4 Pulsing Independence
**Pulsing speed MUST be fixed (not tied to animation_speed)**:

```python
# CORRECT ✓
cycle_duration = 1.0  # Fixed 1 second

# WRONG ✗ - causes strobing
cycle_duration = self.animation_speed / 50.0
```

**Reason**: Pulsing indicates edit mode, not animation state.

### 11.5 lamp_white_mode Exclusions
**When `lamp_white_mode=True`**:
- Lamp excluded from zone selector
- Lamp excluded from animations (`excluded_zones=["lamp"]`)
- Lamp excluded from pulsing
- Lamp color locked to warm_white preset (255, 200, 150)

### 11.6 ControlPanel is Fixed Hardware
**ControlPanel represents physical control panel** - cannot be extended with new inputs. New input sources (web API, MQTT, additional hardware) must publish events directly to EventBus from their own modules.

---

## 12. Extension Points

### 12.1 Adding New Animation
1. Create `animations/new_animation.py` inheriting from `BaseAnimation`
2. Implement `run()` and `run_preview()` methods
3. Register in `AnimationEngine.ANIMATIONS` dict
4. Add to `animations.yaml` with metadata
5. Add parameters to `parameters.yaml`

**Template**:
```python
from animations.base import BaseAnimation
from typing import Dict, AsyncIterator, Tuple

class NewAnimation(BaseAnimation):
    def __init__(self, zones: Dict, speed: int, excluded_zones: List[str], **kwargs):
        super().__init__(zones, speed, excluded_zones)
        self.intensity = kwargs.get('intensity', 50)

    async def run(self) -> AsyncIterator[Tuple[str, int, int, int]]:
        while self.running:
            frame_delay = self._calculate_frame_delay()

            for zone_name in self.active_zones:
                r, g, b = self._calculate_color(zone_name)
                yield (zone_name, r, g, b)

            await asyncio.sleep(frame_delay)

    async def run_preview(self) -> AsyncIterator[List[Tuple[int, int, int]]]:
        # Simplified 8-pixel version
        pass
```

### 12.2 Adding New Input Source
**IMPORTANT**: Do NOT add to ControlPanel (it's a fixed physical module)

1. Create event class in `models/events.py`
2. Add event type to `EventType` enum
3. Create new module for input source
4. Publish events directly to EventBus
5. Subscribe in LEDController

**Example** (Web API):
```python
# In web API module
from models.events import EncoderRotateEvent, EncoderSource

@app.post('/api/rotate')
def api_rotate(delta: int):
    event = EncoderRotateEvent(
        source=EncoderSource.WEB_API,  # Add new source to enum
        delta=delta
    )
    event_bus.publish(event)
```

### 12.3 Adding New Parameter
1. Add to `ParamID` enum in `models/enums.py`
2. Define in `parameters.yaml` with validation rules
3. Add to zone/animation config in YAML
4. Implement adjustment logic in domain model

**Example**:
```python
# models/enums.py
class ParamID(Enum):
    ZONE_SATURATION = "ZONE_SATURATION"

# parameters.yaml
zone_parameters:
  ZONE_SATURATION:
    type: PERCENTAGE
    default: 100
    min: 0
    max: 100
    step: 10
    wraps: false

# Use in Color.to_rgb()
def to_rgb_with_saturation(self, saturation: int) -> Tuple[int, int, int]:
    # Implement saturation adjustment
```

### 12.4 Adding New Domain Entity
1. Create Config, State, and Combined classes in `models/domain/`
2. Add ID enum to `models/enums.py`
3. Create service in `services/`
4. Update `DataAssembler` for persistence
5. Add YAML config file

---

## Appendix A: Performance Characteristics

### Timing Constraints
- **Hardware polling**: 100Hz (10ms interval)
- **Animation frame rate**: 10-50 FPS (speed-dependent)
- **Pulsing cycle**: 1Hz (1000ms)
- **Transition duration**: 100-1000ms (configurable)

### Resource Usage
- **Memory**: Minimal (few MB)
- **CPU**: Low (asyncio is efficient)
- **Disk I/O**: Only on state changes
- **GPIO**: 2 encoders + 4 buttons + 2 LED strips

---

## Appendix B: Logging System

### Structured Logger
**Format**:
```
[HH:MM:SS] CATEGORY ✓ Message
           └─ detail1: value
           └─ detail2: value
```

**Categories** (color-coded):
- CONFIG (cyan)
- HARDWARE (bright blue)
- STATE (bright cyan)
- COLOR (bright magenta)
- ANIMATION (bright yellow)
- ZONE (bright green)
- SYSTEM (bright white)

**Usage**:
```python
from utils.logger import get_category_logger, LogCategory

log = get_category_logger(LogCategory.ZONE)
log("Zone changed", zone="Lamp", color="warm_white")
log.info("Brightness adjusted", brightness=75)
log.error("Invalid zone ID")
```

---

## Appendix C: Transition System

### TransitionService
**Purpose**: Smooth LED state changes across the system.

**Transition Types**:
- `FADE`: Gradual brightness change
- `CROSSFADE`: Blend between states (pixel interpolation)
- `CUT`: Brief black frame
- `NONE`: Instant switch

**Presets**:
```python
STARTUP = TransitionConfig(type=FADE, duration_ms=1000, steps=20)
SHUTDOWN = TransitionConfig(type=FADE, duration_ms=500, steps=15)
MODE_SWITCH = TransitionConfig(type=FADE, duration_ms=300, steps=10)
POWER_TOGGLE = TransitionConfig(type=FADE, duration_ms=400, steps=12)
```

**Easing Functions**:
- `ease_linear`
- `ease_in_quad`, `ease_out_quad`
- `ease_in_out_quad`
- `ease_in_cubic`, `ease_out_cubic`

---

## Appendix D: Special Features

### lamp_white_mode System
**Purpose**: Desk lamp functionality

**Behavior when enabled**:
- Lamp excluded from zone selector
- Lamp excluded from animations
- Lamp excluded from pulsing
- Lamp color locked to warm_white preset (255, 200, 150)
- Previous state saved for restore

**Toggle**: BTN2

### Edit Mode with Pulsing
**Visual indicator**: Current zone pulses at 1Hz

**Details**:
- Fixed 1.0s cycle (independent from animation speed)
- Sine wave: 10% → 100% brightness
- Async task
- Stops during animations
- Skips excluded zones

### Power Toggle with Transitions
**OFF sequence**:
1. Save brightness for all zones
2. Save animation state
3. Fade out (400ms)
4. Set brightnesses to 0
5. Clear preview

**ON sequence**:
1. Restore saved brightnesses
2. Build target frame
3. Fade in from black (400ms)
4. Restart animation if it was running

---

## Revision History

| Version | Date       | Changes                                                    |
|---------|------------|------------------------------------------------------------|
| 0.1     | 2025-11-02 | Initial architecture documentation                         |
| 0.1.1   | 2025-11-03 | Added keyboard input system (Layer 1), dual backend architecture |

---

**END OF DOCUMENT**
