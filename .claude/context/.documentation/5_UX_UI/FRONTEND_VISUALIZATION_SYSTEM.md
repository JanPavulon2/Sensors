# Frontend Visualization System - UI/UX Specification

## 📋 Document Overview

**Purpose:** Comprehensive specification for visualizing LED zones, strips, matrices, animations, and controls in the Diuna web frontend.

**Scope:** UI components, interaction patterns, preview generation, and rendering strategies for LED control system.

**Target Platform:** React + TypeScript + Tailwind CSS web application

**Last Updated:** 2025-01-15

---

## 🎨 Part 1: Zone & LED Visualization

### 1.1 Zone Card Component (Primary Pattern)

**Use Case:** Main dashboard view showing all zones with live preview and quick controls.

**Visual Structure:**
```
┌─────────────────────────────────────────────┐
│ Floor Strip (45 LEDs)              [⚙️ Edit]│
├─────────────────────────────────────────────┤
│                                             │
│  ████████████████████████████████████████   │ ← Live preview bar
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   │   (actual LED colors)
│                                             │
│  Color: [●●●● Cyan]     Brightness: 80%     │
│  Mode: STATIC           Status: ✓ Active    │
│                                             │
│  [🎨 Change Color] [💡 Adjust] [❌ Turn Off]│
└─────────────────────────────────────────────┘
```

**Key Features:**
- Real-time pixel data via WebSocket
- Individual LED visualization (50+ pixels rendered as gradient bar)
- Color swatch with current color
- Brightness indicator (visual bar + percentage)
- Quick action buttons (touch-friendly, 44x44px minimum)

**Component Hierarchy:**
```
ZoneCard
├── ZoneHeader (name, pixel count, edit button)
├── LEDStripPreview (live pixel rendering)
├── ZoneInfo (color swatch, brightness, mode, status)
└── QuickActions (color picker, adjust, toggle)
```

**Data Flow:**
```
WebSocket → useZoneStore → ZoneCard → LEDStripPreview
                                    → ColorSwatch
                                    → BrightnessIndicator
```

---

### 1.2 LED Strip Preview Component

**Purpose:** Show actual LED colors in real-time with visual effects.

**Rendering Strategy:**

**Option A: Flexbox Gradient (Simple, Performant)**
```tsx
// 50 LEDs rendered as flex items
<div className="flex gap-0.5">
  {pixels.map((pixel, idx) => (
    <div
      key={idx}
      className="flex-1 h-12 rounded-sm transition-colors duration-100"
      style={{
        backgroundColor: `rgb(${pixel.r}, ${pixel.g}, ${pixel.b})`,
        boxShadow: `0 0 8px rgba(${pixel.r}, ${pixel.g}, ${pixel.b}, 0.6)`
      }}
    />
  ))}
</div>
```

**Visual Effects:**
- Glow effect via `box-shadow` (subtle, 8px blur)
- Smooth color transitions (100ms duration)
- Background gradient overlay for depth
- Semi-transparent housing effect

**Performance Considerations:**
- Maximum 60 FPS updates
- CSS transitions for smoothness
- Debounced WebSocket updates (100ms)
- Virtual scrolling for 300+ LED strips

---

### 1.3 Interactive 2D Canvas Layout

**Use Case:** Advanced visualization for wearables with multiple strips in different positions.

**Example: Hoodie with Multiple Zones**
```
┌─────────────────────────────────────────────────────┐
│  LED Layout - Interactive Canvas        [🔍 Zoom]   │
├─────────────────────────────────────────────────────┤
│                                                      │
│      Hoodie Visualization                           │
│                                                      │
│         ╭────────────╮                              │
│         │  ████████  │ ← Hood Strip (20 LEDs)       │
│         ╰─────┬──────╯                              │
│               │                                      │
│       ╭───────┴───────╮                             │
│       │               │                              │
│   ████│               │████  ← Arm Strips           │
│       │               │                              │
│       │   ████████    │      ← Front Chest          │
│       │               │                              │
│       ╰───────────────╯                             │
│                                                      │
│  [Click any zone to edit]                           │
└─────────────────────────────────────────────────────┘
```

**Canvas Rendering Types:**

**A) Line Strip:**
```python
# Layout configuration
layout:
  type: LINE
  x: 200        # Canvas X position
  y: 50         # Canvas Y position
  width: 400    # Total width in pixels
  height: 10    # Strip height
```

**B) Matrix (8x8):**
```python
layout:
  type: MATRIX
  x: 250
  y: 200
  width: 8      # LEDs wide
  height: 8     # LEDs tall
  pixel_size: 20
  serpentine: true  # Wiring pattern
```

**C) Ring/Circle:**
```python
layout:
  type: RING
  center_x: 300
  center_y: 300
  radius: 50
  led_count: 16
```

**Interaction Features:**
- Click zone to select/edit
- Hover to highlight
- Zoom/pan controls
- Export layout as PNG
- Drag-and-drop zone positioning (future)

---

## 🎨 Part 2: Color Picker System

### 2.1 Multi-Mode Color Picker

**Supported Modes:**
- **HUE** - Single hue slider (0-360°) - Simplest for wearables
- **RGB** - Three sliders (R/G/B 0-255) - Precise control
- **HSV** - Hue/Saturation/Value sliders - Best for animations
- **PRESET** - Named color presets - Quick selection
- **TEMP** - Color temperature in Kelvin (future)

**UI Layout:**
```
┌───────────────────────────────────┐
│  Color Selection                  │
├───────────────────────────────────┤
│                                   │
│  [HUE] [RGB] [HSV] [PRESETS]     │ ← Mode tabs
│                                   │
│  ⬤ Live Preview                  │
│  [████████████] Cyan              │
│                                   │
│  [Mode-specific controls here]   │
│                                   │
│  🎨 Presets:                      │
│  [🔴] [🟢] [🔵] [🟡] [🟣] [🟠]   │
│                                   │
│  Recent Colors:                   │
│  ⬤ ⬤ ⬤ ⬤ ⬤                      │
│                                   │
│  [Apply] [Cancel]                 │
└───────────────────────────────────┘
```

---

### 2.2 Hue Mode (Recommended Default for Wearables)

**Visual Design:**
```
┌───────────────────────────────────┐
│  Hue Mode                         │
├───────────────────────────────────┤
│                                   │
│  ⬤ Live Preview                  │
│  [████████████] Cyan (180°)      │
│                                   │
│  Hue Slider (0-360°)              │
│  ╔═══════════════════════════╗   │
│  ║  🔴🟠🟡🟢🔵🟣           ║   │
│  ║  ▰▰▰▰▰▰▰▰▰▰▱▱▱▱▱▱▱▱▱▱  ║   │
│  ╚═══════════════════════════╝   │
│                                   │
│  Quick Presets (8 colors):        │
│  [🔴 Red 0°]   [🟠 Orange 30°]   │
│  [🟡 Yellow 60°][🟢 Green 120°]  │
│  [🔵 Cyan 180°] [🔵 Blue 240°]   │
│  [🟣 Purple 280°][🟣 Magenta 300°]│
│                                   │
└───────────────────────────────────┘
```

**Interactive Features:**
- Gradient slider with full spectrum background
- Numeric input (0-360)
- Color name display (e.g., "Cyan", "Orange")
- Preset buttons with emoji indicators
- Live preview with glow effect

**Implementation Details:**
```tsx
// Hue slider background CSS
background: linear-gradient(to right,
  hsl(0, 100%, 50%),    // Red
  hsl(60, 100%, 50%),   // Yellow
  hsl(120, 100%, 50%),  // Green
  hsl(180, 100%, 50%),  // Cyan
  hsl(240, 100%, 50%),  // Blue
  hsl(300, 100%, 50%),  // Magenta
  hsl(360, 100%, 50%)   // Red again
);
```

---

### 2.3 RGB Mode (Precise Control)

**Visual Design:**
```
┌─────────────────────────────────────┐
│  RGB Mode                           │
├─────────────────────────────────────┤
│                                     │
│  Preview: [████████] #00FFFF       │
│                                     │
│  Red   (0-255)                      │
│  [  0  ] ▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱    │
│                                     │
│  Green (0-255)                      │
│  [ 255 ] ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰    │
│                                     │
│  Blue  (0-255)                      │
│  [ 255 ] ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰    │
│                                     │
│  Hex: [#00FFFF] [Copy] [Paste]     │
└─────────────────────────────────────┘
```

**Features:**
- Three independent sliders (red/green/blue accent colors)
- Numeric input for each channel
- Hex code input/output
- Copy/paste hex values
- Real-time preview update

---

### 2.4 Color Presets & Recent Colors

**Preset Storage Strategy:**
```typescript
interface ColorPreset {
  id: string;
  name: string;
  color: Color;
  created_at: string;
  is_favorite: boolean;
}

// Storage locations:
// 1. Global presets (system-wide)
localStorage.setItem('diuna_color_presets', JSON.stringify(presets));

// 2. Recent colors (per-user, last 20)
localStorage.setItem('diuna_recent_colors', JSON.stringify(recentColors));

// 3. Favorites (starred presets)
localStorage.setItem('diuna_favorite_colors', JSON.stringify(favorites));
```

**UI for Presets:**
```
┌─────────────────────────────────────┐
│  My Presets                 [+ Add] │
├─────────────────────────────────────┤
│  ⭐ Favorites                       │
│  ⬤ Cyan Glow    ⬤ Warm Orange      │
│  ⬤ Purple Rain  ⬤ Sunset Red       │
│                                     │
│  📦 All Presets                     │
│  ⬤ Forest Green ⬤ Ocean Blue       │
│  ⬤ Candy Pink   ⬤ Lemon Yellow     │
│                                     │
│  🕐 Recent (Last 10)                │
│  ⬤ ⬤ ⬤ ⬤ ⬤ ⬤ ⬤ ⬤ ⬤ ⬤            │
└─────────────────────────────────────┘
```

---

## 🎬 Part 3: Animation Visualization

### 3.1 Animation Preview System Architecture

**Three-Tier Preview System:**

```
┌─────────────────────────────────────────────────────────┐
│              ANIMATION PREVIEW GENERATOR                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  TIER 1: Static Thumbnail (5-10 KB PNG)                │
│  • Single representative frame                          │
│  • Used in animation list                              │
│  • Pre-generated at build time                         │
│  • 300x60px resolution                                 │
│                                                          │
│  TIER 2: Animated Loop (30-50 KB GIF)                  │
│  • 8-12 frames showing full cycle                      │
│  • Loops infinitely                                    │
│  • Generated on-demand or cached                       │
│  • 400x80px resolution                                 │
│  • Shown on hover/click                                │
│                                                          │
│  TIER 3: Real-Time Canvas (No files)                   │
│  • Live simulation at 30-60 FPS                        │
│  • Used in animation editor                            │
│  • JavaScript-based rendering                          │
│  • 800x100px resolution                                │
│  • Instant parameter updates                           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

### 3.2 Animation Card with Preview

**Visual Layout:**
```
┌──────────────────────────────────────────────┐
│  ▶️ Color Cycle                              │
│  ┌─────────────────────────────────────────┐ │
│  │ [████░░░░████░░░░████]  ← Animated GIF  │ │
│  │   8-frame loop, plays on hover          │ │
│  └─────────────────────────────────────────┘ │
│                                              │
│  🎨 Rainbow animation across strip           │
│                                              │
│  Speed:    ▰▰▰▰▰▰▱▱▱▱ 60%                   │
│  Colors:   🔴 🟢 🔵 🟡                       │
│  Direction: → Left to Right                  │
│                                              │
│  [▶️ Play] [⏸️ Pause] [⚙️ Edit]             │
└──────────────────────────────────────────────┘
```

**Interaction States:**
- **Default:** Static thumbnail visible
- **Hover:** Animated GIF loads and plays
- **Click:** Opens editor with real-time canvas
- **Playing:** Visual indicator (pulsing play button)

---

### 3.3 Intelligent Frame Sampling

**Problem:** How to choose 8 frames from 600-frame animation (10s @ 60fps)?

**Solution:** Sample "interesting moments" based on animation type.

**Sampling Strategies by Animation Type:**

**A) BREATHE (Brightness variation)**
```python
sample_points = [
  0.0,   # Minimum brightness (fade out complete)
  0.25,  # Rising (25% brightness)
  0.5,   # Peak brightness (100%)
  0.75,  # Falling (75% brightness)
  1.0    # Back to minimum
]
```

**B) COLOR_CYCLE (Hue rotation)**
```python
sample_points = [
  0.0,    # Red (0°)
  0.167,  # Orange (60°)
  0.333,  # Yellow (120°)
  0.5,    # Green (180°)
  0.667,  # Cyan (240°)
  0.833,  # Blue (300°)
  1.0     # Back to Red (360°)
]
```

**C) WAVE (Movement across strip)**
```python
sample_points = [
  0.0,    # Wave at left edge
  0.25,   # Wave 1/4 across
  0.5,    # Wave at center
  0.75,   # Wave 3/4 across
  1.0     # Wave at right edge
]
```

**D) SPARKLE (Random pattern)**
```python
# Random sampling (capture different variations)
sample_points = np.random.uniform(0, 1, 8)
sample_points.sort()
```

---

### 3.4 Preview File Structure

**Backend Storage:**
```
backend/static/previews/
├── thumbnails/           # Static single-frame previews
│   ├── breathe.png
│   ├── color_cycle.png
│   ├── wave.png
│   └── sparkle.png
│
├── loops/                # Animated GIF loops
│   ├── breathe_slow.gif
│   ├── breathe_fast.gif
│   ├── color_cycle_default.gif
│   ├── color_cycle_rainbow.gif
│   ├── wave_left.gif
│   └── wave_right.gif
│
├── metadata/             # JSON descriptions
│   ├── breathe.json
│   ├── color_cycle.json
│   └── wave.json
│
└── cache/                # User-generated previews (custom params)
    └── {user_id}/
        ├── breathe_custom_12345.gif
        └── wave_custom_67890.gif
```

**Metadata JSON Example:**
```json
{
  "animation_id": "COLOR_CYCLE",
  "preset_name": "default",
  "frame_count": 8,
  "duration_seconds": 2.0,
  "loop": true,
  "resolution": {
    "width": 400,
    "height": 80,
    "pixel_count": 50
  },
  "colors_used": [
    {"hue": 0, "name": "Red"},
    {"hue": 60, "name": "Yellow"},
    {"hue": 120, "name": "Green"},
    {"hue": 180, "name": "Cyan"},
    {"hue": 240, "name": "Blue"},
    {"hue": 300, "name": "Magenta"}
  ],
  "complexity": "medium",
  "recommended_zones": ["strip", "matrix"],
  "file_path": "/static/previews/loops/color_cycle_default.gif",
  "file_size_bytes": 48230,
  "generated_at": "2025-01-15T10:30:00Z"
}
```

---

### 3.5 Preview Generation Workflow

**Workflow 1: Pre-Generation (App Startup)**
```
App Startup
    ↓
Check if default previews exist
    ↓ NO (first run)
Generate thumbnails for all animations (20 anims × 10KB = 200KB)
    ↓
Generate 1 default loop per animation (20 × 40KB = 800KB)
    ↓
Store in /static/previews/
    ↓
Index in metadata JSON files
    ↓
Total time: ~2-5 seconds
```

**Workflow 2: On-Demand Custom Preview**
```
User adjusts animation parameters in UI
    ↓
Frontend: POST /api/animations/preview
{
  "animation_id": "BREATHE",
  "parameters": {"speed": 0.8, "color": {...}}
}
    ↓
Backend: Generate hash of parameters
    ↓
Check cache for existing preview (hash-based lookup)
    ↓ MISS
Generate 8-frame GIF (~200-500ms)
    ↓
Cache with 1-hour TTL
    ↓
Return URL: /static/previews/cache/{user_id}/breathe_{hash}.gif
```

**Workflow 3: Real-Time Canvas (Editor)**
```
User opens Animation Editor
    ↓
Frontend loads animation logic (JavaScript port)
    ↓
Canvas renders at 30-60 FPS (requestAnimationFrame)
    ↓
Parameter change triggers immediate re-render
    ↓
Zero latency (local computation, no backend calls)
```

---

### 3.6 Animation Preview Visual Examples

**A) Solid Color Animations (BREATHE, PULSE)**
```
Visualizes brightness variation:
┌────────────────────────────────────┐
│ Frame 1: ░░░░░░░░░░░░░░░░░░░░░░  │  0% brightness
│ Frame 2: ░░░░▰▰▰▰▰▰▰▰▰▰░░░░░░░░  │  25%
│ Frame 3: ▰▰▰▰████████████████▰▰▰▰  │  75%
│ Frame 4: ████████████████████████  │  100% (peak)
│ Frame 5: ▰▰▰▰████████████████▰▰▰▰  │  75%
│ Frame 6: ░░░░▰▰▰▰▰▰▰▰▰▰░░░░░░░░  │  25%
│ Frame 7: ░░░░░░░░░░░░░░░░░░░░░░  │  0%
└────────────────────────────────────┘
All pixels same color, varying intensity
```

**B) Rainbow Animations (COLOR_CYCLE, RAINBOW_WAVE)**
```
Visualizes hue shifting:
┌────────────────────────────────────┐
│ Frame 1: 🔴🟠🟡🟢🔵🟣            │  Hue 0-300
│ Frame 2: 🟣🔴🟠🟡🟢🔵            │  Shift +60°
│ Frame 3: 🔵🟣🔴🟠🟡🟢            │  Shift +120°
│ Frame 4: 🟢🔵🟣🔴🟠🟡            │  Shift +180°
│ Frame 5: 🟡🟢🔵🟣🔴🟠            │  Shift +240°
│ Frame 6: 🟠🟡🟢🔵🟣🔴            │  Shift +300°
└────────────────────────────────────┘
Each pixel different hue, synchronized rotation
```

**C) Movement Animations (WAVE, SCANNER, COMET)**
```
Visualizes spatial movement:
┌────────────────────────────────────┐
│ Frame 1: ████░░░░░░░░░░░░░░░░░░░  │  Wave at left
│ Frame 2: ░░░░████░░░░░░░░░░░░░░░  │
│ Frame 3: ░░░░░░░░████░░░░░░░░░░░  │  Moving right
│ Frame 4: ░░░░░░░░░░░░████░░░░░░░  │
│ Frame 5: ░░░░░░░░░░░░░░░░████░░░  │
│ Frame 6: ░░░░░░░░░░░░░░░░░░░░████  │  Wave at right
└────────────────────────────────────┘
Blob/pattern traveling across strip
```

**D) Pattern Animations (TWINKLE, SPARKLE, FIRE)**
```
Visualizes random/chaotic patterns:
┌────────────────────────────────────┐
│ Frame 1: ░█░░░░█░░█░░░░░█░░░░░░░  │  Random
│ Frame 2: ░░░█░░░░░░░█░░░░░█░░█░░  │  pixels
│ Frame 3: █░░░░░█░░░░░░█░░░░░░░█░  │  lighting
│ Frame 4: ░░█░░░░░█░░█░░░█░░░░░░░  │  up/down
│ Frame 5: ░░░░█░░░░░░░░░█░█░░█░░░  │  at random
└────────────────────────────────────┘
Unpredictable patterns (best shown with animation)
```

**E) Matrix Animations (8x8 LED Matrix)**
```
2D grid visualization for games:
┌────────────────────┐
│ ▓ ░ ░ ░ ░ ░ ░ ▓  │  Snake game
│ ▓ ░ ░ ░ ░ ░ ░ ▓  │  showing snake
│ ▓ ▓ ▓ ░ ░ ░ ░ ▓  │  body (▓)
│ ░ ░ ▓ ░ ░ ░ ░ ▓  │  and movement
│ ░ ░ ▓ ▓ ▓ ░ ░ ▓  │  path
│ ░ ░ ░ ░ ▓ ░ ░ ▓  │
│ ░ ░ ░ ░ ▓ ▓ ▓ ▓  │
│ 🔴 ░ ░ ░ ░ ░ ░ ░  │  Food (🔴)
└────────────────────┘
```

---

## 🎮 Part 4: Animation Parameter Controls

### 4.1 Universal Parameter Component

**Purpose:** Render different control types based on parameter value_type.

**Parameter Types & Controls:**

**INT (Integer Slider)**
```
┌─────────────────────────────────────┐
│ Speed (0-100)                       │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ ▰▰▰▰▰▰▰▰▰▰▰▰▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱   │
│ └─ 0 ──────── 60 ─────────── 100 ┘ │
└─────────────────────────────────────┘
```

**FLOAT (Decimal Slider)**
```
┌─────────────────────────────────────┐
│ Intensity (0.0-1.0)                 │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱   │
│ └─ 0.0 ────── 0.65 ────── 1.0 ───┘ │
└─────────────────────────────────────┘
```

**BOOL (Toggle Switch)**
```
┌─────────────────────────────────────┐
│ Reverse Direction                   │
│ [○──────] OFF                       │
│  ↓ Click to toggle                  │
│ [──────●] ON                        │
└─────────────────────────────────────┘
```

**COLOR (Color Picker Button)**
```
┌─────────────────────────────────────┐
│ Primary Color                       │
│ ┌─────────────────────────────────┐ │
│ │ ████████████████████████████████ │ │
│ │        Click to change          │ │
│ └─────────────────────────────────┘ │
│ Current: Cyan (180°)                │
└─────────────────────────────────────┘
```

**ENUM (Dropdown Select)**
```
┌─────────────────────────────────────┐
│ Direction                           │
│ ┌─────────────────────────────────┐ │
│ │ → Left to Right            ▼   │ │
│ └─────────────────────────────────┘ │
│ Options:                            │
│ • → Left to Right                   │
│ • ← Right to Left                   │
│ • ↕ Bidirectional                   │
└─────────────────────────────────────┘
```

---

### 4.2 Animation Editor Full View

**Layout with Real-Time Preview:**
```
┌───────────────────────────────────────────────────┐
│  Animation Editor: WAVE                           │
├───────────────────────────────────────────────────┤
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  [Real-time Canvas Preview - 60 FPS]        │ │
│  │                                              │ │
│  │  ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ← Wave  │ │
│  │     moving live as you adjust sliders       │ │
│  │                                              │ │
│  │  [▶️ Play] [⏸️ Pause] [⏮️ Reset]           │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  Parameters:                                      │
│  ┌─────────────────────────────────────────────┐ │
│  │ Speed                                       │ │
│  │ ▰▰▰▰▰▰▱▱▱▱  60%                            │ │
│  │                                             │ │
│  │ Direction                                   │ │
│  │ [→ Left to Right ▼]                        │ │
│  │                                             │ │
│  │ Wave Width                                  │ │
│  │ ▰▰▰▰▱▱▱▱▱▱  40%                            │ │
│  │                                             │ │
│  │ Color 1: [🔴 Red]    Color 2: [🔵 Blue]   │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  [Apply to LEDs] [Save as Preset] [Cancel]       │
└───────────────────────────────────────────────────┘
```

**Key Features:**
- Parameters update preview in real-time (no lag)
- Preview runs continuously (looping animation)
- "Apply to LEDs" sends to physical hardware
- "Save as Preset" stores parameter combination
- All changes are reversible (Cancel button)

---

## 📱 Part 5: Responsive Layout Design

### 5.1 Mobile Layout (Portrait, <768px)

**Single Column, Touch-Optimized:**
```
┌─────────────────────┐
│ Diuna          ☰    │
├─────────────────────┤
│                     │
│ ┌─────────────────┐ │
│ │ Floor Strip     │ │
│ │ ███████████████ │ │
│ │ Cyan • 80%      │ │
│ │ [🎨] [💡] [❌] │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ Lamp            │ │
│ │ ████            │ │
│ │ Orange • 40%    │ │
│ │ [🎨] [💡] [❌] │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ Desk            │ │
│ │ ████████████    │ │
│ │ Purple • 100%   │ │
│ │ [🎨] [💡] [❌] │ │
│ └─────────────────┘ │
│                     │
│ Quick Actions:      │
│ [🎬 Movie] [💼 Work]│
│ [🎉 Party] [😴 Sleep]│
│                     │
│ [+ Add Scene]       │
└─────────────────────┘
```

**Mobile-Specific Features:**
- Large touch targets (minimum 44x44px)
- Swipeable zone cards (scroll horizontally)
- Bottom navigation bar (sticky)
- Simplified controls (hide advanced options)
- Haptic feedback on button press (if supported)

---

### 5.2 Tablet Layout (768px - 1024px)

**Two Column Grid:**
```
┌─────────────────────────────────────────────┐
│ Diuna LED Control            🌙 ⚙️ 👤      │
├──────────────────┬──────────────────────────┤
│                  │                          │
│ ┌──────────────┐ │ ┌──────────────────────┐ │
│ │ Floor Strip  │ │ │ Lamp                 │ │
│ │ ████████████ │ │ │ ████                 │ │
│ │ Cyan • 80%   │ │ │ Orange • 40%         │ │
│ │ [🎨] [💡] [❌]│ │ │ [🎨] [💡] [❌]       │ │
│ └──────────────┘ │ └──────────────────────┘ │
│                  │                          │
│ ┌──────────────┐ │ ┌──────────────────────┐ │
│ │ Desk         │ │ │ Monitor              │ │
│ │ ████████████ │ │ │ ████████             │ │
│ │ Purple • 100%│ │ │ Blue • 60%           │ │
│ │ [🎨] [💡] [❌]│ │ │ [🎨] [💡] [❌]       │ │
│ └──────────────┘ │ └──────────────────────┘ │
│                  │                          │
├──────────────────┴──────────────────────────┤
│ Quick Actions:                              │
│ [🎬 Movie] [💼 Work] [🎉 Party] [😴 Sleep] │
└─────────────────────────────────────────────┘
```

---

### 5.3 Desktop Layout (>1024px)

**Three Column with Sidebar:**
```
┌───────────────────────────────────────────────────────────┐
│ Diuna LED Control                      🌙 ⚙️ 👤           │
├──────────────┬────────────────────────────────────────────┤
│              │                                            │
│ ZONES        │  FLOOR STRIP                               │
│              │  ┌──────────────────────────────────────┐  │
│ ┌──────────┐ │  │ █████████████████████████████████████│  │
│ │Floor     │◀┼──│ Cyan • 80% • STATIC                  │  │
│ │████████  │ │  │                                       │  │
│ └──────────┘ │  │ [🎨 Color] [💡 Bright] [❌ Off]      │  │
│              │  └──────────────────────────────────────┘  │
│ ┌──────────┐ │                                            │
│ │Lamp      │ │  LAMP                                      │
│ │████      │ │  ┌──────────────────────────────────────┐  │
│ └──────────┘ │  │ Orange • 40% • STATIC                │  │
│              │  └──────────────────────────────────────┘  │
│ ┌──────────┐ │                                            │
│ │Desk      │ │  QUICK ACTIONS                             │
│ │████████  │ │  [🎬 Movie] [💼 Work] [🎉 Party] [😴 Sleep]│
│ └──────────┘ │                                            │
│              │  ANIMATIONS                                │
│ SCENES       │  ▶️ Color Cycle  [████░░░░████]           │
│ • Movie Time │  🎨 Breathe     [░░░░████░░░░]           │
│ • Work Mode  │  🌊 Wave        [████░░░░░░░░]           │
│ • Party      │                                            │
│ • Sleep      │  SYSTEM STATUS                             │
│ [+ New]      │  FPS: 60 │ Mode: STATIC │ Uptime: 2d 5h   │
│              │                                            │
└──────────────┴────────────────────────────────────────────┘
```

**Desktop-Specific Features:**
- Persistent sidebar navigation
- Multi-select zones (Ctrl+Click)
- Keyboard shortcuts (Space = play/pause)
- Drag-and-drop preset ordering
- Multi-monitor support (detached windows)

---

## 🎯 Part 6: Advanced Matrix Visualization

### 6.1 LED Matrix Display Component

**8x8 Matrix Example:**
```tsx
// Grid display with individual pixel control
┌───────────────────────────────┐
│ LED Matrix (8x8 = 64 pixels)  │
├───────────────────────────────┤
│  ┌─┬─┬─┬─┬─┬─┬─┬─┐           │
│  │▓│░│░│░│░│░│░│▓│  ← Row 0  │
│  ├─┼─┼─┼─┼─┼─┼─┼─┤           │
│  │▓│░│░│░│░│░│░│▓│           │
│  ├─┼─┼─┼─┼─┼─┼─┼─┤           │
│  │▓│▓│▓│░│░│░│░│▓│  Snake    │
│  ├─┼─┼─┼─┼─┼─┼─┼─┤  body     │
│  │░│░│▓│░│░│░│░│▓│           │
│  ├─┼─┼─┼─┼─┼─┼─┼─┤           │
│  │░│░│▓│▓│▓│░│░│▓│           │
│  ├─┼─┼─┼─┼─┼─┼─┼─┤           │
│  │░│░│░│░│▓│░│░│▓│           │
│  ├─┼─┼─┼─┼─┼─┼─┼─┤           │
│  │░│░│░│░│▓│▓│▓│▓│           │
│  ├─┼─┼─┼─┼─┼─┼─┼─┤           │
│  │🔴│░│░│░│░│░│░│░│  Food    │
│  └─┴─┴─┴─┴─┴─┴─┴─┘           │
│                               │
│  [Click pixel to toggle]      │
│  [Clear] [Pattern] [Save]     │
└───────────────────────────────┘
```

**Rendering Strategy:**
- CSS Grid layout (`display: grid; grid-template-columns: repeat(8, 1fr)`)
- Each pixel as div with color and glow effect
- 60 FPS updates via requestAnimationFrame
- Click/touch to manually set pixels (paint mode)

---

### 6.2 Matrix Patterns Library

**Pre-built patterns for quick testing:**
```
┌─────────────────────────────────────┐
│ Matrix Patterns                     │
├─────────────────────────────────────┤
│                                     │
│ [Smiley Face]  [Heart]  [Arrow]    │
│                                     │
│ ┌───────┐  ┌───────┐  ┌───────┐   │
│ │ ░██░  │  │ ░███  │  │ ░░█░░ │   │
│ │ █░░█  │  │ █░░█  │  │ ░██░░ │   │
│ │ █░░█  │  │ █░░█  │  │ █░█░░ │   │
│ │ ░░░░  │  │ ░███  │  │ ░░█░░ │   │
│ │ █░░█  │  │ ░░█░  │  │ ░░█░░ │   │
│ │ ░██░  │  │ ░░░░  │  │ ░░█░░ │   │
│ └───────┘  └───────┘  └───────┘   │
│                                     │
│ [Checkerboard] [Stripes] [Custom]  │
└─────────────────────────────────────┘
```

---

## 💡 Part 7: Performance Optimization

### 7.1 WebSocket Update Strategy

**Problem:** 300 LEDs × 60 FPS = 18,000 color updates/second

**Solution: Throttled + Batched Updates**

```typescript
// Frontend WebSocket handler
const handlePixelUpdate = throttle((data: PixelUpdate) => {
  // Batch multiple pixel updates
  pixelBuffer.push(data);
  
  // Flush buffer every 100ms (10 FPS visual update)
  if (!flushScheduled) {
    flushScheduled = true;
    setTimeout(() => {
      applyPixelBatch(pixelBuffer);
      pixelBuffer = [];
      flushScheduled = false;
    }, 100);
  }
}, 50); // Throttle individual updates to 50ms
```

**Result:**
- Visual refresh: 10-20 FPS (smooth enough for perception)
- Network traffic: 90% reduction
- CPU usage: Minimal (batched DOM updates)

---

### 7.2 Canvas vs DOM Rendering

**When to use Canvas:**
- ✅ 100+ LEDs
- ✅ Real-time animations (30-60 FPS)
- ✅ Matrix displays (8x8 = 64 pixels)
- ✅ Complex visual effects (blur, glow)

**When to use DOM (div elements):**
- ✅ <50 LEDs
- ✅ Static/slow-changing displays
- ✅ Need CSS animations/transitions
- ✅ Accessibility (screen readers)

**Performance Comparison:**
```
Scenario: 300 LEDs @ 60 FPS
├── Canvas:    ~5ms render time   ✅ GOOD
└── DOM:       ~45ms render time  ❌ BAD (frame drops)

Scenario: 30 LEDs @ 10 FPS
├── Canvas:    ~1ms render time   ✅ GOOD (overkill)
└── DOM:       ~3ms render time   ✅ GOOD (simpler code)
```

---

### 7.3 Lazy Loading Strategy

**Image Loading Priority:**
```
Priority 1: Zone thumbnails (always visible)
Priority 2: Animation static thumbnails (above fold)
Priority 3: Animation GIF loops (on hover)
Priority 4: Custom preview generation (on demand)
```

**Implementation:**
```tsx
<img 
  src="/previews/thumbnails/breathe.png"
  loading="eager"  // Load immediately
/>

<img 
  src="/previews/loops/breathe_slow.gif"
  loading="lazy"   // Load when visible/hover
/>
```

---

## 🎨 Part 8: Component Library Summary

### 8.1 Core Components

**Zone Components:**
- `<ZoneCard>` - Main zone display with preview
- `<LEDStripPreview>` - Live pixel rendering
- `<ZoneList>` - Grid of all zones
- `<ZoneSelector>` - Dropdown for zone selection

**Color Components:**
- `<ColorPicker>` - Multi-mode color selector
- `<HuePicker>` - Hue slider (0-360°)
- `<RGBPicker>` - RGB sliders
- `<ColorSwatch>` - Color preview circle
- `<PresetPicker>` - Preset color buttons

**Animation Components:**
- `<AnimationCard>` - Animation with preview
- `<AnimationList>` - Grid of animations
- `<AnimationEditor>` - Full parameter editor
- `<AnimationPreview>` - Canvas/GIF preview

**Control Components:**
- `<AnimationParameter>` - Universal param control
- `<Slider>` - Range input with labels
- `<Toggle>` - Boolean switch
- `<Dropdown>` - Enum selector

**Layout Components:**
- `<LEDLayoutCanvas>` - 2D interactive layout
- `<LEDMatrix>` - Matrix grid display
- `<DashboardGrid>` - Responsive zone grid
- `<Sidebar>` - Navigation sidebar

---

## 🚀 Part 9: Implementation Checklist

### Phase 1: Core Zone Visualization (Week 1)
- [ ] Implement `ZoneCard` component
- [ ] Implement `LEDStripPreview` with WebSocket
- [ ] Add brightness slider
- [ ] Add quick action buttons
- [ ] Test with 3-4 zones

### Phase 2: Color Picker (Week 2)
- [ ] Implement `HuePicker` (primary mode)
- [ ] Implement `RGBPicker`
- [ ] Add preset buttons
- [ ] Add recent colors storage
- [ ] Test color changes with real LEDs

### Phase 3: Animation Previews (Week 3)
- [ ] Generate static thumbnails (backend)
- [ ] Generate animated GIF loops (backend)
- [ ] Implement `AnimationCard` with preview
- [ ] Add hover → GIF loading
- [ ] Test with 5-10 animations

### Phase 4: Animation Editor (Week 4)
- [ ] Implement `AnimationParameter` component
- [ ] Implement real-time canvas preview
- [ ] Add parameter sliders
- [ ] Add "Apply to LEDs" button
- [ ] Test parameter changes

### Phase 5: Advanced Features (Week 5+)
- [ ] Implement 2D canvas layout
- [ ] Add matrix visualization
- [ ] Add preset management
- [ ] Add scene management
- [ ] Performance optimization

---

## 📚 Additional Resources

### Related Documents:
- `DIUNA_VISION_AND_ROADMAP.md` - Overall project vision
- `ARCHITECTURE.md` - Backend architecture
- `Diuna LED Control System - Professional Architecture Refactoring Plan.md` - Refactoring strategy

### External References:
- React Canvas: https://konvajs.org/ (advanced canvas library)
- Color Theory: https://color.adobe.com/ (color harmony)
- LED Visualization: https://fastled.io/ (inspiration)

---

## 🎯 Success Criteria

**Visual Quality:**
- ✅ Smooth animations (no jank, 30+ FPS perceived)
- ✅ Accurate color representation (matches physical LEDs)
- ✅ Professional design (not "hobby project" aesthetic)

**Performance:**
- ✅ <100ms UI response time
- ✅ <50ms color picker interaction
- ✅ <500ms custom preview generation

**User Experience:**
- ✅ Intuitive without tutorial (first-time user success)
- ✅ Mobile-friendly (works on phone)
- ✅ Accessible (keyboard nav, screen readers)

**Technical:**
- ✅ Real-time WebSocket sync (<200ms latency)
- ✅ Efficient rendering (low CPU usage)
- ✅ Small bundle size (<2MB total including previews)



## 🎨 Part 10: Design Aesthetic & Visual Language

### 10.1 Dual Aesthetic Philosophy

Diuna's visual identity embraces two distinct yet complementary aesthetic directions that can be used separately or blended together. The user interface supports both themes with the ability to switch between them or create hybrid designs.

---

### 10.2 Theme A: Cyber-Tech Aesthetic

**Core Concept:** Electronics, circuitry, integrated circuits (IC chips - repeated motif), futurism, cyberpunk

**Visual Language:**
- Circuit board traces connecting elements
- IC chip package outlines (DIP, SOIC, QFP styles)
- Hexadecimal addresses and binary patterns  
- Neon glow effects (cyan, magenta, green)
- Monospace typography with technical feel
- Sharp angles, grid-based layouts
- Scanline overlays and CRT effects
- Logic gate symbols as icons

**Color Palette - Cyber:**
```
Primary:
- Neon Cyan:     #00FFFF - Electric glow
- Neon Magenta:  #FF00FF - Synthetic highlight
- Circuit Green: #00FF41 - Matrix code
- Deep Black:    #0A0A0F - Void background

Accents:
- Electric Blue:  #0080FF
- Purple Haze:    #8B00FF  
- Warning Orange: #FF6B00
```

---

### 10.3 Theme B: Organic-Nature Aesthetic

**Core Concept:** Forest, botanical motifs, natural systems, organic growth

**Visual Language:**
- Leaf vein patterns as connectors
- Branch and root structures
- Rounded, flowing shapes (no sharp corners)
- Wood grain and moss textures
- Warm, humanist typography
- Growth ring patterns (tree cross-sections)
- Soft shadows and natural gradients
- Botanical icons (leaves, flowers, seeds)

**Color Palette - Nature:**
```
Primary:
- Forest Green:  #2D5016 - Deep foliage
- Moss Green:    #4A7C2C - Living moss
- Bark Brown:    #3E2723 - Tree bark
- Sage Green:    #9CAF88 - Soft leaves

Accents:
- Sunrise Amber: #FFA726 - Morning light
- Sky Blue:      #64B5F6 - Clear sky
- Earth Brown:   #6D4C41 - Rich soil
```

---

### 10.4 Hybrid: Cyber-Organic Fusion

**Core Concept:** Technology and nature coexisting, bio-digital synthesis

**Visual Approach:**
- Circuit traces that resemble leaf veins
- Neon colors on organic shapes
- Bioluminescent glow effects
- Wood grain with embedded LED traces
- Moss-covered circuit board aesthetic
- Crystalline structures with electronic pulses

**Color Fusion:**
```
- Bio-Cyan:      #00FFB2 (cyan + green)
- Tech-Moss:     #4AFFA0 (neon green)
- Circuit-Amber: #FFB84D (warm tech glow)
- Void-Forest:   #0F1A0F (dark green-black)
```

---

### 10.5 Theme Implementation

**User Selection:**
Users can choose their preferred aesthetic in settings:
- **Cyber-Tech Mode:** Electronic, futuristic, sharp
- **Organic-Nature Mode:** Natural, flowing, warm
- **Hybrid Mode:** Best of both worlds
- **Intensity Slider:** 0-100% theme strength

**Contextual Theming:**
- Wearables projects → Default to Cyber-Tech
- Home ambient lighting → Default to Nature
- Per-zone theme override (mix themes in one UI)

---

---

*End of Document*
