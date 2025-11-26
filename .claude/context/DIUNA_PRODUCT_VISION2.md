# 🎨 Diuna - Product Vision & Architecture

## 🎯 Executive Summary

Diuna to ekosystem składający się z dwóch głównych komponentów:
1. **Diuna LED System** - profesjonalny backend do kontroli LED
2. **Diuna App** - frontend demonstracyjny wykorzystujący możliwości systemu

**Kluczowa filozofia:** Separation of concerns - backend jest niezależnym, reużywalnym systemem, który może być używany przez różne frontendy (web, mobile, embedded).

---

## 📦 Component 1: Diuna LED System (Backend/Core)

> "Moje dzieciątko najukochańsze" - profesjonalny system do wyświetlania animacji na ledach ARGB

### 🎯 Core Philosophy

**Hardware-agnostic rendering engine** - system nie wie (i nie musi wiedzieć) czy renderuje na:
- Fizycznych LEDach (Raspberry Pi → WS2811)
- Aplikacji webowej (Canvas/WebGL)
- Simulator w IDE
- Arduino/ESP32/Adafruit

**Platform-independent** - ten sam kod działa na:
- Raspberry Pi (Python)
- Arduino/ESP32 (przyszłość - C++)
- Desktop simulator (Python + GUI)
- Web (przyszłość - WASM?)

---

### 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  DIUNA LED SYSTEM                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │   Zones &    │  │  Animation   │  │   Color     │  │
│  │  ZoneGroups  │  │    Engine    │  │   System    │  │
│  └──────────────┘  └──────────────┘  └─────────────┘  │
│         │                  │                 │         │
│         └──────────────────┴─────────────────┘         │
│                          │                             │
│                  ┌───────▼────────┐                    │
│                  │ Render Engine  │                    │
│                  │  (Hardware-    │                    │
│                  │   Agnostic)    │                    │
│                  └───────┬────────┘                    │
│                          │                             │
│         ┌────────────────┴────────────────┐            │
│         │                                 │            │
│    ┌────▼─────┐                    ┌─────▼────┐       │
│    │ Physical │                    │  Virtual │       │
│    │ Hardware │                    │ Renderer │       │
│    │ (GPIO)   │                    │ (Canvas) │       │
│    └──────────┘                    └──────────┘       │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │          Event System & I/O Layer                │  │
│  │  (Buttons, Encoders, Keyboard, Buzzer, etc.)    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │       State Persistence & Configuration          │  │
│  │         (JSON, YAML, Database)                   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### 🎨 Feature 1: Zones & ZoneGroups System

**Status:** ✅ Core implemented, 🔄 Groups in planning

#### **Zones - Core Concept**

```python
# Zone = isolated LED segment with independent control
Zone {
    id: ZoneID
    name: str
    pixel_range: (start, end)
    color: Color
    brightness: int
    animation: Optional[Animation]
}

# Examples:
Zone(id=FLOOR, name="Floor Strip", range=(0, 45))
Zone(id=LAMP, name="Desk Lamp", range=(45, 90))
Zone(id=SLEEVE_LEFT, name="Left Sleeve", range=(0, 30))
```

**Key capabilities:**
- **Independent control** - każda strefa ma swój kolor, brightness, animację
- **Pixel-level precision** - każdy piksel może być swoją strefą
- **Autonomous rendering** - strefy mogą działać niezależnie
- **Overlapping support** (future) - jedna dioda w wielu strefach (layering)

#### **ZoneGroups - Advanced Concept**

```python
# ZoneGroup = logical grouping of zones for coordinated control
ZoneGroup {
    id: str
    name: str
    zones: List[ZoneID]
    blend_mode: BlendMode  # How zones interact
    master_control: bool   # Can override individual zones
}

# Examples:
ZoneGroup(
    id="ALL_SLEEVES",
    zones=[SLEEVE_LEFT, SLEEVE_RIGHT],
    blend_mode=SYNC  # Same animation
)

ZoneGroup(
    id="FULL_GARMENT",
    zones=[SLEEVE_LEFT, SLEEVE_RIGHT, FRONT, BACK, HOOD],
    blend_mode=WAVE  # Animation flows through zones
)
```

**Scalability principle:**
- **Granular:** 1 pixel = 1 zone (maximum control)
- **Coarse:** All pixels = 1 zone (unified control)
- **Flexible:** Any combination in between

**Use cases:**
- Fashion: Left sleeve + right sleeve = coordinated movement
- Installation: Multiple strips acting as one big canvas
- Performance: Reduce computation by grouping static zones

---

### 🎬 Feature 2: Animation Engine

**Status:** ✅ Implemented, 🔄 Continuously expanding

> "DRUGIE SEDNO APLIKACJI"

#### **Animation Types**

**Current Presets:**
```
✅ BREATHE     - Gentle fade in/out (relaxing, ambient)
✅ COLOR_CYCLE - Rainbow through hue spectrum
✅ FADE        - Smooth transition between colors
✅ SNAKE       - Moving pattern (chase effect)
✅ SPARKLE     - Random pixel twinkles
✅ WAVE        - Traveling wave pattern
```

**Future Presets:**
```
🔄 FIRE        - Flickering flame effect
🔄 LIGHTNING   - Random flash bursts
🔄 AURORA      - Northern lights simulation
🔄 PULSE       - Beat-synchronized flash
🔄 STROBE      - Adjustable strobe effect
🔄 MATRIX      - Digital rain (for matrix displays)
```

#### **Configuration System**

Every animation is **fully parametrizable:**

```python
Animation {
    id: AnimationID
    name: str
    parameters: {
        "speed": Parameter(min=0.1, max=10.0, default=1.0),
        "color_primary": ColorParameter(default=Color.RED),
        "color_secondary": ColorParameter(default=Color.BLUE),
        "direction": EnumParameter(values=[LEFT, RIGHT, UP, DOWN]),
        "intensity": Parameter(min=0, max=100, default=50)
    }
}

# Example usage:
breathe = Animation(
    id=BREATHE,
    params={
        "speed": 0.5,      # Slow breathing
        "color_primary": Color.from_hue(240),  # Blue
        "intensity": 30    # Subtle
    }
)
```

**Parameter types:**
- `FloatParameter` - numeric values with range
- `ColorParameter` - color selection (any mode)
- `EnumParameter` - discrete choices
- `BoolParameter` - on/off toggles
- `ListParameter` - multiple values (e.g., color palette)

#### **Save/Load System - Critical Feature**

> "możliwość eksportu i odpalenia 'u siebie' - to będzie jedna z najważniejszych funkcji"

**Export formats:**

```json
// .diuna - Native format (lossless)
{
  "version": "1.0.0",
  "animation": {
    "id": "BREATHE",
    "name": "Subtle Ember Glow",
    "parameters": {
      "speed": 0.5,
      "color_primary": {"mode": "HUE", "hue": 0, "brightness": 30},
      "intensity": 20
    }
  },
  "zones": [
    {"id": "SLEEVE_LEFT", "pixel_count": 30, "shape": "line"},
    {"id": "SLEEVE_RIGHT", "pixel_count": 30, "shape": "line"}
  ],
  "metadata": {
    "author": "harki",
    "created": "2024-11-25T20:00:00Z",
    "tags": ["subtle", "wearable", "ember"]
  }
}
```

```cpp
// .ino - Arduino/FastLED export
// AUTO-GENERATED by Diuna LED System
// Animation: Subtle Ember Glow

#include <FastLED.h>

#define NUM_LEDS 60
#define DATA_PIN 6

CRGB leds[NUM_LEDS];

void setup() {
  FastLED.addLeds<WS2812B, DATA_PIN, GRB>(leds, NUM_LEDS);
}

void loop() {
  // Breathe animation - Subtle Ember Glow
  uint8_t brightness = beatsin8(30, 10, 50); // Speed: 0.5
  fill_solid(leds, NUM_LEDS, CHSV(0, 255, brightness)); // Hue: 0 (red)
  FastLED.show();
  delay(20);
}
```

```python
# .py - Python export (for other Raspberry Pi setups)
# AUTO-GENERATED by Diuna LED System

from diuna import Animation, Color, Zone

animation = Animation.BREATHE.configure(
    speed=0.5,
    color_primary=Color.from_hue(0, brightness=30),
    intensity=20
)

zones = [
    Zone(id="SLEEVE_LEFT", pixels=30),
    Zone(id="SLEEVE_RIGHT", pixels=30)
]

# Run animation
animation.apply_to_zones(zones)
animation.start()
```

**Sharing workflow:**
1. User creates animation in Diuna App
2. Exports to `.diuna` file
3. Uploads to community/cloud/local storage
4. Other user downloads `.diuna` file
5. Imports to their Diuna System
6. Runs on their hardware (regardless of platform)

**Import sources:**
- Local file upload
- URL (direct link)
- QR code (embedded preset)
- Community library (future)
- Git repository (for version control)

---

### 🎨 Feature 3: Color System

**Status:** ✅ Core implemented, 🔄 Palettes in development

> "PIERWSZE SEDNO APLIKACJI"

#### **Color Modes**

```python
class ColorMode(Enum):
    RGB     # Standard (r, g, b) - 0-255
    HSV     # Hue, Saturation, Value (h: 0-360, s/v: 0-100)
    HUE     # Hue-only (simplified HSV, max saturation)
    PRESET  # Named presets (RED, BLUE, WARM_WHITE, etc.)
    # Future:
    TEMP    # Color temperature in Kelvin (1800-10000K)
    CIE_XY  # Professional color space
```

**Why multiple modes?**
- **RGB:** Direct control, intuitive for developers
- **HSV:** Best for animations (rotate hue, keep saturation/value)
- **HUE:** Simplified for quick rainbow effects
- **PRESET:** User-friendly named colors
- **TEMP:** Warm/cool whites for ambient lighting

#### **Brightness - The Magic**

> "BRIGHTNESS = magia"

**Why brightness is special:**

```python
# Traditional approach (bad):
color = (255, 0, 0)  # Red at full brightness
# To dim: (128, 0, 0)  # Changes color perception!

# Diuna approach (good):
color = Color.from_rgb(255, 0, 0)  # Define pure red
brightness = 128  # Separate brightness control
# Result: Pure red hue preserved, only intensity changes
```

**Brightness features:**
- **Independent control** - adjust brightness without touching color
- **Per-zone brightness** - each zone has its own level
- **Global brightness** - master control for all zones
- **Smooth transitions** - fade brightness independently
- **Power management** - limit max brightness to save power

**Advanced brightness:**
```python
# Automatic brightness adjustment
brightness_curve = {
    "linear": lambda x: x,                    # Direct mapping
    "exponential": lambda x: x ** 2,          # More gradual at low end
    "logarithmic": lambda x: log(x + 1),      # Perceptually linear
    "custom": load_curve_from_file()          # User-defined
}
```

#### **Color Palettes System (Future)**

> "predefiniowane, tematyczne, fajne narzędzia będą do tworzenia palet"

**Palette structure:**

```python
class ColorPalette:
    id: str
    name: str
    colors: List[Color]  # 3-8 colors
    theme: PaletteTheme  # WARM, COOL, NATURE, URBAN, etc.
    author: str
    tags: List[str]
    
    # Methods:
    def interpolate(self, position: float) -> Color:
        """Get color at position 0.0-1.0 along palette"""
        
    def gradient(self, steps: int) -> List[Color]:
        """Generate smooth gradient"""
        
    def random(self) -> Color:
        """Pick random color from palette"""
```

**Palette creation tools:**

1. **Manual creation:**
   - Pick 3-5 colors
   - Arrange in order
   - Name and save

2. **From photo:**
   - Upload image
   - K-means clustering
   - Extract 3-5 dominant colors
   - Auto-name based on dominance

3. **Algorithmic generation:**
   - Complementary (opposite on color wheel)
   - Analogous (adjacent colors)
   - Triadic (120° apart)
   - Split-complementary
   - Tetradic (square/rectangle)

4. **From existing art:**
   - Import from Adobe Color
   - Import from Coolors.co
   - Import from Pantone
   - Import from photo libraries

**Palette usage:**

```python
# Apply palette to animation
animation = ColorCycle(
    palette=Palette.SUNSET,  # Auto-cycle through palette colors
    speed=1.0
)

# Apply palette to zones
zone_group.apply_palette(
    palette=Palette.OCEAN,
    mode=GRADIENT  # or DISCRETE, RANDOM
)
```

**Sharing & Distribution:**
- Export palette as `.dpal` file
- Share via URL/QR code
- Publish to community library
- Import from popular palette sites

---

### 🔄 Feature 4: Transition System

**Status:** ✅ Implemented, 🔄 Expanding

> "płynne przejścia pomiędzy animacjami, kolorami, dowolnymi dwoma elementami"

#### **Transition Types**

```python
class TransitionType(Enum):
    # Basic
    FADE          # Linear fade (alpha blending)
    CUT           # Instant (no transition)
    
    # Directional
    WIPE_LEFT     # Wipe from left to right
    WIPE_RIGHT    # Wipe right to left
    WIPE_CENTER   # Expand from center
    
    # Organic
    SPARKLE       # Random pixels fade in
    RIPPLE        # Wave propagation
    DISSOLVE      # Random pixel crossfade
    
    # Advanced
    MORPH         # Shape morphing
    ZOOM          # Scale effect
    SPIRAL        # Rotation effect
```

#### **Easing Functions**

```python
class EasingFunction(Enum):
    LINEAR        # Constant speed
    EASE_IN       # Start slow, accelerate
    EASE_OUT      # Start fast, decelerate
    EASE_IN_OUT   # Slow → fast → slow
    CUBIC         # Smooth cubic curve
    ELASTIC       # Bouncy overshoot
    BOUNCE        # Bouncing effect
```

#### **Use Cases**

**Between animations:**
```python
# Fade from BREATHE to COLOR_CYCLE over 2 seconds
transition = Transition(
    from_animation=BREATHE,
    to_animation=COLOR_CYCLE,
    duration=2.0,
    type=FADE,
    easing=EASE_IN_OUT
)
```

**Between colors:**
```python
# Smooth color transition
zone.transition_to_color(
    target_color=Color.BLUE,
    duration=1.5,
    easing=EASE_OUT
)
```

**Between states:**
```python
# Scene change with ripple effect
system.transition_to_scene(
    scene=MOVIE_MODE,
    transition=RIPPLE,
    duration=3.0,
    origin=CENTER  # Start ripple from center
)
```

**Power events:**
```python
# Shutdown with fade-out
system.power_off(
    transition=FADE,
    duration=2.0,
    final_color=BLACK
)
```

---

### 🔌 Feature 5: Hardware Support

**Status:** ✅ WS2811/WS2812, 🔄 Expanding

#### **Currently Supported**

**LED Types:**
```
✅ WS2811  - Addressable RGB LED strip (12V)
✅ WS2812B - Addressable RGB LED (NeoPixel, 5V)
✅ Individual pixels - 5050, 3535, 2020, 1515 packages
```

**Microcontrollers:**
```
✅ Raspberry Pi - Primary platform (Python)
   - GPIO control via rpi_ws281x library
   - Hardware PWM support
   - Multi-channel support (2 strips independent)
```

#### **Future Support**

**LED Types:**
```
🔄 WS2813   - Improved WS2812 (backup data line)
🔄 APA102   - SPI-based, faster refresh (10-20 kHz)
🔄 SK6812   - RGBW (white channel)
🔄 WS2815   - 12V addressable (longer runs)
```

**Light Technologies:**
```
🔄 Fiber Optics - For continuous glow (wearables)
   - End-glow fibers
   - Side-glow fibers
   - LED coupling adapters
   
🔄 EL Wire - Electroluminescent (if controllable via TRIAC)
🔄 LED Neon Flex - For larger installations
```

**Microcontroller Platforms:**
```
🔄 Arduino - C++ port of Diuna
   - ESP32 (WiFi + BLE)
   - ESP8266 (WiFi)
   - Arduino Uno/Mega
   
🔄 Adafruit Boards
   - FLORA
   - GEMMA M0
   - Circuit Playground
   
🔄 Teensy - High-performance alternative
```

#### **Fiber Optic Integration**

> Kluczowe dla subtle wearables aesthetic

**Setup:**
```python
# 1 RGB LED source → many fiber optic strands
fiber_zone = FiberOpticZone(
    led_source=GPIO_PIN_18,      # Single RGB LED
    fiber_count=20,               # 20 strands
    fiber_length=0.5,             # 50cm per strand
    glow_type=SIDE_GLOW,          # Along entire length
    placement="seam"              # Where fibers go
)

# Render to fiber zone - system handles brightness/loss
fiber_zone.set_color(Color.from_hue(0, brightness=20))
# Result: All 20 fibers glow red along seams
```

**Considerations:**
- Light loss over distance (~30% per meter)
- Need for light coupling (LED → fiber interface)
- Multiple fibers from single source (star topology)
- Diffusion vs. focused endpoint

---

### 💾 Feature 6: State Persistence & Configuration

**Status:** ✅ Implemented

#### **State Management**

```yaml
# state.json - Runtime state (changes frequently)
{
  "zones": {
    "FLOOR": {
      "color": {"mode": "HUE", "hue": 240},
      "brightness": 200,
      "enabled": true
    },
    "LAMP": {
      "color": {"mode": "RGB", "rgb": [255, 100, 50]},
      "brightness": 150
    }
  },
  "animations": {
    "COLOR_CYCLE": {
      "active": true,
      "parameters": {
        "speed": 1.5,
        "zones": ["FLOOR"]
      }
    }
  },
  "system": {
    "main_mode": "ANIMATION",
    "power_state": "ON",
    "last_updated": "2024-11-25T20:30:00Z"
  }
}
```

```yaml
# config.yaml - Hardware configuration (rarely changes)
zones:
  - id: FLOOR
    display_name: "Floor Strip"
    pixel_count: 45
    start_pixel: 0
    enabled: true
    
  - id: LAMP
    display_name: "Desk Lamp"
    pixel_count: 45
    start_pixel: 45
    enabled: true

hardware:
  led_strip:
    type: WS2811
    gpio_pin: 18
    total_pixels: 90
    frequency: 800_000  # 800 kHz
    dma: 10
    
  rotary_encoder:
    clk_pin: 17
    dt_pin: 27
    sw_pin: 22
    
system:
  frame_rate: 60  # FPS
  brightness_limit: 255
  power_limit_watts: 60
```

#### **Persistence Features**

**Auto-save:**
- State persists every N seconds (debounced)
- Or on significant events (animation change, power off)
- Graceful shutdown saves current state

**State restoration:**
- On boot: load last state
- Resume animations where they left off
- Restore brightness levels
- Maintain zone configurations

**Configuration hot-reload:**
- Edit YAML without restart (future)
- Validate before applying
- Rollback on error

**Backup & versioning:**
```bash
# Automatic backups
state/
  state.json           # Current
  state.json.backup    # Previous
  state.json.2024-11-25_20-30-00  # Timestamped

# Config history
config/
  config.yaml
  config.yaml.v1
  config.yaml.v2
```

---

### 🎮 Feature 7: Event System

**Status:** ✅ Core implemented, 🔄 Expanding

#### **Event Architecture**

```python
class EventType(Enum):
    # Input Events
    BUTTON_PRESS
    BUTTON_RELEASE
    BUTTON_LONG_PRESS
    ENCODER_ROTATE
    ENCODER_CLICK
    KEYBOARD_KEY
    
    # System Events
    ZONE_COLOR_CHANGED
    ANIMATION_STARTED
    ANIMATION_STOPPED
    BRIGHTNESS_CHANGED
    MODE_CHANGED
    POWER_STATE_CHANGED
    
    # Hardware Events
    LED_STRIP_READY
    LED_STRIP_ERROR
    HARDWARE_CONNECTED
    HARDWARE_DISCONNECTED
    
    # Future: External Events
    WEBSOCKET_MESSAGE
    API_REQUEST
    MQTT_MESSAGE
    SENSOR_TRIGGERED
```

#### **Event Flow**

```python
# Publisher (hardware/input)
button.on_press(lambda: event_bus.publish(
    EventType.BUTTON_PRESS,
    data={"button_id": "MAIN", "timestamp": time.now()}
))

# Subscriber (controller/logic)
event_bus.subscribe(
    EventType.BUTTON_PRESS,
    handler=power_toggle_controller.handle_button,
    priority=EventPriority.HIGH
)

# Handler
def handle_button(event: Event):
    if event.data["button_id"] == "MAIN":
        system.toggle_power()
```

#### **Physical Inputs**

**Currently supported:**

```python
# Button
Button(
    gpio_pin=23,
    pull_up=True,
    debounce_ms=50,
    long_press_ms=1000
)
# Events: PRESS, RELEASE, LONG_PRESS

# Rotary Encoder
RotaryEncoder(
    clk_pin=17,
    dt_pin=27,
    sw_pin=22  # Push button
)
# Events: ROTATE (direction, steps), CLICK

# Keyboard (for dev/testing)
KeyboardAdapter(
    key_mappings={
        "UP": "brightness_increase",
        "DOWN": "brightness_decrease",
        "LEFT": "hue_decrease",
        "RIGHT": "hue_increase",
        "SPACE": "toggle_animation",
        "ENTER": "cycle_mode"
    }
)
```

#### **Physical Outputs**

```python
# Buzzer
Buzzer(gpio_pin=24)
buzzer.beep(duration=0.1)  # Short confirmation
buzzer.pattern([0.1, 0.1, 0.1])  # Three beeps

# LED indicator
StatusLED(gpio_pin=25)
status_led.on()
status_led.blink(interval=0.5)
status_led.pulse(speed=1.0)

# LED Strip (main output)
ZoneStrip.set_zone_color(zone_id, r, g, b)
ZoneStrip.show()  # Update physical LEDs
```

#### **Future: External Event Sources**

```python
# Mobile app (WebSocket)
websocket.on_message(lambda msg: event_bus.publish(
    EventType.WEBSOCKET_MESSAGE,
    data=msg
))

# Web app (REST API)
api.on_request("/zones/FLOOR/color", lambda req: 
    zone_service.set_color(ZoneID.FLOOR, req.color)
)

# Sensors (for wearables)
heart_rate_sensor.on_change(lambda bpm:
    event_bus.publish(EventType.HEART_RATE_CHANGED, {"bpm": bpm})
)

# MQTT (home automation)
mqtt.subscribe("home/led/command", lambda msg:
    command_parser.execute(msg)
)
```

---

## 📱 Component 2: Diuna App (Frontend)

> "To będzie demonstracyjna wersja aplikacji korzystającej z Diuna LED System"

### 🎯 Purpose

**Diuna App** = Showcase + Control Interface dla Diuna LED System

**Not a separate product** - to narzędzie do:
1. Demonstracji możliwości systemu
2. Real-time kontroli hardware
3. Wizualizacji stanu systemu
4. Prototypowania UI patterns

**Key principle:** Frontend może być wymieniony - system działa bez niego.

---

### 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     DIUNA APP                           │
│                   (Frontend Demo)                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────────────────────────────────────────┐    │
│  │        React UI Components                     │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐  │    │
│  │  │  Zone    │ │Animation │ │   Color      │  │    │
│  │  │ Control  │ │ Control  │ │   Picker     │  │    │
│  │  └──────────┘ └──────────┘ └──────────────┘  │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐  │    │
│  │  │  Visual  │ │  System  │ │  Settings    │  │    │
│  │  │  Canvas  │ │  Status  │ │   Panel      │  │    │
│  │  └──────────┘ └──────────┘ └──────────────┘  │    │
│  └────────────────────────────────────────────────┘    │
│                          │                             │
│  ┌────────────────────────────────────────────────┐    │
│  │          Communication Layer                   │    │
│  │                                                │    │
│  │  WebSocket  ◄──► Real-time state sync         │    │
│  │  REST API   ◄──► Commands & queries           │    │
│  │  Events     ◄──► Bidirectional updates        │    │
│  └────────────────────────────────────────────────┘    │
│                          │                             │
└──────────────────────────┼─────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │   Diuna LED System       │
            │      (Backend)           │
            └──────────────────────────┘
```

---

### 🛠️ Technology Stack

```javascript
// Frontend Framework
React 18                  // Modern React with hooks
TypeScript                // Type safety
Vite                      // Fast build tool

// UI Components
Tailwind CSS              // Utility-first styling
Shadcn/ui                 // Beautiful components
Radix UI                  // Headless primitives
Lucide React              // Icon library

// State Management
Zustand                   // Lightweight global state
TanStack Query            // Server state & caching
Jotai                     // Atomic state (forms)

// Communication
Socket.IO Client          // WebSocket (real-time)
Axios                     // REST API calls

// Canvas/Visualization
React Konva               // 2D canvas manipulation
// or Fabric.js           // Alternative
// or Three.js            // 3D preview (future)

// Animations
Framer Motion             // UI transitions
GSAP                      // Complex animations

// Color Tools
Culori                    // Color space conversions
react-colorful            // Color picker
```

---

### 🎨 Core Features

#### **1. Real-Time Visualization**

> "Wyświetlanie reprezentacji graficznej systemu"

**Visual Canvas:**
```tsx
<LEDCanvas>
  {/* Real-time LED representation */}
  <Zone id="FLOOR" pixels={45} layout="horizontal" />
  <Zone id="LAMP" pixels={45} layout="vertical" />
  
  {/* Live color updates via WebSocket */}
  {zones.map(zone => (
    <ZoneVisualization
      key={zone.id}
      zone={zone}
      liveColors={true}  // Updates 60fps
      interactive={true}  // Click to select
    />
  ))}
</LEDCanvas>
```

**System Status:**
```tsx
<SystemStatus>
  <Metric label="FPS" value={60} />
  <Metric label="Frame Time" value="2.1ms" />
  <Metric label="Power Draw" value="18W" />
  <Metric label="Brightness" value="80%" />
  <Metric label="Mode" value="ANIMATION" />
</SystemStatus>
```

#### **2. Control Interfaces**

**Zone Control:**
```tsx
<ZoneControlPanel zone={selectedZone}>
  <ColorPicker
    color={zone.color}
    onChange={handleColorChange}
    modes={["RGB", "HSV", "HUE", "PRESET"]}
  />
  
  <BrightnessSlider
    value={zone.brightness}
    onChange={handleBrightnessChange}
  />
  
  <QuickActions>
    <Button onClick={turnOff}>Off</Button>
    <Button onClick={maxBrightness}>Max</Button>
    <Button onClick={cyclePresets}>Next Preset</Button>
  </QuickActions>
</ZoneControlPanel>
```

**Animation Control:**
```tsx
<AnimationPanel>
  <AnimationList>
    {animations.map(anim => (
      <AnimationCard
        animation={anim}
        onPlay={handlePlay}
        onStop={handleStop}
        isActive={anim.id === activeAnimation}
      />
    ))}
  </AnimationList>
  
  <AnimationParameters animation={selected}>
    <Slider label="Speed" param="speed" />
    <ColorPicker label="Primary Color" param="color_primary" />
    <ColorPicker label="Secondary Color" param="color_secondary" />
  </AnimationParameters>
</AnimationPanel>
```

#### **3. WebSocket Integration**

**Bidirectional Communication:**

```typescript
// Client → Server (Commands)
socket.emit('zone:set_color', {
  zone_id: 'FLOOR',
  color: { mode: 'HUE', hue: 240 }
});

socket.emit('animation:start', {
  animation_id: 'COLOR_CYCLE',
  params: { speed: 1.5 }
});

// Server → Client (State Updates)
socket.on('zone:state_changed', (data) => {
  updateZoneState(data.zone_id, data.state);
});

socket.on('animation:frame', (data) => {
  renderFrame(data.pixels); // Real-time visual update
});

socket.on('system:status', (data) => {
  updateSystemMetrics(data);
});
```

**State Synchronization:**
- **60 FPS visual updates** - smooth animation preview
- **Zero-latency commands** - instant response to user input
- **Automatic reconnection** - handle network interruptions
- **State reconciliation** - sync after disconnect

#### **4. REST API Integration**

**CRUD Operations:**

```typescript
// GET - Fetch current state
const zones = await api.get('/zones');
const animations = await api.get('/animations');
const system = await api.get('/system');

// PUT - Update state
await api.put('/zones/FLOOR/color', {
  color: { mode: 'RGB', rgb: [255, 0, 0] }
});

// POST - Trigger actions
await api.post('/animations/COLOR_CYCLE/start', {
  zones: ['FLOOR', 'LAMP'],
  speed: 2.0
});

// DELETE - Remove custom items
await api.delete('/presets/my-custom-preset');
```

**React Query Integration:**

```typescript
// Automatic caching + background refetch
const { data: zones, isLoading } = useQuery({
  queryKey: ['zones'],
  queryFn: () => api.get('/zones'),
  refetchInterval: 5000  // Fallback polling (WebSocket primary)
});

// Optimistic updates
const updateZone = useMutation({
  mutationFn: (data) => api.put(`/zones/${data.id}`, data),
  onMutate: async (newZone) => {
    // Cancel refetch
    await queryClient.cancelQueries(['zones']);
    
    // Snapshot previous value
    const previous = queryClient.getQueryData(['zones']);
    
    // Optimistically update
    queryClient.setQueryData(['zones'], (old) => 
      old.map(z => z.id === newZone.id ? newZone : z)
    );
    
    return { previous };
  },
  onError: (err, newZone, context) => {
    // Rollback on error
    queryClient.setQueryData(['zones'], context.previous);
  }
});
```

---

### 🎯 UI/UX Principles

**Design Philosophy:**
1. **Real-time feedback** - see changes instantly
2. **Visual-first** - show, don't tell
3. **Touch-friendly** - large targets, gestures
4. **Responsive** - works on phone, tablet, desktop
5. **Accessible** - keyboard nav, screen readers

**Key Screens:**

```
Dashboard
├── Live Preview (Canvas showing all zones)
├── Quick Controls (Brightness, Power, Mode)
├── Zone Cards (Grid of zones with previews)
└── System Status (FPS, Power, Uptime)

Zone Detail
├── Large Preview
├── Color Picker (All modes)
├── Brightness Slider
├── Quick Actions
└── Animation Assignment

Animation Browser
├── Animation Cards (with GIF previews)
├── Search & Filter
├── Parameter Editor
└── Save/Load Presets

Settings
├── System Configuration
├── Hardware Setup
├── Network Settings
└── Debug Tools
```

---

## 🗺️ Development Roadmap

### ✅ Phase 1-7: Foundation (COMPLETED)

- ✅ Core Zone system
- ✅ Animation engine
- ✅ Color system (RGB, HSV, HUE, PRESET)
- ✅ Transition system
- ✅ Event system
- ✅ State persistence
- ✅ Hardware integration (WS2811, Raspberry Pi)
- ✅ Unified rendering (FrameManager)

### 🔄 Phase 8: Backend Refinement (IN PROGRESS)

**Current Focus:** Architecture cleanup & API preparation

- 🔄 Dependency injection refactor
- 🔄 Enum serialization centralization
- 🔄 Save debouncing
- 🔄 FastAPI layer setup
- 🔄 WebSocket server implementation

**Timeline:** 2-3 weeks

### 📋 Phase 9: Frontend MVP (NEXT)

**Goal:** Working Diuna App with core features

**Week 1-2:**
- [ ] Project setup (React + Vite + TypeScript)
- [ ] Design system & component library
- [ ] WebSocket client implementation
- [ ] Basic dashboard layout

**Week 3-4:**
- [ ] Zone control components
- [ ] Color picker (all modes)
- [ ] Live preview canvas
- [ ] System status display

**Week 5-6:**
- [ ] Animation browser
- [ ] Animation control panel
- [ ] Parameter editors
- [ ] Polish & testing

**Deliverable:** Functional web app controlling physical LED setup

### 📋 Phase 10: Advanced Features

**Timeline:** Ongoing, parallel development

#### **Backend Expansions:**
- [ ] ZoneGroups implementation
- [ ] Advanced animations (Fire, Lightning, Aurora)
- [ ] Color palette system
- [ ] Fiber optic support
- [ ] Multi-platform export (Arduino, ESP32)
- [ ] Animation marketplace/library

#### **Frontend Enhancements:**
- [ ] 3D preview (Three.js)
- [ ] Timeline editor (keyframe-based)
- [ ] Preset management
- [ ] Community features
- [ ] Mobile app (React Native/Flutter)
- [ ] Wearables garment designer

#### **Integration & Ecosystem:**
- [ ] Home automation (MQTT, Home Assistant)
- [ ] Voice control (Alexa, Google Home)
- [ ] Music synchronization
- [ ] External sensors
- [ ] Cloud sync

---

## 🎯 Target Use Cases

### 1. **Personal LED Installation** (Current Primary)
- Home ambient lighting
- Desk/gaming setup
- Room decoration
- Mood lighting

**User:** Tech-savvy individual, hobbyist
**Hardware:** Raspberry Pi + LED strips
**Interface:** Diuna App (web) + physical controls

### 2. **Wearable Fashion** (Future Vision)
- LED-integrated clothing
- Subtle glow effects
- Fashion shows / performances
- Smart garments

**User:** Fashion designer, performer, artist
**Hardware:** Small microcontroller (ESP32/FLORA) + discrete LEDs/fibers
**Interface:** Mobile app (preset selection) or pre-programmed

### 3. **Art Installations**
- Large-scale LED sculptures
- Interactive exhibits
- Museum displays
- Public art

**User:** Artists, exhibition designers
**Hardware:** Multiple Raspberry Pi nodes (distributed)
**Interface:** Web app + custom control interfaces

### 4. **Commercial / Entertainment**
- Stage lighting
- Club/bar ambiance
- Retail displays
- Event production

**User:** Lighting designers, technicians
**Hardware:** Professional controllers + DMX integration
**Interface:** DMX console + Diuna backend

---

## 🔑 Key Differentiators

### **vs. WLED:**
- ✅ **Zone-centric** vs. segment-based
- ✅ **Platform-agnostic** rendering engine
- ✅ **Python-first** (better for AI/data integration)
- ✅ **Export system** (share animations as code)
- ✅ **Advanced color system** (multiple modes, palettes)

### **vs. FastLED:**
- ✅ **Higher-level API** (easier to use)
- ✅ **Cross-platform** (not Arduino-only)
- ✅ **Real-time control** (WebSocket API)
- ✅ **State persistence** (remembers settings)
- ✅ **Transition system** (smooth changes)

### **vs. Commercial Controllers:**
- ✅ **Open source** (free, customizable)
- ✅ **Programmable** (not locked to presets)
- ✅ **Extensible** (add your own animations)
- ✅ **Community-driven** (share presets)
- ✅ **Developer-friendly** (Python API)

---

## 📝 Design Principles

### **1. Separation of Concerns**
- Backend = Logic, rendering, hardware
- Frontend = Presentation, user interaction
- Communication = WebSocket/REST API

**Benefit:** Can swap frontend, add multiple interfaces

### **2. Hardware Agnostic**
- Render engine doesn't care about physical LEDs
- Same code runs on Pi, simulator, web canvas
- Easy to port to new platforms

**Benefit:** Development without hardware, cross-platform

### **3. Export First**
- Every configuration/animation is exportable
- Presets are first-class citizens
- Share-ability built into core

**Benefit:** Community growth, ecosystem development

### **4. Type Safety**
- TypeScript frontend
- Python type hints backend
- Enums for all IDs

**Benefit:** Fewer bugs, better IDE support

### **5. Real-Time by Default**
- WebSocket for state sync
- 60 FPS rendering
- Instant feedback

**Benefit:** Professional feel, smooth UX

---

## 🚀 Getting Started (For Developers)

### **Run Diuna LED System:**

```bash
# Clone repository
git clone https://github.com/yourusername/diuna.git
cd diuna/backend

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run system (without hardware)
python src/main_asyncio.py --simulator

# Run with hardware (Raspberry Pi)
python src/main_asyncio.py
```

### **Run Diuna App:**

```bash
# Navigate to frontend
cd diuna/frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

### **Connect App to System:**

```typescript
// frontend/src/config.ts
export const DIUNA_BACKEND_URL = "http://localhost:8000";
export const WEBSOCKET_URL = "ws://localhost:8000/ws";
```

---

## 📚 Documentation Structure

```
docs/
├── architecture/
│   ├── backend-architecture.md
│   ├── frontend-architecture.md
│   └── communication-protocol.md
│
├── api/
│   ├── rest-api.md          # OpenAPI spec
│   ├── websocket-api.md     # WebSocket messages
│   └── event-system.md      # Event types & handlers
│
├── guides/
│   ├── getting-started.md
│   ├── creating-animations.md
│   ├── color-system.md
│   ├── hardware-setup.md
│   └── deployment.md
│
├── reference/
│   ├── configuration.md
│   ├── cli-commands.md
│   └── troubleshooting.md
│
└── development/
    ├── contributing.md
    ├── code-style.md
    ├── testing.md
    └── roadmap.md
```

---

## 🎯 Success Metrics

### **Technical:**
- ✅ 60 FPS stable rendering
- ✅ < 50ms command latency
- ✅ < 200 MB memory usage
- ✅ Cross-platform compatibility

### **User Experience:**
- [ ] < 5 minutes first animation
- [ ] < 10 minutes to understand system
- [ ] 100% feature discoverability
- [ ] Zero config for basic usage

### **Community:**
- [ ] 100+ animation presets
- [ ] 50+ color palettes
- [ ] Active user contributions
- [ ] Documentation completeness

---

## 📞 Contact & Community

**Project Lead:** Harki  
**Status:** Active Development  
**License:** TBD (Open Source planned)

**Links:**
- Repository: (TBD)
- Documentation: (TBD)
- Community Forum: (TBD)
- Discord: (TBD)

---

## 🔮 Long-Term Vision

**Year 1:** Diuna LED System + App (MVP)
- Solid backend with all core features
- Working web app
- Community starting to form

**Year 2:** Ecosystem Growth
- Mobile app (iOS/Android)
- Arduino/ESP32 ports
- Animation marketplace
- 1000+ users

**Year 3:** Platform Maturity
- Professional integrations (DMX, Art-Net)
- Commercial licensing
- Hardware partnerships (LED manufacturers)
- Industry recognition

**Ultimate Goal:**
> Diuna becomes the **de-facto standard** for programmable LED control - the system that everyone recommends when they want professional, beautiful, extensible lighting.

---

*This is a living document - updated as the project evolves.*

**Last Updated:** 2024-11-25  
**Version:** 1.0.0  
**Status:** 🔄 In Active Development
