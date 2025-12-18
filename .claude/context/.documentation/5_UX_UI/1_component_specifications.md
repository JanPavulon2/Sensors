# 🔧 Component Specifications

**Date**: 2025-12-10
**Status**: Detailed specifications for Phase 1 components
**Audience**: Frontend developers, component creators

---

## Table of Contents
1. [LED Visualization Components](#led-visualization)
2. [Color Control Components](#color-control)
3. [Animation Control Components](#animation-control)
4. [Zone Management Components](#zone-management)
5. [Layout & Container Components](#layout-containers)

---

## LED Visualization

### **LEDCanvasRenderer**

**Purpose**: Main canvas for rendering addressable LED pixels with realistic glow effects

**Props**:
```typescript
interface LEDCanvasRendererProps {
  // Data
  zones: ZoneCombined[];
  selectedZoneId?: ZoneID;

  // Visual
  orientation?: 'horizontal' | 'vertical'; // default: 'horizontal'
  pixelSize?: number; // default: 24px
  gapBetweenZones?: number; // default: 12px
  theme?: 'cyber' | 'nature'; // default: 'cyber'

  // Behavior
  zoom?: number; // default: 1.0
  pan?: { x: number; y: number };
  onZoneSelect?: (zoneId: ZoneID) => void;
  onPixelHover?: (zoneId: ZoneID, pixelIndex: number) => void;

  // Performance
  fps?: number; // default: 60
  enableGlowEffect?: boolean; // default: true
  enableColorBleeding?: boolean; // default: true
}
```

**Rendering Details**:
- **Pixel Structure**:
  - Core circle (actual LED color, r = 6px)
  - Glow layer 1 (blur 8px, opacity 0.6)
  - Glow layer 2 (blur 16px, opacity 0.3)
  - Bloom layer (blur 24px, opacity 0.15)

- **Color Bleeding**:
  - Each pixel adds 10% of its glow to neighbors
  - Dimmer pixels receive less glow from neighbors
  - Creates cohesive "strip" appearance

- **Brightness Scaling**:
  - Glow radius increases with brightness
  - Core brightness always matches actual color
  - Glow opacity scales: `opacity * (brightness / 255)`

**State**:
```typescript
const [canvas, setCanvas] = useState<HTMLCanvasElement>(null);
const [context, setContext] = useState<CanvasRenderingContext2D>(null);
const [hoveredPixel, setHoveredPixel] = useState<{ zone: ZoneID; pixel: number } | null>();
const [dimensions, setDimensions] = useState<{ width: number; height: number }>();
```

**Methods**:
- `render()` - Main render loop (called by requestAnimationFrame)
- `renderPixel(x, y, color, brightness)` - Single pixel rendering
- `getPixelAtCoordinate(x, y)` - Find zone/pixel at mouse position
- `zoomTo(factor)` - Zoom canvas
- `panTo(x, y)` - Pan view

**WebSocket Integration**:
- Listen for real-time frame updates (60 FPS)
- Buffer frames to avoid jank
- Graceful fallback to 30 FPS if lagging

---

### **LEDPixel**

**Purpose**: Individual LED pixel component with glow effect

**Props**:
```typescript
interface LEDPixelProps {
  color: [number, number, number]; // RGB
  brightness: number; // 0-255
  size?: number; // default: 24px
  glowIntensity?: number; // 0-1, default: 0.6
  showIndex?: boolean; // show pixel index on hover
  pixelIndex?: number;
  onHover?: () => void;
  onLeave?: () => void;
}
```

**CSS-based Rendering**:
```css
.led-pixel {
  width: var(--size);
  height: var(--size);
  border-radius: 50%;
  background: rgb(var(--r), var(--g), var(--b));
  box-shadow:
    0 0 8px rgb(var(--r), var(--g), var(--b), var(--glow-0)),
    0 0 16px rgb(var(--r), var(--g), var(--b), var(--glow-1)),
    0 0 24px rgb(var(--r), var(--g), var(--b), var(--glow-2));
  filter: brightness(var(--brightness-factor));
  transition: box-shadow 0.05s ease-out;
}
```

---

### **LEDZoneOverlay**

**Purpose**: Visual zone boundary markers on LED canvas

**Props**:
```typescript
interface LEDZoneOverlayProps {
  zones: ZoneCombined[];
  selectedZoneId?: ZoneID;
  pixelSize: number;
  gapBetweenZones: number;
  onZoneSelect: (zoneId: ZoneID) => void;
  editable?: boolean; // Allow dragging boundaries
  onBoundaryChange?: (zoneId: ZoneID, startPixel: number, endPixel: number) => void;
}
```

**Visual Elements**:
- Zone label above strip
- Subtle background highlight (per-zone color, 10% opacity)
- Left/right drag handles for boundary adjustment
- Click zone name to select

---

## Color Control

### **ColorControlPanel**

**Purpose**: Tab-based color control interface

**Props**:
```typescript
interface ColorControlPanelProps {
  currentColor: Color;
  mode: ColorMode; // 'HUE' | 'RGB' | 'PRESET' | 'PALETTE'
  onChange: (color: Color) => void;
  onModeChange: (mode: ColorMode) => void;
  defaultMode?: ColorMode;
}
```

**Tab Structure**:
- **HUE Tab** → HueWheelPicker
- **RGB Tab** → RGBSliderGroup
- **PRESET Tab** → PresetColorGrid
- **PALETTE Tab** → CustomPaletteBuilder (Phase 3)

**State**:
```typescript
const [activeTab, setActiveTab] = useState<ColorMode>('HUE');
const [recentColors, setRecentColors] = useState<Color[]>([]);
const [colorHistory, setColorHistory] = useState<Color[]>([]);
```

---

### **HueWheelPicker**

**Purpose**: Circular hue selector (0-360°)

**Props**:
```typescript
interface HueWheelPickerProps {
  hue: number; // 0-360
  saturation?: number; // 0-100, default: 100
  brightness?: number; // 0-100, default: 100
  onChange: (hue: number, saturation: number, brightness: number) => void;
  size?: number; // diameter, default: 200px
  showValue?: boolean; // default: true
}
```

**Features**:
- Canvas-rendered color wheel
- Central crosshair cursor
- Click or drag to select
- Tooltip showing HSB values
- Numerical hue input (0-360)
- Recent colors carousel (last 5)

**Rendering**:
- Divide circle into 360° segments
- Each segment is HSV(hue, 100%, 100%)
- Central click → full saturation
- Outer edge → pure hue

---

### **RGBSliderGroup**

**Purpose**: Individual RGB channel sliders

**Props**:
```typescript
interface RGBSliderGroupProps {
  red: number; // 0-255
  green: number; // 0-255
  blue: number; // 0-255
  onChange: (r: number, g: number, b: number) => void;
  showPreview?: boolean; // default: true
  showHex?: boolean; // default: true
}
```

**Layout**:
```
R ●───────● 255 [255 input field]
G ●───────● 255 [255 input field]
B ●───────● 255 [255 input field]

Preview: [████████] #FFFFFF
```

**Features**:
- Individual sliders (0-255)
- Numeric input fields
- Live color preview
- Hex color input/output
- Copy hex button

---

### **PresetColorGrid**

**Purpose**: Grid of 20 preset colors organized by category

**Props**:
```typescript
interface PresetColorGridProps {
  selectedPreset?: string;
  onSelect: (presetName: string, color: Color) => void;
  showCategories?: boolean; // default: true
  searchable?: boolean; // default: true
}
```

**Structure**:
```
Search: [________] [×]

BASIC COLORS
[●red] [●green] [●blue] [●yellow] [●cyan] [●magenta]

WARM TONES
[●orange] [●amber] [●pink] [●hot_pink]

COOL TONES
[●purple] [●violet] [●indigo]

NATURAL TONES
[●mint] [●lime] [●sky_blue] [●ocean] [●lavender]

WHITES
[●warm_white] [●white] [●cool_white]
```

**Features**:
- Expandable/collapsible categories
- Swatch preview with glow effect
- Selected swatch has border highlight
- Hover tooltip with preset name
- Search filter by name or category
- Copy hex button on swatch

**Data** (from colors.yaml):
```typescript
interface Preset {
  name: string;
  category: 'basic' | 'warm' | 'cool' | 'white' | 'natural';
  rgb: [number, number, number];
  isWhite?: boolean;
}
```

---

## Animation Control

### **AnimationControlPanel**

**Purpose**: Main animation configuration interface

**Props**:
```typescript
interface AnimationControlPanelProps {
  selectedAnimation?: AnimationID;
  parameters: Map<ParamID, any>;
  isPlaying: boolean;
  onAnimationSelect: (animId: AnimationID) => void;
  onParameterChange: (paramId: ParamID, value: any) => void;
  onPlay: () => void;
  onPause: () => void;
  onReset: () => void;
  onSavePreset: (name: string) => void;
  onLoadPreset: (presetId: string) => void;
}
```

**Layout**:
```
┌──────────────────────────────────┐
│ Animation: [BREATHE ▼]  [▶ Play] │
│                                  │
│ ┌────────────────────────────┐  │
│ │  Live Preview              │  │
│ │  ● ● ● ● ● ● ● ●          │  │
│ └────────────────────────────┘  │
│                                  │
│ Speed        ●──────── 50%       │
│ Intensity    ─────●──── 75%      │
│ Hue          ───────●── 240°     │
│                                  │
│ [Save Preset] [Reset]            │
└──────────────────────────────────┘
```

---

### **AnimationSelector**

**Purpose**: Dropdown to select animation

**Props**:
```typescript
interface AnimationSelectorProps {
  animations: AnimationConfig[];
  selectedId?: AnimationID;
  onSelect: (animId: AnimationID) => void;
  showDescription?: boolean; // default: true
  showThumbnail?: boolean; // default: true
}
```

**Features**:
- Dropdown with all 6 animations
- Thumbnail preview for each
- Description on hover
- Quick keyboard navigation (arrow keys)
- Disabled state for unavailable animations

---

### **ParameterSlider**

**Purpose**: Universal slider for animation parameters

**Props**:
```typescript
interface ParameterSliderProps {
  paramId: ParamID;
  paramName: string;
  value: number | string;
  min: number;
  max: number;
  step?: number;
  unit?: string; // '%', '°', 'px', etc.
  onChange: (value: number | string) => void;
  onLock?: () => void; // Lock parameter while adjusting others
  locked?: boolean;
  showValue?: boolean; // default: true
}
```

**Features**:
- Single slider for each parameter
- Lock button to prevent accidental changes
- Input field for direct numeric input
- Unit suffix (%, °, px)
- Min/max visualization
- Snap to step points
- Live preview

**Parameter Mapping**:
| ParamID | Min | Max | Step | Unit | Default |
|---------|-----|-----|------|------|---------|
| ANIM_SPEED | 1 | 100 | 10 | % | 50 |
| ANIM_INTENSITY | 0 | 100 | 10 | % | 75 |
| ANIM_LENGTH | 1 | 20 | 1 | px | 5 |
| ANIM_HUE_OFFSET | 1 | 180 | 5 | ° | 60 |
| ANIM_PRIMARY_COLOR_HUE | 0 | 360 | 10 | ° | 0 |

---

### **AnimationPreview**

**Purpose**: Mini strip showing animation preview

**Props**:
```typescript
interface AnimationPreviewProps {
  animation: AnimationID;
  parameters: Map<ParamID, any>;
  pixelCount?: number; // default: 8
  height?: number; // default: 40px
  isPlaying?: boolean;
  loopDuration?: number; // milliseconds, default: 2000
}
```

**Features**:
- 8-pixel miniature strip
- Plays animation on loop
- Updates in real-time as parameters change
- Glow effects same as main canvas
- Play/pause indicator

---

## Zone Management

### **ZoneCard**

**Purpose**: Compact zone control card

**Props**:
```typescript
interface ZoneCardProps {
  zone: ZoneCombined;
  isSelected?: boolean;
  isExpanded?: boolean;
  onSelect?: () => void;
  onExpand?: () => void;
  onCollapse?: () => void;
  onBrightnessChange?: (brightness: number) => void;
  onModeChange?: (mode: ZoneRenderMode) => void;
  onDelete?: () => void;
  onDuplicate?: () => void;
  onAddToGroup?: () => void;
  showActions?: boolean; // default: true
}
```

**Compact View** (Collapsed):
```
┌─────────────────────────────────┐
│ FLOOR                  ● ON     │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓ 18px               │
│ Mode: ANIMATION (Breathe)       │
│ Brightness ●──── 25%            │
│ [🎨 Edit]                       │
└─────────────────────────────────┘
```

**Expanded View** (Full Controls):
```
┌─────────────────────────────────┐
│ FLOOR                 ● ON      │
│ Zone: 0-18 | Pixels: 18         │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ ● ● ● ● ● ● ● ● ● ● ● ● │ │
│ │  LED Preview Strip         │ │
│ └─────────────────────────────┘ │
│                                 │
│ Color: [hue wheel]              │
│ Brightness: ●────── 25%         │
│ Mode: [STATIC ▼]                │
│                                 │
│ [Save] [Reset] [Delete]         │
└─────────────────────────────────┘
```

**Features**:
- Color swatch with glow
- Pixel count display
- Current mode indicator
- Brightness quick slider
- Quick action buttons
- Expandable for full controls
- Drag handles for reordering
- Long-press context menu (mobile)

---

### **ZonesList**

**Purpose**: Grid of all zone cards

**Props**:
```typescript
interface ZonesListProps {
  zones: ZoneCombined[];
  selectedZoneId?: ZoneID;
  onZoneSelect?: (zoneId: ZoneID) => void;
  viewMode?: 'grid' | 'list'; // default: 'grid'
  gridColumns?: number; // default: auto
  allowReordering?: boolean; // default: false
  onReorder?: (zones: ZoneID[]) => void;
}
```

**Features**:
- Responsive grid layout
- Drag-to-reorder (desktop)
- Swipe actions (mobile)
- Batch operations (multi-select)
- Filter/search by zone name
- Collapse all / expand all buttons

---

### **BrightnessSlider**

**Purpose**: Zone brightness control

**Props**:
```typescript
interface BrightnessSliderProps {
  brightness: number; // 0-255 or 0-100
  onChange: (brightness: number) => void;
  min?: number; // default: 0
  max?: number; // default: 255
  step?: number; // default: 1
  showValue?: boolean; // default: true
  showPercent?: boolean; // default: true
  icons?: { low: ReactNode; high: ReactNode }; // sun icons
}
```

**Visual**:
```
☀️ ●────────────── 100%
```

---

### **ZoneRenderModeToggle**

**Purpose**: Switch between STATIC / ANIMATION / OFF

**Props**:
```typescript
interface ZoneRenderModeToggleProps {
  currentMode: ZoneRenderMode; // 'STATIC' | 'ANIMATION' | 'OFF'
  onChange: (mode: ZoneRenderMode) => void;
  availableModes?: ZoneRenderMode[]; // default: all 3
}
```

**Visual**:
```
┌─────────────────────────────────┐
│ [STATIC ✓] [ANIMATION] [OFF]    │
└─────────────────────────────────┘
```

---

## Layout & Container

### **DesignShowcasePage**

**Purpose**: Component library and design prototype page

**Props**: None (page component)

**Sections**:
1. **Theme Toggle** - Switch between cyber/nature
2. **Component Library**
   - LED Canvas showcase
   - Color controls demo
   - Animation controls demo
   - Zone cards showcase
3. **Live Playground**
   - Full LED control interface
   - All components working together
   - Real-time WebSocket sync

**Routes**:
- `/future-design` - Main showcase
- `/future-design/components` - Component library
- `/future-design/playground` - Live playground

---

### **ResponsiveLayout**

**Purpose**: Adaptive layout for desktop/mobile

**Desktop (> 1200px)**:
- Left sidebar (nav)
- Main canvas area
- Right control panel
- Fixed positioning

**Tablet (768px - 1200px)**:
- Top nav bar
- Collapsible sidebar
- Canvas takes 60% width
- Controls below canvas

**Mobile (< 768px)**:
- Top nav bar
- Full-width canvas
- Bottom control panels (tabs)
- Collapsible sections

---

## Theme System

### **Design Tokens**

**Cyber Theme**:
```typescript
const cyberTheme = {
  background: '#0a0e14',
  surface: 'rgba(20, 25, 35, 0.6)',
  accent: '#00f5ff',
  accent2: '#b721ff',
  accent3: '#00ff88',
  text: '#e8eaed',
  textDim: '#8894a8',
};
```

**Nature Theme**:
```typescript
const natureTheme = {
  background: '#0d1a0a',
  surface: 'rgba(20, 35, 25, 0.6)',
  accent: '#4ecca3',
  accent2: '#ff8c42',
  accent3: '#ffd700',
  text: '#e8eaed',
  textDim: '#8aa878',
};
```

---

## Responsive Breakpoints

```typescript
const breakpoints = {
  mobile: 0,
  tablet: 768,
  desktop: 1200,
  wide: 1920,
};
```

---

## Accessibility

### **Color Contrast**
- Text on surface: WCAG AA (4.5:1 minimum)
- Interactive elements: WCAG AA (4.5:1 minimum)
- Glow effects: Supplementary (not primary method of indication)

### **Keyboard Navigation**
- Tab through all interactive elements
- Enter/Space to activate buttons
- Arrow keys for sliders and selection
- Escape to close modals/menus

### **Screen Readers**
- Semantic HTML
- ARIA labels on all controls
- Live regions for status updates
- Descriptive alt text

---

## Performance Considerations

### **Canvas Rendering**
- Use `requestAnimationFrame` for smooth updates
- Buffer WebSocket frames (skip if lagging)
- Implement virtual scrolling for large zone lists
- Lazy load animations (don't render all at once)

### **WebSocket**
- Reconnect on disconnect (exponential backoff)
- Debounce parameter changes (50ms)
- Throttle canvas redraws (16ms = 60 FPS)

---

*Created for Phase 1 implementation of Diuna UX/UI System*
