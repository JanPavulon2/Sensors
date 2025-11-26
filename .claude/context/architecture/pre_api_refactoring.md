---
Last Updated: 2025-11-17
Updated By: @architecture-expert-sonnet
Changes: Complete pre-API refactoring plan - Per-Zone Modes, Multi-GPIO Architecture, Parameters Clarity, Color System
Phase: Before Phase 9 (API Layer)
Status: PLANNING - Ready for Review
---

# Pre-API Refactoring: Code Perfection Plan

## Executive Summary

Before implementing FastAPI (Phase 9) and Frontend (Phase 10), we must achieve **code perfection** in four critical areas:

1. **Per-Zone Independent Modes** - Enable zones to have individual STATIC/ANIMATION/OFF states
2. **Multi-GPIO Zone Architecture** - Support multiple LED chains on different GPIO pins
3. **Parameter System Clarity** - Keep Config/State/Combined pattern but make it clearer
4. **Color System Enhancement** - Add HSV, temperature support, harmonies, and perfect the architecture

**Total Effort**: 42-56 hours (5-7 focused days)
**Complexity**: Medium-High
**Risk**: Medium (substantial refactor, high value)

**Philosophy**: Perfect the backend architecture NOW, so the API layer can be thin and beautiful.

---

## Critical Design Rules

### 1. NO MAGIC STRINGS - Always Use Enums
```python
# ❌ WRONG - Magic string
mode = zone_data.get("mode", "STATIC")

# ✅ CORRECT - Use Serializer
from utils.serialization import Serializer
mode = Serializer.str_to_enum(zone_data.get("mode", "STATIC"), ZoneMode)
```

### 2. ALL Serialization via Serializer Class
```python
# Enum → String
Serializer.enum_to_str(ZoneMode.STATIC)  # → "STATIC"

# String → Enum
Serializer.str_to_enum("STATIC", ZoneMode)  # → ZoneMode.STATIC

# Dict → Object
Serializer.zone_to_dict(zone_combined)

# Object → Dict
Serializer.dict_to_zone(zone_dict, zone_service)
```

### 3. Keep Three-Layer Parameter Pattern
**Config** (immutable) + **State** (mutable) + **Combined** (business logic) = **Good Architecture**

### 4. Zone Groups, Not Global Mode
**Future**: Group all zones → same behavior as old global mode

---

## Part 1: Per-Zone Independent Modes

### Vision

**Current (Global Mode)**:
```python
Application.main_mode = STATIC  # All zones static
         OR
Application.main_mode = ANIMATION  # All zones animate
```

**New (Per-Zone Modes)**:
```python
Zone[FLOOR].mode = STATIC       # Static color
Zone[LAMP].mode = ANIMATION     # Running snake
Zone[DESK].mode = OFF           # Powered off
Zone[NEW_STRIP].mode = ANIMATION  # On GPIO 19
Zone[PREVIEW].mode = STATIC     # Preview zone
```

**Future (Zone Groups)**:
```python
group = ZoneGroup("ALL", [FLOOR, LAMP, DESK, ...])
group.set_mode(ZoneMode.ANIMATION)  # Like old global mode
```

### Why This Matters for Wearables

**Smart Jacket Example**:
```python
zones = {
    "LEFT_SLEEVE": mode=STATIC, color=white,      # Visibility
    "RIGHT_SLEEVE": mode=ANIMATION, anim=SNAKE,   # Style
    "CHEST": mode=ANIMATION, anim=BREATHE,        # Ambient
    "BACK": mode=STATIC, color=red,               # Branding
    "COLLAR": mode=OFF                             # Disabled
}
```

### Implementation Plan

#### Step 1: Add ZoneMode to State Model (2-3 hours)

**New Enum**:
```python
# src/models/enums/zone.py
class ZoneMode(Enum):
    STATIC = auto()
    ANIMATION = auto()
    OFF = auto()
```

**Update ZoneState**:
```python
# src/models/domain/zone.py
@dataclass
class ZoneState:
    id: ZoneID
    color: Color
    mode: ZoneMode = ZoneMode.STATIC  # NEW
    animation_id: Optional[AnimationID] = None  # NEW
```

**Remove Global Mode**:
```python
# src/models/domain/application.py
@dataclass
class ApplicationState:
    selected_zone_index: int = 0  # Cycles through ALL zones
    edit_mode: bool = False
    lamp_white_mode: bool = False
    frame_by_frame: bool = False
```

**Serialization (CORRECT WAY)**:
```python
# src/services/data_assembler.py
from utils.serialization import Serializer

def build_zones(self) -> List[ZoneCombined]:
    """Build zones from config + state"""
    for zone_id_str, zone_data in state_data["zones"].items():
        zone_id = Serializer.str_to_enum(zone_id_str, ZoneID)

        # Parse mode (with default)
        mode_str = zone_data.get("mode", "STATIC")
        mode = Serializer.str_to_enum(mode_str, ZoneMode)

        # Parse animation_id (optional)
        animation_id = None
        if "animation_id" in zone_data:
            animation_id = Serializer.str_to_enum(
                zone_data["animation_id"],
                AnimationID
            )

        zone_state = ZoneState(
            id=zone_id,
            color=Serializer.dict_to_color(zone_data["color"]),
            mode=mode,
            animation_id=animation_id
        )

def save_zone_state(self, zones: List[ZoneCombined]):
    """Save zones to state.json"""
    state_dict = {}
    for zone in zones:
        state_dict[Serializer.enum_to_str(zone.config.id)] = {
            "color": Serializer.color_to_dict(zone.state.color),
            "mode": Serializer.enum_to_str(zone.state.mode),
            "animation_id": Serializer.enum_to_str(zone.state.animation_id)
                           if zone.state.animation_id else None
        }
    # Write to file...
```

**Deliverable**: Zone mode persisted correctly in state.json

---

#### Step 2: Animation Engine Frame Merging (4-6 hours)

**Problem**: AnimationEngine only submits animated zones → static zones go dark

**Solution**: Merge static zones into PixelFrame

```python
# src/animations/engine.py
async def _run_loop(self):
    """Main animation loop - merges static zones"""

    async for frame_data in self.current_animation.run():
        # Collect animated zone updates
        zone_pixels = {}  # {ZoneID: [(r,g,b), ...]}

        for update in frame_data:
            # ... existing pixel/zone collection ...
            pass

        # NEW: Merge static zones from ALL GPIO chains
        static_zones = [z for z in self.zone_service.get_enabled()
                        if z.state.mode == ZoneMode.STATIC]

        for zone in static_zones:
            r, g, b = zone.get_rgb()  # With brightness
            zone_pixels[zone.id] = [(r, g, b)] * zone.config.pixel_count

        # Submit unified frame
        frame = PixelFrame(
            priority=FramePriority.ANIMATION,
            zone_pixels=zone_pixels,
            source=FrameSource.MIXED  # NEW enum value
        )
        await self.frame_manager.submit_pixel_frame(frame)
```

**New FrameSource**:
```python
# src/models/frames.py
class FrameSource(Enum):
    STATIC = auto()
    ANIMATION = auto()
    MIXED = auto()  # NEW: Static + animated zones
    TRANSITION = auto()
```

---

#### Step 3: Controller Routing Refactor (6-8 hours)

**Remove Global Mode Checks**:
```python
# src/controllers/led_controller/led_controller.py

# OLD (DELETE):
if self.main_mode == MainMode.STATIC:
    self.static_mode_controller.handle(...)
else:
    self.animation_mode_controller.handle(...)

# NEW: Route based on current zone's mode
current_zone = self._get_current_zone()

if current_zone.state.mode == ZoneMode.STATIC:
    self.static_mode_controller.handle(...)
elif current_zone.state.mode == ZoneMode.ANIMATION:
    self.animation_mode_controller.handle(...)
# elif ZoneMode.OFF: no action
```

**Zone Selection (Edit Mode)**:
```python
def _get_current_zone(self) -> ZoneCombined:
    """Get currently selected zone

    Cycles through ALL zones regardless of mode
    """
    zones = self.zone_service.get_all()
    index = self.app_state_service.state.selected_zone_index
    return zones[index]

def change_zone(self, delta: int):
    """Cycle through zones (SELECTOR encoder)"""
    zones = self.zone_service.get_all()
    current_index = self.app_state_service.state.selected_zone_index
    new_index = (current_index + delta) % len(zones)

    self.app_state_service.set_current_zone_index(new_index)
    await self._sync_preview()
```

**Mode Toggle (BTN4)**:
```python
async def _toggle_zone_mode(self):
    """Cycle current zone: STATIC → ANIMATION → OFF → STATIC"""
    current_zone = self._get_current_zone()

    if current_zone.state.mode == ZoneMode.STATIC:
        current_zone.state.mode = ZoneMode.ANIMATION
        if not current_zone.state.animation_id:
            # Set default animation
            first_anim = self.animation_service.get_all()[0]
            current_zone.state.animation_id = first_anim.config.id
        await self._restart_animations()

    elif current_zone.state.mode == ZoneMode.ANIMATION:
        current_zone.state.mode = ZoneMode.OFF
        await self._restart_animations()

    else:  # OFF
        current_zone.state.mode = ZoneMode.STATIC

    self.zone_service.save()
    await self._sync_preview()
```

---

#### Step 4: Zone Groups (Future Concept) (0 hours)

**Not implementing now**, just designing for future:

```python
# Future: src/models/domain/zone_group.py
@dataclass
class ZoneGroup:
    id: str
    name: str
    zone_ids: List[ZoneID]

    def set_mode(self, mode: ZoneMode):
        """Set mode for all zones in group"""
        for zone_id in self.zone_ids:
            zone = zone_service.get_zone(zone_id)
            zone.state.mode = mode
```

**Usage**:
```python
all_zones = ZoneGroup("ALL", "All Zones",
                      [FLOOR, LAMP, DESK, NEW_STRIP, PREVIEW])
all_zones.set_mode(ZoneMode.ANIMATION)  # Old global mode behavior
```

---

## Part 2: Multi-GPIO Zone Architecture

### Hardware Scenarios

**Scenario 1: Multiple GPIO Pins**
```
GPIO 18 (Main strip - WS2811 12V):
├─ FLOOR (45 px)
├─ LAMP (30 px)
└─ DESK (15 px)

GPIO 19 (Second strip - WS2812 5V):
├─ PIXEL (30 px)
├─ PIXEL2 (30 px)
└─ PREVIEW (8 px)
```

**Scenario 2: Mixed Voltage Chaining**
```
GPIO 18 (chained):
├─ WS2811 12V zones (separate 12V power)
└─ WS2812 5V zones (separate 5V power)
    └─ Data line only, shared ground
```

**Why Multi-GPIO Still Needed**:
- Signal degradation on long chains (>300 LEDs)
- Independent control (different frame rates)
- Hardware isolation (fault tolerance)
- Flexibility (mix WS2811, WS2812, SK6812, etc.)

### Implementation

#### Step 1: Update Zone Config Schema (2-3 hours)

**zones.yaml Structure**:
```yaml
# Multi-GPIO chain configuration
gpio_chains:
  - gpio_pin: 18
    led_type: WS2811
    freq_hz: 800000
    dma: 10
    channel: 0
    invert: false
    brightness: 255
    zones:
      - id: FLOOR
        display_name: "Floor Strip"
        start_index: 0  # Within THIS chain
        pixel_count: 45
        enabled: true
        reversed: false

      - id: LAMP
        display_name: "Lamp"
        start_index: 45
        pixel_count: 30
        enabled: true
        reversed: false

      - id: DESK
        display_name: "Desk"
        start_index: 75
        pixel_count: 15
        enabled: true
        reversed: false

  - gpio_pin: 19
    led_type: WS2812  # GRB order
    freq_hz: 800000
    dma: 11
    channel: 1
    invert: false
    brightness: 255
    zones:
      - id: NEW_STRIP
        display_name: "New Strip"
        start_index: 0  # Within THIS chain
        pixel_count: 30
        enabled: true
        reversed: false

      - id: PREVIEW
        display_name: "Preview Panel"
        start_index: 30
        pixel_count: 8
        enabled: true
        reversed: true  # Upside-down mounting
        is_preview: true
```

**ZoneConfig Update**:
```python
# src/models/domain/zone.py
@dataclass(frozen=True)
class ZoneConfig:
    id: ZoneID
    display_name: str
    start_index: int  # Index within GPIO chain
    pixel_count: int
    gpio_pin: int  # NEW: Which GPIO
    led_type: str  # WS2811 or WS2812
    enabled: bool
    reversed: bool = False  # NEW: Reverse pixel order
    is_preview: bool = False  # NEW: Preview zone flag
```

**Config Loading (Serializer)**:
```python
# src/managers/config_manager.py
from utils.serialization import Serializer

def load_zones_config(self, data: dict) -> List[ZoneConfig]:
    """Load zones from gpio_chains structure"""
    zones = []

    for chain in data["gpio_chains"]:
        gpio_pin = chain["gpio_pin"]
        led_type = chain.get("led_type", "WS2811")

        for zone_data in chain["zones"]:
            zone_id = Serializer.str_to_enum(zone_data["id"], ZoneID)

            zone_config = ZoneConfig(
                id=zone_id,
                display_name=zone_data["display_name"],
                start_index=zone_data["start_index"],
                pixel_count=zone_data["pixel_count"],
                gpio_pin=gpio_pin,  # From parent chain
                led_type=led_type,
                enabled=zone_data.get("enabled", True),
                reversed=zone_data.get("reversed", False),
                is_preview=zone_data.get("is_preview", False)
            )
            zones.append(zone_config)

    return zones
```

---

#### Step 2: Multi-Chain Zone Strip Manager (4-6 hours)

**New Architecture**:
```python
# src/components/zone_strip_manager.py
from rpi_ws281x import PixelStrip, ws

class ZoneStripManager:
    """Manages multiple LED strips on different GPIO pins"""

    def __init__(self, chains_config: List[dict]):
        """
        Args:
            chains_config: GPIO chain configs from zones.yaml
        """
        self.strips: Dict[int, PixelStrip] = {}
        self.zone_to_gpio: Dict[ZoneID, int] = {}

        for chain in chains_config:
            gpio = chain["gpio_pin"]
            led_type = chain.get("led_type", "WS2811")

            # Calculate total pixels for this chain
            total_pixels = sum(
                z["pixel_count"] for z in chain["zones"]
            )

            # Determine strip type (color order)
            if led_type == "WS2812":
                strip_type = ws.WS2811_STRIP_GRB
            elif led_type == "SK6812":
                strip_type = ws.SK6812_STRIP_RGBW
            else:  # WS2811
                strip_type = ws.WS2811_STRIP_RGB

            # Create hardware strip
            self.strips[gpio] = PixelStrip(
                total_pixels,
                gpio,
                freq_hz=chain.get("freq_hz", 800000),
                dma=chain.get("dma", 10),
                invert=chain.get("invert", False),
                brightness=chain.get("brightness", 255),
                channel=chain.get("channel", 0),
                strip_type=strip_type
            )
            self.strips[gpio].begin()

            # Build zone → GPIO routing map
            for zone_data in chain["zones"]:
                zone_id_enum = Serializer.str_to_enum(
                    zone_data["id"],
                    ZoneID
                )
                self.zone_to_gpio[zone_id_enum] = gpio

    def set_zone_color(
        self,
        zone: ZoneConfig,
        r: int, g: int, b: int
    ):
        """Set entire zone to single color"""
        strip = self.strips[zone.gpio_pin]

        for i in range(zone.pixel_count):
            pixel_index = zone.start_index + i

            # Handle reversed mounting
            if zone.reversed:
                pixel_index = zone.start_index + (zone.pixel_count - 1 - i)

            strip.setPixelColorRGB(pixel_index, r, g, b)

    def set_zone_pixels(
        self,
        zone: ZoneConfig,
        pixels: List[Tuple[int, int, int]]
    ):
        """Set zone with per-pixel colors"""
        strip = self.strips[zone.gpio_pin]

        for i, (r, g, b) in enumerate(pixels):
            if i >= zone.pixel_count:
                break

            pixel_index = zone.start_index + i

            # Handle reversed mounting
            if zone.reversed:
                pixel_index = zone.start_index + (zone.pixel_count - 1 - i)

            strip.setPixelColorRGB(pixel_index, r, g, b)

    def show_all(self):
        """Update all hardware strips"""
        for strip in self.strips.values():
            strip.show()

    def clear_all(self):
        """Turn off all LEDs"""
        for strip in self.strips.values():
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, 0)
        self.show_all()
```

**Benefits**:
- Supports unlimited GPIO chains
- Per-zone GPIO routing
- Reversed mounting automatic
- Mixed LED types (WS2811, WS2812, SK6812)
- Single show() updates all hardware

---

#### Step 3: Update FrameManager (2-3 hours)

**FrameManager already zone-centric** - minimal changes:

```python
# src/engine/frame_manager.py
def _render_pixel_frame(self, frame: PixelFrame):
    """Render pixel frame (multi-GPIO aware)"""

    for zone_id, pixels in frame.zone_pixels.items():
        zone = self.zone_service.get_zone(zone_id)

        # Route to correct GPIO chain
        self.zone_strip_manager.set_zone_pixels(
            zone.config,
            pixels
        )

    # Update all hardware strips
    self.zone_strip_manager.show_all()
```

**No other changes needed!**

---

#### Step 4: Preview as Normal Zone (3-4 hours)

**Delete**: `PreviewPanelController` (570 lines)

**Create**: Lightweight `PreviewService`

```python
# src/services/preview_service.py
class PreviewService:
    """Manages preview zone behavior"""

    def __init__(
        self,
        zone_service: ZoneService,
        app_state_service: ApplicationStateService
    ):
        self.zone_service = zone_service
        self.app_state_service = app_state_service
        self.preview_zone_id = ZoneID.PREVIEW

    async def sync_to_current_zone(self):
        """Update preview to show current zone's state"""

        current_zone = self._get_current_zone()
        preview_zone = self.zone_service.get_zone(self.preview_zone_id)

        if current_zone.state.mode == ZoneMode.STATIC:
            preview_zone.state.mode = ZoneMode.STATIC
            preview_zone.state.color = current_zone.state.color
            # Scaled brightness for visibility
            preview_zone.parameters["brightness"].value = min(
                current_zone.brightness,
                128
            )

        elif current_zone.state.mode == ZoneMode.ANIMATION:
            preview_zone.state.mode = ZoneMode.ANIMATION
            preview_zone.state.animation_id = current_zone.state.animation_id

        elif current_zone.state.mode == ZoneMode.OFF:
            preview_zone.state.mode = ZoneMode.OFF

        self.zone_service.save()

    def _get_current_zone(self) -> ZoneCombined:
        """Get current zone (excluding preview)"""
        zones = [z for z in self.zone_service.get_all()
                 if not z.config.is_preview]
        index = self.app_state_service.state.selected_zone_index
        return zones[index]

    async def show_bar_indicator(self, value: int, max_value: int):
        """Show parameter adjustment as bar (0-8 LEDs)"""
        preview_zone = self.zone_service.get_zone(self.preview_zone_id)
        proportion = value / max_value
        lit_count = int(proportion * preview_zone.config.pixel_count)

        pixels = []
        for i in range(preview_zone.config.pixel_count):
            if i < lit_count:
                pixels.append((0, 255, 0))  # Green
            else:
                pixels.append((0, 0, 0))  # Off

        # Direct hardware update (bypass FrameManager)
        self.zone_service._zone_strip_manager.set_zone_pixels(
            preview_zone.config,
            pixels
        )
        self.zone_service._zone_strip_manager.show_all()
```

**Benefits**:
- Preview is normal zone (consistent architecture)
- ~800 lines deleted
- Can control preview via API
- Simplified logic

---

### Files Modified

1. **src/config/zones.yaml** - gpio_chains structure
2. **src/models/enums/zone.py** - Add ZoneID.PREVIEW, ZoneID.NEW_STRIP
3. **src/models/domain/zone.py** - Add gpio_pin, reversed, is_preview
4. **src/components/zone_strip_manager.py** - NEW: Multi-GPIO manager
5. **src/services/preview_service.py** - NEW: Lightweight preview
6. **src/engine/frame_manager.py** - Multi-chain routing
7. **DELETE: src/controllers/preview_panel_controller.py** (570 lines)
8. **DELETE: src/components/preview_panel.py** (100 lines)

---

## Part 3: Parameter System Clarity

### Keep Three-Layer Architecture (It's Good!)

**Why Config/State/Combined is CORRECT**:

```
ParameterConfig (YAML, immutable)
  ↓ What: Type, min, max, step, wraps
  ↓ Purpose: Constraints and metadata
  ↓ Lifetime: Loaded once at startup

ParameterState (JSON, mutable)
  ↓ What: Current value only
  ↓ Purpose: Runtime state
  ↓ Lifetime: Persisted across restarts

ParameterCombined (Runtime, in-memory)
  ↓ What: Business logic (validation, adjustment)
  ↓ Purpose: Rich domain API
  ↓ Lifetime: Reconstructed at startup
```

**Benefits**:
- Config changes don't corrupt state
- Minimal state (just values)
- Rich API for domain logic
- Clear separation of concerns

### Problems to Fix

1. **Verbosity**: `param.state.value` → Add convenience properties
2. **Documentation**: Add clear docstrings explaining pattern
3. **Duplication**: Unify parameter type definitions
4. **Color Params**: Remove (color is state, not parameter)

### Implementation

#### Step 1: Add Convenience Properties (1-2 hours)

```python
# src/models/domain/parameter.py
@dataclass
class ParameterCombined:
    """Combined parameter: Config (constraints) + State (value).

    Three-Layer Pattern:
    ====================
    - Config: Immutable metadata from YAML (type, min, max, step)
    - State: Mutable runtime value from JSON
    - Combined: Business logic (validation, adjustment)

    Why Three Layers?
    -----------------
    Separation: Config changes don't corrupt state files
    Minimal State: JSON stores only values, not metadata
    Rich API: Combined provides domain-friendly methods

    Example:
        >>> param = ParameterCombined(
        ...     config=ParameterConfig(
        ...         id=ParamID.BRIGHTNESS,
        ...         type=ParameterType.PERCENTAGE,
        ...         min=0, max=100, step=10
        ...     ),
        ...     state=ParameterState(id=ParamID.BRIGHTNESS, value=80)
        ... )
        >>> param.value  # Convenience property
        80
        >>> param.adjust(1)  # +10 (one step)
        >>> param.value
        90
    """
    config: ParameterConfig
    state: ParameterState

    # NEW: Convenience properties (proxies to state/config)
    @property
    def value(self) -> Any:
        """Get current value"""
        return self.state.value

    @value.setter
    def value(self, new_value: Any):
        """Set value with validation"""
        if not self.validate(new_value):
            raise ValueError(
                f"Value {new_value} out of range "
                f"[{self.config.min}, {self.config.max}]"
            )
        self.state.value = new_value

    @property
    def id(self) -> ParamID:
        return self.config.id

    @property
    def type(self) -> ParameterType:
        return self.config.type

    @property
    def min(self) -> Optional[float]:
        return self.config.min

    @property
    def max(self) -> Optional[float]:
        return self.config.max

    # Existing methods (unchanged)
    def adjust(self, delta: int) -> None: ...
    def validate(self, value: Any) -> bool: ...
```

**Usage**:
```python
# Before (verbose)
brightness = zone.parameters[ParamID.ZONE_BRIGHTNESS].state.value

# After (clean)
brightness = zone.parameters[ParamID.ZONE_BRIGHTNESS].value
```

---

#### Step 2: Unify Parameter Type Definitions (2-3 hours)

**Problem**: Duplicated definitions

**Solution**: Define types once, reference everywhere

```yaml
# src/config/parameters.yaml

# Reusable parameter type definitions
parameter_types:
  brightness:
    type: PERCENTAGE
    min: 0
    max: 100
    step: 12.5
    default: 100
    unit: "%"
    description: "LED brightness level"

  hue:
    type: ANGLE
    min: 0
    max: 360
    step: 10
    wraps: true
    default: 0
    unit: "°"
    description: "Color hue on HSV wheel"

  speed:
    type: PERCENTAGE
    min: 1
    max: 100
    step: 10
    default: 50
    unit: "%"
    description: "Animation speed"

  intensity:
    type: PERCENTAGE
    min: 0
    max: 100
    step: 10
    default: 100
    unit: "%"
    description: "Effect intensity"

  length:
    type: INTEGER
    min: 1
    max: 20
    step: 1
    default: 5
    unit: "px"
    description: "Effect length in pixels"

# Zone parameter assignments (reference types)
zone_parameters:
  ZONE_BRIGHTNESS:
    type_ref: brightness  # References parameter_types.brightness

# Animation parameter assignments
animation_parameters:
  ANIM_SPEED:
    type_ref: speed

  ANIM_INTENSITY:
    type_ref: intensity

  ANIM_LENGTH:
    type_ref: length
```

**Benefits**:
- DRY: Define once
- Consistent: Same constraints everywhere
- Flexible: Override per-use if needed

---

#### Step 3: Remove Color Parameters (1-2 hours)

**Rationale**: Color is STATE, not parameter

**Delete from parameters.yaml**:
```yaml
# DELETE:
zone_parameters:
  ZONE_COLOR_HUE: ...
  ZONE_COLOR_PRESET: ...

animation_parameters:
  ANIM_PRIMARY_COLOR_HUE: ...
```

**Update Zone Model**:
```python
# src/models/domain/zone.py
@dataclass
class ZoneCombined:
    config: ZoneConfig
    state: ZoneState  # Has color: Color
    parameters: Dict[ParamID, ParameterCombined]  # ONLY brightness

    @property
    def brightness(self) -> int:
        """Convenience: get brightness value"""
        return self.parameters[ParamID.ZONE_BRIGHTNESS].value

    def adjust_color_hue(self, delta: int):
        """Adjust hue (operates on state.color)"""
        if self.state.color.mode == ColorMode.HUE:
            self.state.color = self.state.color.adjust_hue(delta)

    def next_color_preset(self, delta: int, color_manager):
        """Cycle presets (operates on state.color)"""
        if self.state.color.mode == ColorMode.PRESET:
            self.state.color = self.state.color.next_preset(
                delta,
                color_manager
            )
```

---

### Files Modified

1. **src/models/domain/parameter.py** - Convenience properties
2. **src/config/parameters.yaml** - Unified types, remove color
3. **src/models/domain/zone.py** - Color adjustment methods
4. **src/controllers/** - Update color adjustment calls

---

## Part 4: Color System Enhancement

### Goals

1. ✅ Full HSV support (hue, saturation, value)
2. ✅ Color temperature (Kelvin)
3. ✅ Color harmonies (complementary, triadic, etc.)
4. ✅ Perfect conversions (lossless RGB↔HSV)
5. ✅ Enhanced presets (categories, metadata)

### Implementation

#### Step 1: Add Full HSV Support (3-4 hours)

**New ColorMode**:
```python
# src/models/color.py
class ColorMode(Enum):
    HUE = auto()           # Hue only (S=100%, V=100%)
    HSV = auto()           # NEW: Full HSV
    RGB = auto()
    PRESET = auto()
    TEMPERATURE = auto()   # NEW: Kelvin
```

**Update Color Model**:
```python
@dataclass
class Color:
    _hue: Optional[int] = None
    _saturation: Optional[int] = None  # NEW: 0-100
    _value: Optional[int] = None       # NEW: 0-100
    _rgb: Optional[Tuple[int, int, int]] = None
    _preset_name: Optional[str] = None
    _temperature: Optional[int] = None  # NEW: Kelvin
    mode: ColorMode = ColorMode.HUE

    @classmethod
    def from_hsv(cls, h: int, s: int, v: int) -> 'Color':
        """Create from full HSV

        Args:
            h: Hue (0-360°)
            s: Saturation (0-100%)
            v: Value (0-100%)
        """
        return cls(_hue=h, _saturation=s, _value=v, mode=ColorMode.HSV)

    def to_hsv(self) -> Tuple[int, int, int]:
        """Get (h, s, v) tuple"""
        if self.mode == ColorMode.HSV:
            return (self._hue, self._saturation, self._value)
        elif self.mode == ColorMode.HUE:
            return (self._hue, 100, 100)
        elif self.mode == ColorMode.RGB:
            return rgb_to_hsv(*self._rgb)
        # ...
```

**Serialization (Correct Way)**:
```python
# src/utils/serialization.py
class Serializer:
    @staticmethod
    def color_to_dict(color: Color) -> dict:
        """Serialize color to dict"""
        result = {
            "mode": Serializer.enum_to_str(color.mode)
        }

        if color.mode == ColorMode.HUE:
            result["hue"] = color._hue
        elif color.mode == ColorMode.HSV:
            result["hue"] = color._hue
            result["saturation"] = color._saturation
            result["value"] = color._value
        elif color.mode == ColorMode.RGB:
            result["rgb"] = list(color._rgb)
        elif color.mode == ColorMode.PRESET:
            result["preset_name"] = color._preset_name
        elif color.mode == ColorMode.TEMPERATURE:
            result["temperature"] = color._temperature

        return result

    @staticmethod
    def dict_to_color(data: dict, color_manager) -> Color:
        """Deserialize dict to color"""
        mode = Serializer.str_to_enum(data["mode"], ColorMode)

        if mode == ColorMode.HUE:
            return Color.from_hue(data["hue"])
        elif mode == ColorMode.HSV:
            return Color.from_hsv(
                data["hue"],
                data["saturation"],
                data["value"]
            )
        elif mode == ColorMode.RGB:
            return Color.from_rgb(*data["rgb"])
        elif mode == ColorMode.PRESET:
            return Color.from_preset(data["preset_name"], color_manager)
        elif mode == ColorMode.TEMPERATURE:
            return Color.from_temperature(data["temperature"])
```

---

#### Step 2: Add Color Temperature (2-3 hours)

```python
@classmethod
def from_temperature(cls, kelvin: int) -> 'Color':
    """Create from Kelvin temperature

    Examples:
        1800K: Candle
        2700K: Warm white
        5500K: Daylight
        6500K: Cool white
    """
    rgb = temperature_to_rgb(kelvin)
    return cls(_temperature=kelvin, _rgb=rgb, mode=ColorMode.TEMPERATURE)
```

**Conversion Function**:
```python
# src/utils/colors.py
def temperature_to_rgb(kelvin: int) -> Tuple[int, int, int]:
    """Convert Kelvin to RGB (Tanner Helland algorithm)"""
    temp = kelvin / 100.0

    # Red
    if temp <= 66:
        r = 255
    else:
        r = temp - 60
        r = 329.698727446 * (r ** -0.1332047592)
        r = max(0, min(255, r))

    # Green
    if temp <= 66:
        g = temp
        g = 99.4708025861 * math.log(g) - 161.1195681661
    else:
        g = temp - 60
        g = 288.1221695283 * (g ** -0.0755148492)
    g = max(0, min(255, g))

    # Blue
    if temp >= 66:
        b = 255
    elif temp <= 19:
        b = 0
    else:
        b = temp - 10
        b = 138.5177312231 * math.log(b) - 305.0447927307
        b = max(0, min(255, b))

    return (int(r), int(g), int(b))
```

---

#### Step 3: Add Color Harmonies (2-3 hours)

```python
# src/models/color.py
class Color:
    def get_complementary(self) -> 'Color':
        """Opposite on color wheel (180°)"""
        hue = self.to_hue()
        return Color.from_hue((hue + 180) % 360)

    def get_triadic(self) -> List['Color']:
        """Three colors 120° apart"""
        hue = self.to_hue()
        return [
            Color.from_hue(hue),
            Color.from_hue((hue + 120) % 360),
            Color.from_hue((hue + 240) % 360)
        ]

    def get_analogous(self, angle: int = 30) -> List['Color']:
        """Adjacent colors ±angle°"""
        hue = self.to_hue()
        return [
            Color.from_hue((hue - angle) % 360),
            Color.from_hue(hue),
            Color.from_hue((hue + angle) % 360)
        ]
```

---

### Files Modified

1. **src/models/color.py** - HSV, temperature, harmonies
2. **src/utils/colors.py** - Conversion functions
3. **src/utils/serialization.py** - Color serialization
4. **src/managers/color_manager.py** - Categories
5. **src/config/colors.yaml** - Temperature metadata

---

## Implementation Checklist

### Phase 1: Per-Zone Modes (16-23 hours)
- [ ] Add ZoneMode enum
- [ ] Update ZoneState with mode + animation_id
- [ ] Remove global main_mode from ApplicationState
- [ ] Update Serializer for zone mode (NO MAGIC STRINGS)
- [ ] Animation engine frame merging
- [ ] Controller routing refactor
- [ ] Testing

### Phase 2: Multi-GPIO (11-15 hours)
- [ ] Update zones.yaml (gpio_chains structure)
- [ ] Create ZoneStripManager
- [ ] Update FrameManager
- [ ] Delete PreviewPanelController
- [ ] Create PreviewService
- [ ] Testing (both GPIO chains)

### Phase 3: Parameter Clarity (5-7 hours)
- [ ] Add convenience properties
- [ ] Improve documentation
- [ ] Unify parameter types
- [ ] Remove color parameters
- [ ] Testing

### Phase 4: Color Enhancement (10-12 hours)
- [ ] Add HSV support
- [ ] Add temperature support
- [ ] Add harmonies
- [ ] Update Serializer
- [ ] Testing

### Total: 42-57 hours (5-7 days)

---

## Success Criteria

✅ Per-zone autonomous modes working
✅ Multi-GPIO zones rendering correctly
✅ Preview as normal zone (simplified)
✅ Parameters: Clean API + clear docs
✅ Colors: HSV, temperature, harmonies
✅ NO magic strings (all via Serializer)
✅ All tests passing
✅ Hardware verified (GPIO 18 + GPIO 19)
✅ API-ready architecture

---

**Let's make it perfect!** 🎨✨
