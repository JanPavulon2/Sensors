# 🎨 Diuna - Comprehensive Vision & Technical Roadmap

## Executive Summary

Diuna has evolved from a hobby LED controller into a **professional-grade IoT lighting system** with strong architectural foundations. This document outlines the complete vision for transforming it into a **production-ready, extensible, beautiful** application.

---

## 🎯 Core Philosophy

### The Three Pillars

1. **Color & Light Mastery**
   - LEDs are not just "on/off" - they're an art medium
   - Every color operation must be **precise, predictable, and beautiful**
   - Support for RGB, HSV, HSL, color temperature, CIE XYZ, and advanced color science

2. **Hardware-First, Software-Smart**
   - Respect physical constraints (WS2811 timing, power limits)
   - Abstract hardware properly (easy to add new LED types)
   - Performance matters: 60 FPS rendering, <2ms latency

3. **User Experience Excellence**
   - Physical controls must feel **instant and smooth**
   - Web UI must be **gorgeous and responsive**
   - System must be **intuitive** even for non-technical users

---

## 🏗️ Architecture Evolution

### Current State (Phase 7 - DONE ✅)
```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Infrastructure (Config, Events, Logging, GPIO)     │
│ Layer 3: Application (Controllers, Orchestration)           │
│ Layer 2: Domain (Models, Services, Business Logic)          │
│ Layer 1: Hardware (Components - Buttons, Encoders, Strips)  │
│ Layer 0: GPIO (Centralized pin management)                  │
└─────────────────────────────────────────────────────────────┘

✅ Clean separation of concerns
✅ Domain-driven design (Config/State/Combined pattern)
✅ Event-driven architecture (EventBus)
✅ FrameManager with priority queues (brilliant!)
✅ Type-safe enums everywhere
```

### Target Architecture (Phase 9+)

```
┌──────────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                          │
│  - Web UI (desktop, mobile, tablet)                          │
│  - Real-time WebSocket sync                                  │
│  - Beautiful color pickers, animation previews               │
│  - 2D LED layout visualization                               │
└────────────────┬─────────────────────────────────────────────┘
                 │ REST API + WebSocket
┌────────────────▼─────────────────────────────────────────────┐
│                  API LAYER (FastAPI)                          │
│  - REST endpoints (zones, animations, presets, system)       │
│  - WebSocket server (real-time bidirectional)                │
│  - Authentication & rate limiting                            │
│  - OpenAPI documentation (auto-generated)                    │
└────────────────┬─────────────────────────────────────────────┘
                 │ ServiceContainer (DI)
┌────────────────▼─────────────────────────────────────────────┐
│               CORE (Existing Backend)                         │
│  - Domain Models & Services (zone, animation, color)         │
│  - Controllers (decoupled via DI)                            │
│  - Hardware Layer (Raspberry Pi GPIO, LED strips)            │
│  - FrameManager (60 FPS rendering)                           │
└──────────────────────────────────────────────────────────────┘
```

---

## 🚀 Feature Roadmap

### 🎨 Advanced Color System

#### Color Modes (Beyond RGB)
```python
class ColorMode(Enum):
    RGB      # Standard (0-255, 0-255, 0-255)
    HSV      # Hue-Saturation-Value (best for animations)
    HSL      # Hue-Saturation-Lightness (intuitive for users)
    TEMP     # Color Temperature in Kelvin (1000-10000K)
    CIE_XY   # CIE 1931 color space (professional lighting)
    PRESET   # Named presets (existing)
```

**Why Each Mode Matters:**
- **HSV**: Perfect for rainbow animations (rotate hue, keep saturation/value)
- **HSL**: Better for dimming (reduce lightness, keep hue/saturation)
- **Temperature**: Warm whites (2700K) vs daylight (5500K) - critical for ambient lighting
- **CIE XY**: Industry standard, accurate color reproduction

#### Smart Color Features

**1. Color Palettes & Themes**
```yaml
palettes:
  sunset:
    name: "Sunset Vibes"
    colors:
      - {mode: TEMP, kelvin: 1800}  # Candle
      - {mode: RGB, rgb: [255, 100, 50]}  # Orange
      - {mode: RGB, rgb: [255, 50, 100]}  # Pink
      - {mode: RGB, rgb: [100, 50, 150]}  # Purple
    
  cyberpunk:
    name: "Cyberpunk Neon"
    colors:
      - {mode: RGB, rgb: [255, 0, 255]}   # Magenta
      - {mode: RGB, rgb: [0, 255, 255]}   # Cyan
      - {mode: RGB, rgb: [255, 255, 0]}   # Yellow
```

**2. Color Harmonies (Auto-Generate)**
- Complementary (opposite on color wheel)
- Analogous (adjacent on color wheel)
- Triadic (120° apart)
- Split-complementary
- **Use case:** User picks one color → system suggests matching palette

**3. Color History & Favorites**
- Last 20 colors used (per zone)
- Favorite colors (star system)
- Quick access in UI

**4. Color Temperature Presets**
```python
COLOR_TEMPS = {
    "CANDLE": 1800,
    "WARM_WHITE": 2700,
    "SOFT_WHITE": 3000,
    "NEUTRAL": 4000,
    "DAYLIGHT": 5500,
    "COOL_WHITE": 6500,
    "CLOUDY_DAY": 7500,
    "BLUE_SKY": 10000
}
```

**5. Adaptive Color (Advanced)**
- **Circadian Rhythm:** Auto-adjust temperature based on time of day
  - Morning: Cool whites (energizing)
  - Afternoon: Neutral (productive)
  - Evening: Warm whites (relaxing)
- **Ambient Light Sensor:** Adapt brightness based on room light
- **Weather Sync:** Match colors to current weather (blue for sunny, gray for cloudy)

---

### 🎬 Advanced Animation System

#### Animation Categories

**1. Ambient Animations (Slow, Subtle)**
```python
class BreathAnimation:
    """Gentle fade in/out - perfect for background ambiance"""
    speed: float = 0.5  # Slow
    colors: List[Color] = [warm_white]
    
class PulseAnimation:
    """Rhythmic pulse - relaxing"""
    bpm: int = 60  # Heart rate
    colors: List[Color]
```

**2. Dynamic Animations (Medium Speed)**
```python
class ColorCycleAnimation:
    """Rainbow through color wheel"""
    speed: float = 1.0
    saturation: float = 100%
    
class WaveAnimation:
    """Wave traveling across strip"""
    speed: float = 1.0
    direction: Direction = LEFT_TO_RIGHT
    colors: List[Color]
```

**3. Reactive Animations (Input-Driven)**
```python
class MusicReactiveAnimation:
    """React to music/sound input"""
    microphone: AudioInput
    fft_bands: int = 8
    sensitivity: float = 0.8
    
class VoiceCommandAnimation:
    """Voice-controlled patterns"""
    commands: Dict[str, AnimationPreset]
```

**4. Game Animations (Interactive)**
```python
class SnakeGameAnimation:
    """Play Snake on LED matrix"""
    matrix: LEDMatrix
    controls: GameController
    
class PongAnimation:
    """Two-player Pong"""
    matrix: LEDMatrix
    player1_encoder: RotaryEncoder
    player2_encoder: RotaryEncoder
```

#### Animation Engine Improvements

**1. Animation Blending**
```python
# Mix two animations with alpha blending
result = AnimationBlender.mix(
    animation_a=ColorCycle(speed=1.0),
    animation_b=Sparkle(density=0.2),
    blend_mode=BlendMode.OVERLAY,
    alpha=0.5
)
```

**2. Animation Scheduling**
```yaml
schedules:
  - animation: BREATHE
    start_time: "22:00"
    duration: "8h"
    days: [MON, TUE, WED, THU, FRI]
    
  - animation: COLOR_CYCLE
    start_time: "06:00"
    duration: "1h"
    days: [SAT, SUN]
```

**3. Animation Presets (User-Saved)**
```python
class AnimationPreset:
    """Saved parameter set for animation"""
    animation_id: AnimationID
    name: str  # e.g., "Fast Rainbow", "Slow Blue Wave"
    parameters: Dict[ParamID, Any]
    thumbnail: bytes  # 8-frame preview GIF
```

**4. Animation Preview Generation**
```python
# Generate 8-frame preview for UI
preview = AnimationEngine.generate_preview(
    animation=ColorCycle(speed=2.0),
    frames=8,
    width=100,
    height=10
)
# Output: preview.gif (displayed in web UI)
```

---

### 🗂️ Zone Management & Scenes

#### Advanced Zone Features

**1. Zone Groups**
```python
class ZoneGroup:
    """Logical grouping of zones"""
    id: str
    name: str
    zones: List[ZoneID]
    
    # Examples:
    # "All Desk" = [DESK, MONITOR, KEYBOARD]
    # "Ambient" = [FLOOR, CEILING, WALL]
    # "Accent" = [SHELF, PICTURE_FRAME]
```

**2. Scenes (Snapshot of All Zones)**
```python
class Scene:
    """Complete system state snapshot"""
    id: str
    name: str
    thumbnail: bytes  # Visual preview
    zone_states: Dict[ZoneID, ZoneState]
    animation_states: Optional[Dict[AnimationID, AnimationState]]
    
    # Examples:
    # "Movie Time": Floor=dim blue, Lamp=off, Monitor=purple
    # "Work Mode": All=cool white 80% brightness
    # "Party": All=rainbow animation, high brightness
    # "Sleep": All=warm white 5% brightness
```

**3. Zone Layout (2D Visualization)**
```yaml
zones:
  - id: FLOOR
    display_name: "Floor Strip"
    pixel_count: 45
    layout:
      type: LINE
      start: {x: 0, y: 100}
      end: {x: 200, y: 100}
      
  - id: MATRIX
    display_name: "LED Matrix"
    pixel_count: 64
    layout:
      type: GRID
      position: {x: 250, y: 50}
      width: 8
      height: 8
      serpentine: true  # Wiring pattern
```

**Frontend Benefit:** Interactive 2D canvas showing live LED colors and positions

---

### 🎮 Advanced Transitions

**Current:** Simple fade
**Target:** Cinematic transitions between states

```python
class TransitionType(Enum):
    FADE          # Existing - smooth fade
    CUT           # Instant (no transition)
    WIPE_LEFT     # Wipe from left to right
    WIPE_RIGHT    # Wipe from right to left
    WIPE_CENTER   # Expand from center
    SPARKLE       # Random pixels fade in
    RIPPLE        # Wave effect
    ZOOM          # Expand/contract from point
    SPIRAL        # Rotate around center
```

**Use Cases:**
- Scene changes: Smooth FADE (500ms)
- Mode switches: Quick WIPE (200ms)
- Emergency off: Instant CUT
- Party mode: SPARKLE transition (fun!)

---

### 🖥️ Frontend Application Design

#### Technology Stack
```
React 18 + TypeScript + Vite
├── Tailwind CSS (utility-first styling)
├── Zustand (lightweight state management)
├── React Query (data fetching + caching)
├── Socket.IO Client (WebSocket)
├── React Color (color pickers)
├── Framer Motion (animations)
└── Recharts (performance graphs)
```

#### UI Components Library

**1. Color Picker Component**
```tsx
<ColorPicker
  color={currentColor}
  onChange={handleColorChange}
  modes={['RGB', 'HSV', 'HSL', 'TEMP']}
  showPalettes={true}
  showHistory={true}
  showHarmonies={true}
/>
```

**Features:**
- Tabbed interface (RGB | HSV | Temp | Presets)
- Live preview on selected zone
- Color harmonies suggestions
- Recent colors row
- Favorite colors ⭐ system

**2. Zone Control Card**
```tsx
<ZoneCard zone={floorZone}>
  <ColorPreview color={zone.state.color} />
  <BrightnessSlider value={zone.brightness} />
  <QuickActions>
    <Button onClick={turnOff}>Off</Button>
    <Button onClick={maxBrightness}>Max</Button>
    <Button onClick={previousColor}>← Prev</Button>
  </QuickActions>
</ZoneCard>
```

**3. Animation Browser**
```tsx
<AnimationGrid>
  {animations.map(anim => (
    <AnimationCard key={anim.id}>
      <PreviewGIF src={anim.thumbnail} />
      <Title>{anim.name}</Title>
      <Description>{anim.description}</Description>
      <PlayButton onClick={() => startAnimation(anim.id)} />
    </AnimationCard>
  ))}
</AnimationGrid>
```

**4. 2D LED Layout Visualizer**
```tsx
<LEDLayoutCanvas
  zones={zones}
  liveColors={true}  // Show current LED colors
  interactive={true} // Click zone to select
  zoomEnabled={true}
/>
```

**5. Scene Manager**
```tsx
<SceneGallery>
  <SceneCard scene={movieTime}>
    <Thumbnail src={scene.preview} />
    <LoadButton onClick={() => loadScene(scene.id)} />
  </SceneCard>
  <CreateSceneButton onClick={captureCurrentState} />
</SceneGallery>
```

#### Dashboard Layout (Desktop)

```
┌─────────────────────────────────────────────────────────────┐
│  Diuna LED Control                [☀️ Light] [🌙 Dark] [⚙️]  │
├───────────────────┬─────────────────────────────────────────┤
│                   │                                          │
│  ZONES            │  FLOOR STRIP                            │
│  ┌─────────┐      │  ┌─────────────────────────────────┐   │
│  │ Floor   │◀─────┼─▶│ Color: [████████] Cyan          │   │
│  │ ████████│      │  │ Brightness: ████████░░ 80%      │   │
│  └─────────┘      │  │ [Off] [Max] [Prev] [Next]       │   │
│  ┌─────────┐      │  └─────────────────────────────────┘   │
│  │ Lamp    │      │                                          │
│  │ ████    │      │  LAMP                                   │
│  └─────────┘      │  ┌─────────────────────────────────┐   │
│  ┌─────────┐      │  │ Color: [████] Orange            │   │
│  │ Desk    │      │  │ Brightness: ████░░░░░░ 40%      │   │
│  │ ████████│      │  └─────────────────────────────────┘   │
│  └─────────┘      │                                          │
│                   │  QUICK ACTIONS                           │
│  SCENES           │  [🎬 Movie Time] [💼 Work Mode]        │
│  • Movie Time     │  [🎉 Party] [😴 Sleep]                 │
│  • Work Mode      │                                          │
│  • Party          │  CURRENT MODE: STATIC                   │
│  • Sleep          │  Animation: None                        │
│  [+ New Scene]    │  FPS: 60 | Frames: 12,453              │
│                   │                                          │
└───────────────────┴─────────────────────────────────────────┘
```

#### Mobile Layout (Responsive)

```
┌─────────────────────┐
│ Diuna          [⚙️] │
├─────────────────────┤
│                     │
│  FLOOR STRIP        │
│  ┌───────────────┐  │
│  │ ████████ Cyan │  │
│  │ 🔆 ████████░  │  │
│  └───────────────┘  │
│                     │
│  LAMP               │
│  ┌───────────────┐  │
│  │ ████ Orange   │  │
│  │ 🔆 ████░░░░░  │  │
│  └───────────────┘  │
│                     │
│  [🎬 Movie] [💼 Work] │
│  [🎉 Party] [😴 Sleep]│
│                     │
│  Current: STATIC    │
│  FPS: 60            │
└─────────────────────┘
```

---

### 🔐 System Features

#### 1. Authentication & Security
```python
class User:
    username: str
    role: UserRole  # ADMIN, USER, GUEST
    
class UserRole(Enum):
    ADMIN = auto()  # Full control
    USER = auto()   # Control zones, animations
    GUEST = auto()  # View only
```

**Features:**
- JWT-based authentication
- API key support (for integrations)
- Rate limiting (prevent API abuse)
- HTTPS support (Let's Encrypt)

#### 2. Configuration Management

**Web-Based Config Editor:**
- Add/remove zones
- Edit GPIO pin assignments
- Calibrate hardware (encoder steps, button debounce)
- Backup/restore config
- Export/import settings (JSON)

#### 3. System Monitoring

**Performance Dashboard:**
- Frame rate (FPS) - real-time graph
- Frame render time (ms)
- Dropped frames counter
- Memory usage
- CPU temperature (Raspberry Pi)
- Disk space (SD card)

**LED Health Monitoring:**
- Stuck pixels detection
- Color accuracy calibration
- Power consumption estimation

#### 4. Logging & Debugging

**Structured Logging:**
```python
log.info("Zone color changed",
    zone="FLOOR",
    old_color="red",
    new_color="blue",
    source="web_ui",
    user="john"
)
```

**Log Viewers:**
- Web UI log viewer (last 1000 entries)
- Filter by category, level, time
- Export logs (JSON, CSV)

---

### 🔌 Integrations & APIs

#### 1. Home Automation Integration

**Home Assistant:**
```yaml
# configuration.yaml
light:
  - platform: mqtt
    name: "Diuna Floor"
    command_topic: "diuna/floor/set"
    state_topic: "diuna/floor/state"
    rgb: true
    brightness: true
```

**Google Home / Alexa:**
- "Hey Google, turn on floor lights"
- "Alexa, set lamp to red"
- "Hey Google, start rainbow animation"

#### 2. MQTT Integration
```python
class MQTTBridge:
    """Publish LED states to MQTT"""
    def on_zone_change(self, zone: Zone):
        self.publish(
            topic=f"diuna/{zone.id}/state",
            payload={"color": zone.color, "brightness": zone.brightness}
        )
```

#### 3. REST API for Third-Party Apps
```bash
# Get all zones
GET /api/zones

# Set zone color
PUT /api/zones/FLOOR/color
{
  "mode": "HSV",
  "hue": 180,
  "saturation": 100,
  "value": 100
}

# Start animation
POST /api/animations/COLOR_CYCLE/start
{
  "zones": ["FLOOR", "LAMP"],
  "speed": 1.5
}
```

#### 4. Webhook Support
```python
# Trigger actions on external events
webhooks:
  - name: "doorbell_ring"
    url: "https://diuna.local/api/webhooks/doorbell"
    action: "flash_all_zones_white"
    
  - name: "motion_detected"
    url: "https://diuna.local/api/webhooks/motion"
    action: "fade_in_scene('security_lights')"
```

---

### 🎲 Advanced Features (Future)

#### 1. LED Matrix Games

**Snake Game:**
```python
class SnakeGame:
    matrix: LEDMatrix  # 8x8 or 16x16
    controls: GamepadOrEncoder
    colors: SnakeColors = {
        'snake': Color.from_rgb(0, 255, 0),
        'food': Color.from_rgb(255, 0, 0),
        'background': Color.from_rgb(0, 0, 0)
    }
```

**Pong:**
```python
class PongGame:
    matrix: LEDMatrix
    player1_encoder: RotaryEncoder
    player2_encoder: RotaryEncoder
    ball_speed: float = 1.0
```

**Tetris:**
```python
class TetrisGame:
    matrix: LEDMatrix
    controls: Gamepad
    colors: List[Color]  # Rainbow blocks
```

#### 2. Music Visualization

**Audio Input:**
```python
class MusicReactiveSystem:
    microphone: AudioInput
    fft_analyzer: FFTAnalyzer
    
    def analyze_beat(self):
        """Detect beat frequency"""
        return self.fft_analyzer.get_bpm()
    
    def analyze_spectrum(self):
        """Get frequency bands"""
        return self.fft_analyzer.get_bands(count=8)
```

**Visualizations:**
- VU meter (bars react to volume)
- Spectrum analyzer (rainbow bars per frequency)
- Beat pulse (flash on beat)
- Bass reaction (low frequencies)

#### 3. AI-Powered Features

**Smart Scene Suggestions:**
```python
class SceneSuggestionEngine:
    """ML-powered scene recommendations"""
    
    def suggest_scene(self, context: Context) -> Scene:
        # Based on:
        # - Time of day
        # - Day of week
        # - Weather
        # - User history
        # - Calendar events (e.g., "movie night")
        pass
```

**Color Mood Detection:**
```python
# Analyze user's color preferences over time
mood_colors = ColorMoodAnalyzer.analyze(user_history)
# Suggest colors that match user's typical evening mood
```

#### 4. Advanced Hardware Support

**Multiple Raspberry Pi Nodes:**
```python
class DistributedLEDSystem:
    """Control multiple Pi nodes from one master"""
    master: RaspberryPi
    nodes: List[RaspberryPi]
    
    # Use case: Different rooms, synchronized
```

**Additional LED Types:**
```python
class LEDStripType(Enum):
    WS2811 = auto()  # Existing
    WS2812 = auto()  # Existing
    WS2813 = auto()  # More robust
    APA102 = auto()  # SPI-based, faster
    SK6812 = auto()  # RGBW (white channel)
```

**Power Management:**
```python
class PowerMonitor:
    """Monitor and limit power consumption"""
    max_amps: float = 10.0
    
    def check_safe(self, target_brightness: float) -> bool:
        estimated_power = self.calculate_power(target_brightness)
        return estimated_power < self.max_amps * 5  # 5V
```

---

## 📐 Code Architecture Best Practices

### Design Patterns to Apply

#### 1. Repository Pattern (Data Access)
```python
class ZoneRepository:
    """Abstract data access for zones"""
    def get_all(self) -> List[Zone]
    def get_by_id(self, id: ZoneID) -> Zone
    def save(self, zone: Zone)
    def delete(self, id: ZoneID)

# Implementations:
class JSONZoneRepository(ZoneRepository):
    """Save to state.json"""
    
class DatabaseZoneRepository(ZoneRepository):
    """Save to SQLite/PostgreSQL"""
```

#### 2. Strategy Pattern (Animations)
```python
class AnimationStrategy(ABC):
    @abstractmethod
    def generate_frame(self, time: float) -> Frame
        
class RainbowStrategy(AnimationStrategy):
    def generate_frame(self, time: float) -> Frame:
        # Rainbow logic
        
class BreathStrategy(AnimationStrategy):
    def generate_frame(self, time: float) -> Frame:
        # Breathing logic
```

#### 3. Observer Pattern (Event Handling)
```python
# Already implemented via EventBus!
# Good job on this one 👍
```

#### 4. Command Pattern (Undo/Redo)
```python
class Command(ABC):
    @abstractmethod
    def execute(self)
    @abstractmethod
    def undo(self)

class SetColorCommand(Command):
    def __init__(self, zone_id: ZoneID, old_color: Color, new_color: Color):
        self.zone_id = zone_id
        self.old_color = old_color
        self.new_color = new_color
    
    def execute(self):
        zone_service.set_color(self.zone_id, self.new_color)
    
    def undo(self):
        zone_service.set_color(self.zone_id, self.old_color)

# Use case: Undo last 10 color changes in web UI
```

#### 5. Facade Pattern (Simplified API)
```python
class DiunaFacade:
    """Simplified API for common operations"""
    
    def set_zone_color(self, zone_name: str, color_hex: str):
        """Simple: diuna.set_zone_color('floor', '#FF0000')"""
        zone_id = ZoneID[zone_name.upper()]
        color = Color.from_hex(color_hex)
        self.zone_service.set_color(zone_id, color)
    
    def start_animation(self, anim_name: str, speed: float = 1.0):
        """Simple: diuna.start_animation('rainbow', speed=2.0)"""
        anim_id = AnimationID[anim_name.upper()]
        self.animation_service.start(anim_id, {"speed": speed})
```

### Code Quality Standards

#### Type Hints (100% Coverage)
```python
# Good ✅
def set_color(zone_id: ZoneID, color: Color) -> None:
    ...

# Bad ❌
def set_color(zone_id, color):
    ...
```

#### Docstrings (Google Style)
```python
def calculate_color_harmony(
    base_color: Color,
    harmony_type: HarmonyType
) -> List[Color]:
    """Calculate color harmony based on color theory.
    
    Args:
        base_color: The starting color
        harmony_type: Type of harmony (complementary, triadic, etc.)
    
    Returns:
        List of colors that harmonize with base_color
        
    Raises:
        ValueError: If base_color is not in RGB/HSV mode
        
    Example:
        >>> base = Color.from_rgb(255, 0, 0)  # Red
        >>> harmony = calculate_color_harmony(base, HarmonyType.COMPLEMENTARY)
        >>> harmony[0]  # Cyan (opposite of red)
        Color(mode=RGB, rgb=(0, 255, 255))
    """
```

#### Testing Strategy
```python
# Unit tests (pytest)
def test_color_conversion_rgb_to_hsv():
    color = Color.from_rgb(255, 0, 0)
    h, s, v = color.to_hsv()
    assert h == 0
    assert s == 100
    assert v == 100

# Integration tests
async def test_zone_color_change_via_api(client: TestClient):
    response = await client.put("/api/zones/FLOOR/color", json={
        "mode": "RGB",
        "rgb": [255, 0, 0]
    })
    assert response.status_code == 200
    
    # Verify state changed
    zone = zone_service.get_zone(ZoneID.FLOOR)
    assert zone.state.color.to_rgb() == (255, 0, 0)

# E2E tests (Playwright)
async def test_user_changes_color_via_ui(page: Page):
    await page.goto("http://localhost:3000")
    await page.click('text=Floor Strip')
    await page.click('text=RGB')
    await page.fill('input[name="red"]', '255')
    await page.fill('input[name="green"]', '0')
    await page.fill('input[name="blue"]', '0')
    await page.click('button:has-text("Apply")')
    
    # Verify LED changed (check via API)
    zone = await api_client.get_zone("FLOOR")
    assert zone.color.rgb == (255, 0, 0)
```

---

## 🎨 UI/UX Design Principles

### 1. Real-Time Feedback
- Color changes appear **instantly** on LEDs and UI
- No loading spinners for quick operations
- Optimistic updates (assume success, revert on error)

### 2. Touch-Friendly Design
- Minimum 44x44px touch targets
- Large sliders (easy to drag)
- Swipe gestures (swipe between zones)

### 3. Keyboard Shortcuts
```
Space:      Play/pause animation
Ctrl+Z:     Undo last change
Ctrl+S:     Save current state as scene
Arrow keys: Navigate between zones
1-9:        Load scene 1-9
Esc:        Cancel/close modal
```

### 4. Accessibility
- Screen reader support (ARIA labels)
- Keyboard navigation (tab order)
- High contrast mode
- Focus indicators
- Alt text for all images

### 5. Dark/Light Theme
```css
/* Dark theme (default for LEDs) */
--bg-primary: #1a1a1a;
--text-primary: #ffffff;
--accent: #00ffff;

/* Light theme (optional) */
--bg-primary: #ffffff;
--text-primary: #1a1a1a;
--accent: #0066cc;
```

---

## 🔧 Deployment & DevOps

### Production Deployment (Raspberry Pi)

**1. Systemd Service**
```ini
[Unit]
Description=Diuna LED Control System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/diuna
ExecStart=/home/pi/diuna/venv/bin/python src/main_asyncio.py
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**2. Nginx Reverse Proxy**
```nginx
server {
    listen 80;
    server_name diuna.local;

    # Frontend (static files)
    location / {
        root /home/pi/diuna/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

**3. Auto-Start on Boot**
```bash
sudo systemctl enable diuna-backend
sudo systemctl start diuna-backend
```

**4. Monitoring (Prometheus + Grafana)**
```python
# Export metrics
from prometheus_client import Counter, Histogram

frames_rendered = Counter('diuna_frames_rendered_total', 'Total frames rendered')
frame_render_time = Histogram('diuna_frame_render_seconds', 'Frame render time')
```

### Backup Strategy
```bash
# Automated daily backup
0 2 * * * /home/pi/backup.sh

# backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf /mnt/backup/diuna-$DATE.tar.gz \
    /home/pi/diuna/src/config/ \
    /home/pi/diuna/src/state/
```

---

## 🎯 Success Metrics

### Performance Targets
- **Frame Rate:** 60 FPS stable (no drops)
- **Latency:** < 50ms (encoder rotation → LED change)
- **Startup Time:** < 5 seconds
- **Memory Usage:** < 200 MB
- **CPU Usage:** < 30% (idle), < 60% (animation)

### User Experience Goals
- **Setup Time:** < 5 minutes (first-time user)
- **Learning Curve:** < 10 minutes to master basics
- **Error Rate:** < 1% (failed operations)
- **User Satisfaction:** > 4.5/5 stars

### Code Quality Metrics
- **Test Coverage:** > 80%
- **Type Coverage:** 100% (mypy strict)
- **Linting:** 0 errors (pylint, flake8)
- **Documentation:** 100% (all public APIs)

---

## 🚀 Implementation Priority

### Phase 8: Backend Refactoring (CURRENT)
- ✅ Clean up technical debt (logger migration)
- ✅ Dependency injection refactor
- ✅ Centralize enum serialization
- 🔄 Refactoring to make all zone_colors dicts use consistent types (all enums):
- 🔄 Add save debouncing

### Phase 9: Backend API Layer
- FastAPI setup
- REST endpoints (zones, animations, colors, system)
- WebSocket server (real-time bidirectional)
- OpenAPI documentation

### Phase 10: Frontend Application
- React + TypeScript + Vite setup
- Core UI components (zones, animations, colors)
- WebSocket integration
- Responsive design (mobile, tablet, desktop)

### Phase 11: Advanced Color System
- HSV, HSL, color temperature modes
- Color palettes & themes
- Color harmonies
- Adaptive/circadian lighting

### Phase 12: Advanced Animations
- Animation blending
- Animation scheduling
- Animation presets
- Preview generation

### Phase 13: Scenes & Groups
- Zone groups
- Scene management
- Scene scheduling
- 2D LED layout visualization

### Phase 14: Integrations
- Home Assistant / MQTT
- Google Home / Alexa
- REST API for third-party apps
- Webhook support

### Phase 15: Advanced Features
- Music visualization
- LED matrix games (Snake, Pong, Tetris)
- AI-powered suggestions
- Multi-node support

---

## 💡 Closing Thoughts

Diuna has **exceptional foundations**:
- Clean architecture ✅
- Type safety ✅
- Event-driven design ✅
- Performance-first (FrameManager) ✅

The roadmap above transforms it from a **working prototype** into a **production-grade, delightful, extensible system** that rivals commercial LED controllers.

**Key Differentiators:**
1. **Open source** - full control, customizable
2. **Professional architecture** - maintainable, testable, scalable
3. **Beautiful UI** - not just functional, but gorgeous
4. **Advanced features** - beyond simple on/off (games, music, AI)
5. **Hardware-focused** - respects physical constraints, optimized for Pi

**Next Steps:**
1. Complete Phase 8 (backend refactoring)
2. Build Phase 9 (FastAPI layer)
3. Build Phase 10 (React frontend)
4. Iterate on features based on user feedback

**Vision:**
> Diuna becomes the **de-facto standard** for Raspberry Pi LED control - the system that everyone recommends when they want professional, beautiful, programmable lighting.

---

*This document is a living roadmap. Update it as the project evolves!* 🎨✨
