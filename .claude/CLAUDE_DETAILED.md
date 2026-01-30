# Diuna Project - Detailed Reference

This document provides comprehensive technical details for the Diuna LED control system. For a quick overview, see [CLAUDE.md](CLAUDE.md).

---

## Table of Contents

1. [Architecture Deep-Dive](#1-architecture-deep-dive)
2. [All Enums & Constants](#2-all-enums--constants)
3. [Data Models](#3-data-models)
4. [Animation System](#4-animation-system)
5. [Zone Management](#5-zone-management)
6. [Color System](#6-color-system)
7. [Frame System](#7-frame-system)
8. [Rendering Engine](#8-rendering-engine)
9. [Event System](#9-event-system)
10. [API Layer](#10-api-layer)
11. [Socket.IO Real-Time](#11-socketio-real-time)
12. [Frontend Architecture](#12-frontend-architecture)
13. [Hardware Abstraction](#13-hardware-abstraction)
14. [Configuration System](#14-configuration-system)
15. [State Persistence](#15-state-persistence)
16. [Code Patterns](#16-code-patterns)

---

## 1. Architecture Deep-Dive

### Application Startup Sequence

**File:** `src/main_asyncio.py`

```
1. Infrastructure Setup (lines 121-165)
   ├── Initialize GPIO manager (singleton)
   ├── Load YAML configuration files
   ├── Create EventBus with middleware
   └── Load persisted state from state.json

2. Service Initialization (lines 150-206)
   ├── AnimationService (animation definitions)
   ├── ApplicationStateService (global app state)
   ├── ZoneService (zone state mutations)
   └── ServiceContainer (DI aggregator)

3. Hardware Stack (lines 156-190)
   ├── HardwareCoordinator initializes strips
   ├── Create LedChannel instances per GPIO
   └── Register zones with FrameManager

4. FrameManager Startup (lines 173-190)
   ├── Create render loop @ 60 FPS
   ├── Register all LED channels
   └── Create TransitionService

5. Controllers (lines 218-222)
   ├── LightingController (main orchestrator)
   └── ControlPanelController (hardware input polling)

6. API Server (lines 275-300)
   ├── Create FastAPI + Socket.IO app
   ├── Check port availability
   └── Start Uvicorn on 0.0.0.0:8000

7. Graceful Shutdown (lines 303-332)
   ├── ShutdownCoordinator manages teardown
   ├── Signal handlers (Ctrl+C, SIGTERM)
   └── Registered handlers for each subsystem
```

### Rendering Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ FRAME SOURCES                                                        │
├─────────────────────────────────────────────────────────────────────┤
│ • AnimationEngine (per zone)     → SingleZoneFrame / PixelFrame     │
│ • StaticModeController           → MultiZoneFrame                   │
│ • TransitionService              → PixelFrame                       │
│ • API Endpoints                  → Any frame type                   │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
                     push_frame() wraps into MainStripFrame
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PRIORITY QUEUES (FrameManager)                                      │
├─────────────────────────────────────────────────────────────────────┤
│ Queue[DEBUG=50]       - Debug overlays (future)                     │
│ Queue[TRANSITION=40]  - Crossfades, mode switches                   │
│ Queue[PULSE=30]       - Edit mode indicator                         │
│ Queue[ANIMATION=20]   - Running animations (base layer)             │
│ Queue[MANUAL=10]      - Static zone editing                         │
│ Queue[IDLE=0]         - Fallback (black)                            │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
              Render loop @ 60 FPS (_render_loop)
                                  ↓
              _drain_frames() — Intelligent merging:
              1. Collect ANIMATION frames (base layer)
              2. Overlay higher priority frames
              3. Fill gaps with MANUAL/IDLE
                                  ↓
              _render_frame() — Apply zone updates
                                  ↓
              _merge_updates() — Full or partial update
                                  ↓
              _render_to_all_led_channels() — Per-channel routing
                                  ↓
              led_channel.show_full_pixel_frame() — Hardware DMA
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│ LED OUTPUT                                                          │
├─────────────────────────────────────────────────────────────────────┤
│ GPIO 18: WS2811 12V strip (FLOOR, CIRCLE, LAMP, GATE zones)        │
│ GPIO 19: WS2812 5V strip  (PIXEL, PIXEL2, MATRIX zones)            │
└─────────────────────────────────────────────────────────────────────┘
```

### Dependency Injection Pattern

All services are injected via constructor, aggregated in `ServiceContainer`:

```python
# src/services/service_container.py
@dataclass
class ServiceContainer:
    event_bus: EventBus
    zone_service: ZoneService
    animation_service: AnimationService
    app_state_service: ApplicationStateService
    frame_manager: FrameManager
    color_manager: ColorManager
    config_manager: ConfigManager
    data_assembler: DataAssembler
```

**Usage in controllers:**
```python
class LightingController:
    def __init__(self, services: ServiceContainer, ...):
        self._zone_service = services.zone_service
        self._event_bus = services.event_bus
```

---

## 2. All Enums & Constants

**File:** `src/models/enums.py`

### ZoneID (String Enum)
```python
class ZoneID(str, Enum):
    FLOOR = "FLOOR"       # 18 pixels, GPIO 18
    CIRCLE = "CIRCLE"     # 14 pixels, GPIO 18
    LAMP = "LAMP"         # GPIO 18
    GATE = "GATE"         # GPIO 18
    PIXEL = "PIXEL"       # 30 pixels, GPIO 19
    PIXEL2 = "PIXEL2"     # 30 pixels, GPIO 19
    MATRIX = "MATRIX"     # 48 pixels, GPIO 19
    MATRIX2 = "MATRIX2"   # GPIO 19 (disabled)
    PREVIEW = "PREVIEW"   # 8 pixels, GPIO 19 (disabled)
```

### ZoneRenderMode
```python
class ZoneRenderMode(str, Enum):
    STATIC = "STATIC"       # Zone displays static color
    ANIMATION = "ANIMATION" # Zone displays animation
```

### AnimationID (String Enum)
```python
class AnimationID(str, Enum):
    BREATHE = "BREATHE"           # Smooth fade in/out
    COLOR_FADE = "COLOR_FADE"     # Rainbow hue cycling
    SNAKE = "SNAKE"               # Sequential zone chase
    COLOR_SNAKE = "COLOR_SNAKE"   # Multi-pixel rainbow snake
```

### LEDStripID
```python
class LEDStripID(Enum):
    MAIN_12V = auto()  # GPIO 18: WS2811 12V strip
    AUX_5V = auto()    # GPIO 19: WS2812 5V strip
```

### LEDStripType (String Enum)
```python
class LEDStripType(str, Enum):
    WS2811_12V = "WS2811_12V"
    WS2812_5V = "WS2812_5V"
    WS2813 = "WS2813"
    APA102 = "APA102"
    SK6812 = "SK6812"
```

### ColorMode
```python
class ColorMode(auto):
    HUE = auto()     # Hue-based (0-360°)
    PRESET = auto()  # Named preset from colors.yaml
    RGB = auto()     # Direct RGB values
```

### FramePriority
```python
class FramePriority(Enum):
    IDLE = 0         # No active source (black fallback)
    MANUAL = 10      # Manual static color settings
    ANIMATION = 20   # Running animations
    PULSE = 30       # Edit mode pulsing indicator
    TRANSITION = 40  # Crossfades, mode switches
    DEBUG = 50       # Debug overlays (future)
```

### FrameSource
```python
class FrameSource(auto):
    IDLE = auto()
    STATIC = auto()
    MANUAL = auto()
    PULSE = auto()
    ANIMATION = auto()
    TRANSITION = auto()
    PREVIEW = auto()
    DEBUG = auto()
```

### AnimationParamID (String Enum)
```python
class AnimationParamID(str, Enum):
    SPEED = "SPEED"                       # Animation speed (1-100%)
    BRIGHTNESS = "BRIGHTNESS"             # Brightness (0-100%)
    HUE = "HUE"                          # Hue value (0-360°)
    COLOR = "COLOR"                       # Color selector
    INTENSITY = "INTENSITY"               # Intensity/depth (0-100%)
    PRIMARY_COLOR_HUE = "PRIMARY_COLOR_HUE"  # Main animation color
    LENGTH = "LENGTH"                     # Animation length in pixels
```

### ButtonID
```python
class ButtonID(auto):
    BTN1 = auto()  # Toggle edit mode
    BTN2 = auto()  # Quick lamp white mode
    BTN3 = auto()  # Power toggle
    BTN4 = auto()  # Toggle STATIC/ANIMATION mode
```

### EncoderID
```python
class EncoderID(auto):
    SELECTOR = auto()   # Zone/animation selector
    MODULATOR = auto()  # Parameter value modulator
```

### ZoneEditTarget
```python
class ZoneEditTarget(auto):
    COLOR_HUE = auto()     # Edit zone color via hue
    COLOR_PRESET = auto()  # Edit zone color via preset
    BRIGHTNESS = auto()    # Edit zone brightness
```

### EventType
```python
class EventType(auto):
    # Hardware events
    ENCODER_ROTATE = auto()
    ENCODER_CLICK = auto()
    BUTTON_PRESS = auto()
    KEYBOARD_KEYPRESS = auto()

    # Zone events
    ZONE_STATIC_STATE_CHANGED = auto()
    ZONE_RENDER_MODE_CHANGED = auto()
    ZONE_ANIMATION_CHANGED = auto()
    ZONE_SNAPSHOT_UPDATED = auto()

    # Animation events
    ANIMATION_STARTED = auto()
    ANIMATION_STOPPED = auto()
    ANIMATION_PARAMETER_CHANGED = auto()
```

---

## 3. Data Models

### Zone Models (`src/models/domain/zone.py`)

**ZoneConfig** (Immutable, from YAML):
```python
@dataclass(frozen=True)
class ZoneConfig:
    id: ZoneID
    display_name: str
    pixel_count: int
    enabled: bool
    reversed: bool
    order: int
    start_index: int      # First pixel index in GPIO chain
    end_index: int        # Last pixel index in GPIO chain
    gpio: int = 18        # Auto-assigned from zone_mapping.yaml
```

**ZoneState** (Mutable, from state.json):
```python
@dataclass
class ZoneState:
    id: ZoneID
    color: Color
    brightness: int       # 0-100 (percentage)
    is_on: bool
    mode: ZoneRenderMode = ZoneRenderMode.STATIC
    animation: Optional[AnimationState] = None
```

**ZoneCombined** (Config + State):
```python
@dataclass
class ZoneCombined:
    config: ZoneConfig
    state: ZoneState

    @property
    def id(self) -> ZoneID
    @property
    def brightness(self) -> int
```

### Animation Models (`src/models/domain/animation.py`)

**AnimationConfig** (Immutable, from YAML):
```python
@dataclass(frozen=True)
class AnimationConfig:
    id: AnimationID
    display_name: str
    description: str
    parameters: list[AnimationParamID]
```

**AnimationState** (Mutable, per-zone):
```python
@dataclass
class AnimationState:
    id: AnimationID
    parameters: Dict[AnimationParamID, Any]

    def to_dict(self) -> dict
```

### Application State (`src/models/domain/application.py`)

```python
@dataclass
class ApplicationState:
    edit_mode: bool = True
    selected_zone_index: int = 0
    selected_zone_edit_target: ZoneEditTarget = ZoneEditTarget.COLOR_HUE
    selected_animation_param_id: AnimationParamID = AnimationParamID.HUE
    frame_by_frame_mode: bool = False
    save_on_change: bool = True
```

### Hardware Models (`src/models/hardware.py`)

```python
@dataclass(frozen=True)
class LEDStripConfig:
    id: LEDStripID
    gpio: int
    type: LEDStripType
    color_order: str      # "RGB", "GRB", "BRG"
    count: Optional[int] = None
    voltage: float = 5.0
    frequency_hz: int = 800_000
    enabled: bool = True

@dataclass(frozen=True)
class EncoderConfig:
    id: EncoderID
    clk: int              # Clock pin
    dt: int               # Data pin
    sw: Optional[int] = None  # Switch pin

@dataclass(frozen=True)
class ButtonConfig:
    id: ButtonID
    gpio: int
```

---

## 4. Animation System

### Animation Base Class (`src/animations/base.py`)

```python
class BaseAnimation:
    PARAMS: Dict[AnimationParamID, AnimationParam] = {}  # Class-level definitions

    def __init__(self, zone: ZoneCombined, params: Dict[AnimationParamID, Any]):
        self.zone = zone
        self.zone_id: ZoneID = zone.config.id
        self.params: Dict[AnimationParamID, Any] = params.copy()
        self.running: bool = True

    async def step(self) -> SingleZoneFrame | PixelFrame:
        """Generate single animation frame - MUST be implemented by subclasses"""
        raise NotImplementedError

    def get_param(self, param_id: AnimationParamID, default=None) -> Any
    def set_param(self, param_id: AnimationParamID, value: Any) -> None
    def adjust_param(self, param_id: AnimationParamID, delta: int) -> None

    async def run(self):
        """Main generator loop that yields frames until stop()"""
        while self.running:
            yield await self.step()
```

### Animation Engine (`src/animations/engine.py`)

```python
class AnimationEngine:
    ANIMATIONS: Dict[AnimationID, Type[BaseAnimation]] = {
        AnimationID.BREATHE: BreatheAnimation,
        AnimationID.SNAKE: SnakeAnimation,
        AnimationID.COLOR_SNAKE: ColorSnakeAnimation,
        AnimationID.COLOR_FADE: ColorFadeAnimation,
    }

    def __init__(self, frame_manager: FrameManager, ...):
        self.tasks: Dict[ZoneID, asyncio.Task] = {}
        self.active_animations: Dict[ZoneID, BaseAnimation] = {}
        self.active_anim_ids: Dict[ZoneID, AnimationID] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def start_for_zone(self, zone_id: ZoneID, animation_id: AnimationID) -> None:
        """Create animation instance and spawn task"""

    async def stop_for_zone(self, zone_id: ZoneID) -> None:
        """Gracefully stop animation"""

    async def _run_loop(self, zone_id: ZoneID) -> None:
        """Main animation loop - renders frames, submits to FrameManager"""
```

### Built-in Animations

**BreatheAnimation** (`src/animations/breathe.py`):
```python
class BreatheAnimation(BaseAnimation):
    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(),
        AnimationParamID.INTENSITY: IntensityParam(),
    }

    # Internal tuning
    _MIN_SCALE = 0.15    # Minimal brightness 15%
    _MAX_SCALE = 1.0     # Full brightness
    _PHASE_OFFSET = -π/2 # Starts at min brightness

    # Period: 0.8s (speed=100) to 8s (speed=1)
    async def step(self) -> SingleZoneFrame:
        # Sinusoidal brightness modulation
```

**ColorSnakeAnimation** (`src/animations/color_snake.py`):
```python
class ColorSnakeAnimation(BaseAnimation):
    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(),
        AnimationParamID.LENGTH: LengthParam(min_val=3, max_val=15, default=5),
        AnimationParamID.PRIMARY_COLOR_HUE: PrimaryColorHueParam(),
    }

    _HUE_STEP_PER_SEGMENT = 25   # Hue offset between tail segments
    _HUE_DRIFT_PER_FRAME = 1     # Rainbow rotation speed
    _MIN_DELAY = 0.01            # Fastest (speed=100)
    _MAX_DELAY = 0.10            # Slowest (speed=1)

    async def step(self) -> PixelFrame:
        # Multi-pixel rainbow snake
```

### Animation Parameters (`src/models/animation_params/`)

**Base class:**
```python
class AnimationParam(ABC):
    key: AnimationParamID
    label: str
    default: Any

    @abstractmethod
    def adjust(self, current: Any, delta: int) -> Any

    @abstractmethod
    def clamp(self, value: Any) -> Any
```

**Parameter types:**
- `SpeedParam` - Integer 1-100 (step 10)
- `IntensityParam` - Float 0.0-1.0 (step 0.1)
- `LengthParam` - Integer range (customizable)
- `PrimaryColorHueParam` - Integer 0-360 (step 10)

---

## 5. Zone Management

### ZoneService (`src/services/zone_service.py`)

```python
class ZoneService:
    def __init__(self, data_assembler: DataAssembler, event_bus: EventBus, ...):
        self._zones: Dict[ZoneID, ZoneCombined] = {}

    # Read operations
    def get_zone(self, zone_id: ZoneID) -> ZoneCombined
    def get_all(self) -> List[ZoneCombined]
    def get_enabled(self) -> List[ZoneCombined]
    def get_by_render_mode(self, mode: ZoneRenderMode) -> List[ZoneCombined]
    def get_selected_zone(self) -> ZoneCombined

    # Write operations (auto-save + publish event)
    def set_color(self, zone_id: ZoneID, color: Color) -> None
    def set_brightness(self, zone_id: ZoneID, brightness: int) -> None
    def set_render_mode(self, zone_id: ZoneID, mode: ZoneRenderMode) -> None
    def set_animation(self, zone_id: ZoneID, animation: AnimationState) -> None
    def set_power(self, zone_id: ZoneID, is_on: bool) -> None
```

### Zone Hardware Mapping (`src/models/zone_mapping.py`)

```python
@dataclass(frozen=True)
class ZoneHardwareMapping:
    hardware_id: LEDStripID
    zones: List[ZoneID]

@dataclass(frozen=True)
class ZoneMappingConfig:
    mappings: List[ZoneHardwareMapping]

    def get_hardware_for_zone(self, zone_id: ZoneID) -> LEDStripID
    def get_zones_for_hardware(self, hardware_id: LEDStripID) -> List[ZoneID]
```

**Configuration example (zone_mapping.yaml):**
```yaml
hardware_mappings:
  - hardware_id: MAIN_12V
    zones: [FLOOR, CIRCLE, LAMP, GATE]
  - hardware_id: AUX_5V
    zones: [PIXEL, PIXEL2, MATRIX, MATRIX2]
```

### Multi-GPIO Architecture

ConfigManager auto-assigns GPIO based on zone_mapping.yaml:
```
GPIO 18: FLOOR[0-17], CIRCLE[18-31], LAMP[32-50] (starts at 0)
GPIO 19: PIXEL[0-29], PIXEL2[30-59], MATRIX[60-107] (starts at 0)
```

---

## 6. Color System

### Color Model (`src/models/color.py`)

```python
@dataclass
class Color:
    _hue: Optional[int] = None           # 0-360° for HUE mode
    _preset_name: Optional[str] = None   # For PRESET mode
    _rgb: Optional[Tuple[int,int,int]] = None  # Cached RGB
    mode: ColorMode = ColorMode.HUE

    # Constructors
    @classmethod
    def from_hue(cls, hue: int) -> Color

    @classmethod
    def from_preset(cls, preset_name: str, color_manager: ColorManager) -> Color

    @classmethod
    def from_rgb(cls, r: int, g: int, b: int) -> Color

    # Conversion
    def to_rgb(self) -> Tuple[int, int, int]  # Always returns RGB
    def to_hue(self) -> int

    # Manipulation
    def adjust_hue(self, delta: int) -> Color
    def next_preset(self, delta: int, cm: ColorManager) -> Color
    def with_brightness(self, brightness: int) -> Color  # Scale by 0-100%

    # Mode conversion
    def to_preset_mode(self, cm: ColorManager) -> Color
    def to_hue_mode(self) -> Color

    # Utilities
    @staticmethod
    def apply_brightness(r: int, g: int, b: int, brightness: int) -> Tuple[int,int,int]

    # Convenience
    @classmethod
    def black(cls) -> Color   # (0, 0, 0)
    @classmethod
    def white(cls) -> Color   # (255, 255, 255)
```

### ColorManager (`src/managers/color_manager.py`)

```python
class ColorManager:
    @property
    def preset_colors(self) -> Dict[str, Tuple[int,int,int]]

    @property
    def preset_order(self) -> List[str]  # Cycling order

    @property
    def white_presets(self) -> set  # warm_white, white, cool_white

    def get_preset_rgb(self, name: str) -> Tuple[int,int,int]
    def get_preset_by_index(self, index: int) -> Tuple[str, Tuple[int,int,int]]
    def is_white_preset(self, name: str) -> bool
```

### Color Presets (colors.yaml)

**Categories:**
- `basic`: red, green, blue, yellow, cyan, magenta
- `white`: warm_white, white, cool_white
- `warm`: orange, amber, pink, hot_pink
- `cool`: purple, violet, indigo
- `natural`: mint, lime, sky_blue, ocean, lavender
- `special`: off (0,0,0)

**Cycling order (20 presets):**
```
red → orange → amber → yellow → lime → green → mint → cyan → sky_blue → ocean →
blue → indigo → violet → purple → magenta → hot_pink → pink → warm_white → white → cool_white
```

---

## 7. Frame System

### Frame Types (`src/models/frame.py`)

**BaseFrame** (shared metadata):
```python
@dataclass
class BaseFrame:
    priority: FramePriority
    source: FrameSource
    timestamp: float = field(default_factory=time.time)
    ttl: float = 0.1            # Time to live
    partial: bool = False

    def is_expired(self) -> bool
```

**SingleZoneFrame** (one zone → one color):
```python
@dataclass
class SingleZoneFrame(BaseFrame):
    zone_id: ZoneID = ZoneID.FLOOR
    color: Color = field(default_factory=Color.black)

    def as_zone_update(self) -> Dict[ZoneID, Color]
```

**MultiZoneFrame** (many zones → one color each):
```python
@dataclass
class MultiZoneFrame(BaseFrame):
    zone_colors: Dict[ZoneID, Color] = field(default_factory=dict)

    def as_zone_update(self) -> Dict[ZoneID, Color]
```

**PixelFrame** (many zones → pixel arrays):
```python
@dataclass
class PixelFrame(BaseFrame):
    zone_pixels: Dict[ZoneID, List[Color]] = field(default_factory=dict)

    def as_zone_update(self) -> Dict[ZoneID, List[Color]]
```

**MainStripFrame** (unified internal frame):
```python
@dataclass
class MainStripFrame:
    priority: FramePriority
    source: FrameSource
    updates: Dict[ZoneID, Union[Color, List[Color]]]  # Mixed types
    ttl: float = 0.1
    partial: bool = False
    timestamp: float = field(default_factory=time.time)
```

---

## 8. Rendering Engine

### FrameManager (`src/engine/frame_manager.py`)

**Core attributes:**
```python
class FrameManager:
    def __init__(self, fps: int = 60, ...):
        self._fps = fps
        self._main_queues: Dict[int, Deque[MainStripFrame]] = {}  # By priority
        self._led_channels: Dict[LEDStripID, LedChannel] = {}
        self._zone_render_states: Dict[ZoneID, ZoneRenderState] = {}
        self._frame_times: Deque[float] = deque(maxlen=300)  # 5 sec @ 60 FPS
```

**Key methods:**

```python
def push_frame(self, frame: SingleZoneFrame | MultiZoneFrame | PixelFrame) -> None:
    """Submit frame - wraps into MainStripFrame and queues by priority"""

async def _render_loop(self) -> None:
    """Main loop @ 60 FPS - drains, merges, renders"""

def _drain_frames(self) -> Dict[ZoneID, Union[Color, List[Color]]]:
    """Intelligent frame merging:
    1. Collect ANIMATION frames (base layer)
    2. Overlay higher priority frames
    3. Fill gaps with MANUAL/IDLE
    """

def _render_frame(self, updates: Dict[ZoneID, ...]) -> None:
    """Apply updates to zone render states"""

def _render_to_all_led_channels(self) -> None:
    """Push pixels to hardware via LedChannel.show_full_pixel_frame()"""

def get_metrics(self) -> Dict:
    """Returns fps_target, fps_actual, frames_rendered, dropped_frames, dma_skipped"""
```

**DMA Skip Optimization:**
```python
# Compares frame hash with last rendered frame
# Skips redundant DMA transfers if pixels unchanged
# Metric: dma_skipped tracks optimization effectiveness
```

### ZoneRenderState (`src/engine/zone_render_state.py`)

Per-zone runtime pixel buffer (not persisted):
```python
@dataclass
class ZoneRenderState:
    zone_id: ZoneID
    pixels: List[Color]           # Current pixel colors
    last_update: float = 0.0

    def set_solid_color(self, color: Color) -> None
    def set_pixels(self, pixels: List[Color]) -> None
    def get_pixel_rgb_list(self) -> List[Tuple[int,int,int]]
```

---

## 9. Event System

### EventBus (`src/services/event_bus.py`)

```python
class EventBus:
    def __init__(self):
        self._handlers: Dict[EventType, List[Tuple[int, Callable, Optional[Callable]]]] = {}
        self._middleware: List[Callable] = []
        self._history: Deque = deque(maxlen=100)

    @classmethod
    def instance(cls) -> EventBus:
        """Singleton access"""

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable,
        priority: int = 0,
        filter_fn: Optional[Callable] = None
    ) -> None:
        """Subscribe handler - sorted by priority (descending)"""

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware (FIFO execution, can modify/block events)"""

    async def publish(self, event: Any) -> None:
        """Publish event:
        1. Apply middleware
        2. Save to history
        3. Lookup handlers
        4. Execute by priority
        """

    def get_event_history(self, limit: int = 10) -> List:
        """Get recent events"""
```

**Event flow:**
```
Event Sources → publish(event) → Middleware Pipeline →
Event History → Handler Lookup → Priority Sort →
Per-Handler Filters → Async/Sync Execution → Fault Isolation
```

### Event Classes (`src/models/events/`)

```python
# Hardware events
@dataclass
class EncoderRotateEvent:
    encoder_id: EncoderID
    direction: int  # 1 or -1

@dataclass
class ButtonPressEvent:
    button_id: ButtonID

@dataclass
class KeyboardKeyPressEvent:
    key: str
    modifiers: Set[str]

# Zone events
@dataclass
class ZoneStaticStateChangedEvent:
    zone_id: ZoneID
    field: str  # "color", "brightness", etc.

@dataclass
class ZoneSnapshotUpdatedEvent:
    snapshot: ZoneSnapshotDTO

# Animation events
@dataclass
class AnimationStartedEvent:
    zone_id: ZoneID
    animation_id: AnimationID

@dataclass
class AnimationParameterChangedEvent:
    zone_id: ZoneID
    param_id: AnimationParamID
    value: Any
```

---

## 10. API Layer

### FastAPI Application (`src/api/main.py`)

```python
def create_app(
    title: str = "Diuna LED System",
    version: str = "1.0.0",
    docs_enabled: bool = True,
    cors_origins: List[str] = ["*"]
) -> FastAPI:
    """
    - Configures CORS middleware
    - Registers exception handlers
    - Includes routers (zones, animations, logger, system)
    - Creates /api/health endpoint
    """
```

### Route Handlers

**Zones** (`src/api/routes/zones.py`):
```python
@router.put("/{zone_id}/brightness")
async def set_brightness(zone_id: ZoneID, req: SetZoneBrightnessRequest, ...)

@router.put("/{zone_id}/color")
async def set_color(zone_id: ZoneID, req: SetZoneColorRequest, ...)

@router.put("/{zone_id}/is-on")
async def set_power(zone_id: ZoneID, req: SetZonePowerRequest, ...)

@router.put("/{zone_id}/render-mode")
async def set_render_mode(zone_id: ZoneID, req: SetZoneRenderModeRequest, ...)

@router.put("/{zone_id}/animation")
async def set_animation(zone_id: ZoneID, req: SetZoneAnimationRequest, ...)

@router.put("/{zone_id}/animation/parameters")
async def set_animation_params(zone_id: ZoneID, req: SetZoneAnimationParamsRequest, ...)
```

**Animations** (`src/api/routes/animations.py`):
```python
@router.get("/")
async def list_animations(...) -> List[AnimationResponse]

@router.get("/{animation_id}")
async def get_animation(animation_id: AnimationID, ...) -> AnimationResponse
```

**System** (`src/api/routes/system.py`):
```python
@router.get("/health")
async def health_check(...)

@router.get("/tasks")
async def get_all_tasks(...)

@router.get("/tasks/active")
async def get_active_tasks(...)
```

### Request/Response Schemas (`src/api/schemas/`)

```python
# zone.py
class ColorRequest(BaseModel):
    mode: Literal["RGB", "HUE", "PRESET"]
    hue: Optional[int] = Field(None, ge=0, le=360)
    rgb: Optional[list[int]] = None
    preset_name: Optional[str] = None

class SetZoneBrightnessRequest(BaseModel):
    brightness: int = Field(..., ge=0, le=100)

# animation.py
class AnimationResponse(BaseModel):
    id: str
    display_name: str
    description: str
    parameters: List[str]

# error.py
class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: Optional[str]
```

### Dependency Injection (`src/api/dependencies.py`)

```python
_service_container: Optional[ServiceContainer] = None

def set_service_container(container: ServiceContainer) -> None:
    global _service_container
    _service_container = container

async def get_service_container() -> ServiceContainer:
    if _service_container is None:
        raise HTTPException(503, "Service container not initialized")
    return _service_container
```

---

## 11. Socket.IO Real-Time

### Server Setup (`src/api/socketio/server.py`)

```python
def create_socketio_server(cors_origins: list[str]) -> AsyncServer:
    return AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=cors_origins,
        ping_timeout=60,
        ping_interval=25,
    )

def wrap_app_with_socketio(app, sio: AsyncServer):
    return ASGIApp(sio, app)
```

### Connection Lifecycle (`src/api/socketio/on_connect.py`)

```python
@sio.event
async def connect(sid, environ, auth=None):
    # 1. Send all zones snapshot
    zones = services.zone_service.get_all()
    await sio.emit("zones:snapshot", [...], room=sid)

    # 2. Send all tasks
    await sio.emit("tasks:all", {...}, room=sid)

    # 3. Send recent logs
    await sio.emit("logs:history", {...}, room=sid)

@sio.event
async def disconnect(sid):
    log.info(f"Client disconnected: {sid}")
```

### Zone Broadcasting (`src/api/socketio/zones/broadcaster.py`)

```python
def register_zone_broadcaster(sio, services):
    async def on_zone_snapshot_updated(event: ZoneSnapshotUpdatedEvent):
        await sio.emit("zone:snapshot", asdict(event.snapshot))

    services.event_bus.subscribe(
        EventType.ZONE_SNAPSHOT_UPDATED,
        on_zone_snapshot_updated,
    )
```

### Socket.IO Events Summary

**Server → Client:**
| Event | Payload | Trigger |
|-------|---------|---------|
| `zones:snapshot` | `ZoneSnapshotDTO[]` | On connect |
| `zone:snapshot` | `ZoneSnapshotDTO` | Zone state change |
| `tasks:all` | `{tasks: [...]}` | On connect / request |
| `tasks:active` | `{tasks: [...]}` | On request |
| `logs:history` | `{logs: [...]}` | On connect / request |

**Client → Server:**
| Event | Handler |
|-------|---------|
| `task_get_all` | Returns all tasks |
| `task_get_active` | Returns active tasks |
| `task_get_stats` | Returns task statistics |
| `logs_request_history` | Returns recent logs |

### Zone Snapshot DTO (`src/api/dto/zone_snapshot_dto.py`)

```python
@dataclass
class ZoneSnapshotDTO:
    id: str
    display_name: str
    pixel_count: int
    is_on: bool
    brightness: int
    color: dict  # {mode, hue?, rgb?, preset_name?}
    render_mode: str
    animation: Optional[AnimationStateSnapshotDTO]

    @classmethod
    def from_zone(cls, zone: ZoneCombined) -> ZoneSnapshotDTO
```

---

## 12. Frontend Architecture

### Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| React | 18.2 | UI framework |
| TypeScript | 5.9 | Type safety |
| Vite | 7.2 | Build tool |
| Tailwind CSS | 3.4 | Styling |
| Socket.IO Client | 4.8 | Real-time |
| Axios | 1.13 | HTTP client |
| React Query | 5.90 | Server state |
| Zustand | 4.5 | Local state |
| Radix UI | - | Component primitives |

### State Management (Hybrid)

**1. Zones - External Store + Socket.IO**

File: `frontend/src/features/zones/realtime/zones.store.ts`
```typescript
// External store pattern with React hooks
let zonesSnapshot: ZoneSnapshot[] = [];
const listeners = new Set<() => void>();

export function setZonesSnapshot(zones: ZoneSnapshot[]) {
  zonesSnapshot = zones;
  listeners.forEach(fn => fn());
}

export function useZones(): ZoneSnapshot[] {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
```

File: `frontend/src/features/zones/realtime/zones.socket.ts`
```typescript
socket.on('zones:snapshot', (zones: ZoneSnapshot[]) => {
  setZonesSnapshot(zones);
});

socket.on('zone:snapshot', (zone: ZoneSnapshot) => {
  updateZoneSnapshot(zone);
});
```

**2. Initial Fetch - React Query**

File: `frontend/src/features/zones/api/queries.ts`
```typescript
export const useZonesQuery = () => {
  return useQuery<ZonesResponse>({
    queryKey: ['zones'],
    queryFn: fetchZones,
  });
};
```

**3. Design System - Zustand**

File: `frontend/src/future-design/store/designStore.ts`
```typescript
interface DesignState {
  theme: 'cyber' | 'nature';
  colorMode: 'RGB' | 'HUE' | 'PRESET';
  // ...
}

export const useDesignStore = create<DesignState>()(
  persist(
    (set) => ({ ... }),
    { name: 'design-storage' }
  )
);
```

### API Client (`frontend/src/shared/api/client.ts`)

```typescript
const client = axios.create({
  baseURL: getApiUrl(),
  timeout: 10000,
});

// Auth interceptor
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Error interceptor
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### Socket.IO Client (`frontend/src/realtime/socket.ts`)

```typescript
export const socket = io(getWebSocketUrl(), {
  transports: ['websocket'],
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
});
```

### TypeScript Interfaces (`frontend/src/shared/types/domain/`)

```typescript
// zone.ts
interface ZoneSnapshot {
  id: string;
  display_name: string;
  pixel_count: number;
  is_on: boolean;
  brightness: number;
  color: ColorSnapshot;
  render_mode: 'STATIC' | 'ANIMATION';
  animation: AnimationStateSnapshot | null;
}

// color.ts
interface ColorSnapshot {
  mode: 'RGB' | 'HUE' | 'PRESET';
  hue?: number;
  rgb?: [number, number, number];
  preset_name?: string;
}

// animation.ts
interface AnimationStateSnapshot {
  id: string;
  parameters: Record<string, any>;
}
```

### Key Frontend Files

| File | Purpose |
|------|---------|
| `main.tsx` | React 18 entry point |
| `App.tsx` | Router + QueryClientProvider |
| `layout/MainLayout.tsx` | Sidebar + header layout |
| `pages/Dashboard.tsx` | Main dashboard |
| `features/zones/` | Zone management feature |
| `shared/api/client.ts` | Axios instance |
| `realtime/socket.ts` | Socket.IO connection |
| `config/constants.ts` | API/WS URL config |

---

## 13. Hardware Abstraction

### GPIO Manager (`src/hardware/gpio/`)

**Protocol** (`gpio_manager_interface.py`):
```python
class IGPIOManager(Protocol):
    HIGH: int
    LOW: int

    def register_input(self, pin: int, name: str, pull_mode: str) -> None
    def register_output(self, pin: int, name: str) -> None
    def register_ws281x(self, pin: int, name: str) -> None
    def read(self, pin: int) -> int
    def write(self, pin: int, value: int) -> None
    def cleanup(self) -> None
    def get_registry(self) -> Dict
```

**Implementations:**
- `gpio_manager_hardware.py` - RPi.GPIO (production)
- `gpio_manager_mock.py` - Mock for testing

### LED Strip Driver (`src/hardware/led/ws281x_strip.py`)

```python
class WS281xStrip:
    def __init__(self, gpio_pin: int, pixel_count: int, ...):
        self._strip = PixelStrip(...)
        self._buffer: List[int] = [0] * pixel_count

    def set_pixel(self, index: int, r: int, g: int, b: int) -> None
    def get_pixel(self, index: int) -> Tuple[int, int, int]
    def apply_frame(self, pixels: List[Tuple[int,int,int]]) -> None
    def show(self) -> None  # DMA transfer
    def clear(self) -> None
```

**Color order handling:**
- Supports RGB, RBG, GRB, GBR, BRG, BGR
- Configured via `hardware.yaml`

### Input Devices (`src/hardware/input/`)

**RotaryEncoder** (`rotary_encoder.py`):
```python
class RotaryEncoder:
    def read_rotation(self) -> int:  # 1, -1, or 0
    def read_button(self) -> bool:   # Debounced press
```

**Button** (`button.py`):
```python
class Button:
    def is_pressed(self) -> bool:  # True once per press
    def is_held(self) -> bool:     # Raw state
```

**Keyboard Adapters** (`keyboard/adapters/`):
- `evdev.py` - Linux /dev/input (physical keyboard)
- `stdin.py` - Terminal stdin (SSH)
- `dummy.py` - No-op fallback

---

## 14. Configuration System

### ConfigManager (`src/managers/config_manager.py`)

Loads and merges YAML files via include system:

```yaml
# config.yaml
include:
  - hardware.yaml
  - zones.yaml
  - zone_mapping.yaml
  - colors.yaml
  - animations.yaml
  - parameters.yaml
```

**ConfigManager responsibilities:**
1. Load config.yaml with include processing
2. Initialize sub-managers (Hardware, Animation, Color)
3. Build zone-to-hardware mappings
4. Auto-assign GPIO to zones

### Configuration Files

**zones.yaml:**
```yaml
zones:
  - id: FLOOR
    display_name: "Floor"
    pixel_count: 18
    enabled: true
    reversed: false
    order: 1
```

**hardware.yaml:**
```yaml
led_strips:
  - id: MAIN_12V
    gpio: 18
    type: WS2811_12V
    color_order: BRG
    count: 51
    voltage: 12.0

  - id: AUX_5V
    gpio: 19
    type: WS2812_5V
    color_order: GRB
    count: 68
    voltage: 5.0

encoders:
  - id: SELECTOR
    clk: 5
    dt: 6
    sw: 13

buttons:
  - id: BTN1
    gpio: 22
```

**zone_mapping.yaml:**
```yaml
hardware_mappings:
  - hardware_id: MAIN_12V
    zones: [FLOOR, CIRCLE, LAMP, GATE]
  - hardware_id: AUX_5V
    zones: [PIXEL, PIXEL2, MATRIX, MATRIX2]
```

**colors.yaml:**
```yaml
presets:
  red: { rgb: [255, 0, 0], category: basic }
  warm_white: { rgb: [255, 200, 150], category: white }
  # ...

preset_order:
  - red
  - orange
  - yellow
  # ... (20 total)
```

**animations.yaml:**
```yaml
animations:
  BREATHE:
    name: Breathe
    class: BreatheAnimation
    description: "Smooth breathing effect"
    enabled: true
    order: 1
    parameters: []
```

---

## 15. State Persistence

### State File (`src/state/state.json`)

```json
{
  "zones": {
    "FLOOR": {
      "color": { "mode": "PRESET", "preset_name": "warm_white" },
      "brightness": 80,
      "is_on": true,
      "mode": "STATIC",
      "animation": null
    },
    "CIRCLE": {
      "color": { "mode": "HUE", "hue": 180 },
      "brightness": 100,
      "is_on": true,
      "mode": "ANIMATION",
      "animation": {
        "id": "BREATHE",
        "parameters": { "SPEED": 50, "INTENSITY": 0.5 }
      }
    }
  },
  "application": {
    "edit_mode_on": true,
    "selected_zone_index": 0,
    "selected_zone_edit_target": "COLOR_HUE",
    "frame_by_frame_mode": false,
    "save_on_change": true
  }
}
```

### ApplicationStateService (`src/services/application_state_service.py`)

```python
class ApplicationStateService:
    def __init__(self, data_assembler: DataAssembler):
        self._state: ApplicationState
        self._save_task: Optional[asyncio.Task] = None
        self._debounce_delay = 0.5  # 500ms

    def get_state(self) -> ApplicationState

    def save(self, **updates) -> None:
        """Update + queue debounced save"""
        for key, value in updates.items():
            setattr(self._state, key, value)
        self._queue_save()

    def _queue_save(self) -> None:
        """Cancel pending save, schedule new one"""
        if self._save_task:
            self._save_task.cancel()
        self._save_task = asyncio.create_task(self._debounced_save())

    async def _debounced_save(self) -> None:
        await asyncio.sleep(self._debounce_delay)
        self._data_assembler.save_application_state(self._state)
```

### DataAssembler (`src/services/data_assembler.py`)

Repository pattern - only component that touches state.json:
```python
class DataAssembler:
    def load_zones(self) -> Dict[ZoneID, ZoneCombined]
    def save_zone(self, zone: ZoneCombined) -> None
    def load_application_state(self) -> ApplicationState
    def save_application_state(self, state: ApplicationState) -> None
```

---

## 16. Code Patterns

### Pattern 1: Constructor Injection

```python
# CORRECT
class LightingController:
    def __init__(
        self,
        services: ServiceContainer,
        animation_engine: AnimationEngine,
        frame_manager: FrameManager,
    ):
        self._zone_service = services.zone_service
        self._animation_engine = animation_engine
        self._frame_manager = frame_manager

# WRONG
controller = LightingController()
controller.frame_manager = frame_manager  # Property injection
```

### Pattern 2: Event-Driven State Changes

```python
# Service mutation publishes event
class ZoneService:
    def set_color(self, zone_id: ZoneID, color: Color) -> None:
        zone = self._zones[zone_id]
        zone.state.color = color
        self._data_assembler.save_zone(zone)

        # Publish for subscribers (API, controllers, etc.)
        self._event_bus.publish(ZoneSnapshotUpdatedEvent(
            snapshot=ZoneSnapshotDTO.from_zone(zone)
        ))

# Socket.IO broadcaster subscribes
def register_zone_broadcaster(sio, services):
    async def handler(event: ZoneSnapshotUpdatedEvent):
        await sio.emit("zone:snapshot", asdict(event.snapshot))

    services.event_bus.subscribe(EventType.ZONE_SNAPSHOT_UPDATED, handler)
```

### Pattern 3: Async Task Management

```python
# AnimationEngine manages per-zone tasks
class AnimationEngine:
    async def start_for_zone(self, zone_id: ZoneID, anim_id: AnimationID):
        async with self._lock:
            # Stop existing
            if zone_id in self.tasks:
                await self.stop_for_zone(zone_id)

            # Create and start
            animation = self._create_animation(zone_id, anim_id)
            task = asyncio.create_task(self._run_loop(zone_id))
            self.tasks[zone_id] = task

    async def stop_for_zone(self, zone_id: ZoneID):
        async with self._lock:
            if zone_id in self.tasks:
                self.tasks[zone_id].cancel()
                try:
                    await self.tasks[zone_id]
                except asyncio.CancelledError:
                    pass
                del self.tasks[zone_id]
```

### Pattern 4: Frame Submission

```python
# Animation yields frames → Engine submits
async def _run_loop(self, zone_id: ZoneID):
    animation = self.active_animations[zone_id]
    async for frame in animation.run():
        self._frame_manager.push_frame(frame)

# Static controller submits MultiZoneFrame
class StaticModeController:
    def render_zones(self, zone_ids: List[ZoneID]):
        zone_colors = {
            zid: self._zone_service.get_zone(zid).state.color
            for zid in zone_ids
        }
        frame = MultiZoneFrame(
            zone_colors=zone_colors,
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
        )
        self._frame_manager.push_frame(frame)
```

### Pattern 5: Type-Safe APIs

```python
# CORRECT - explicit type check
if isinstance(obj, ZoneStrip):
    obj.get_frame()

# WRONG - duck typing
if hasattr(obj, 'get_frame'):
    obj.get_frame()
```

### Pattern 6: Graceful Shutdown

```python
# ShutdownCoordinator in main_asyncio.py
class ShutdownCoordinator:
    def __init__(self):
        self._handlers: List[Callable] = []

    def register(self, handler: Callable) -> None:
        self._handlers.append(handler)

    async def shutdown(self) -> None:
        for handler in reversed(self._handlers):
            try:
                await handler()
            except Exception as e:
                log.error(f"Shutdown handler failed: {e}")

# Usage
coordinator.register(api_wrapper.stop)
coordinator.register(frame_manager.stop)
coordinator.register(animation_engine.stop_all)
```

---

## Quick Reference Cards

### Adding a New Animation

1. Create `src/animations/my_animation.py`:
```python
class MyAnimation(BaseAnimation):
    PARAMS = {
        AnimationParamID.SPEED: SpeedParam(),
    }

    async def step(self) -> SingleZoneFrame:
        # Calculate color based on self.params
        return SingleZoneFrame(
            zone_id=self.zone_id,
            color=color,
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
        )
```

2. Register in `src/animations/engine.py`:
```python
ANIMATIONS[AnimationID.MY_ANIMATION] = MyAnimation
```

3. Add to `src/config/animations.yaml`:
```yaml
MY_ANIMATION:
  name: My Animation
  class: MyAnimation
  description: "Description"
  enabled: true
```

4. Add enum in `src/models/enums.py`:
```python
class AnimationID(str, Enum):
    MY_ANIMATION = "MY_ANIMATION"
```

### Adding a New Zone

1. Add to `src/config/zones.yaml`
2. Add to `src/config/zone_mapping.yaml`
3. Add to `ZoneID` enum in `src/models/enums.py`
4. Initialize state in `src/state/state.json`

### Adding a New API Endpoint

1. Create route in `src/api/routes/my_route.py`
2. Add schemas in `src/api/schemas/`
3. Include router in `src/api/main.py`
4. Add TypeScript types in `frontend/src/shared/types/`
5. Add API function in `frontend/src/shared/api/`
