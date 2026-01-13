# 🎨 Future Design UX/UI System

**Diuna LED Control System - Phase 1: LED Strip Control**

This folder contains the complete UX/UI design and implementation for the next-generation Diuna LED control interface. It's a completely isolated, prototype environment that doesn't interfere with the existing working app.

---

## 📂 Project Structure

```
future-design/
├── components/              # Reusable React components
│   ├── LEDVisualization/   # LED canvas and pixel rendering
│   ├── ColorControls/       # Color picker variants
│   ├── AnimationControls/   # Animation selectors & parameters
│   ├── ZoneControls/        # Zone management cards
│   ├── Layout/              # Page layout components
│   └── Shared/              # Utility components
│
├── pages/                   # Full page components
│   ├── DesignShowcase.tsx   # Component library (main demo)
│   └── ControlPanel.tsx     # Live control interface (coming soon)
│
├── hooks/                   # Custom React hooks
│   ├── useLEDCanvas.ts      # Canvas rendering logic
│   ├── useColorPicker.ts    # Color selection state
│   ├── useAnimationPreview.ts
│   ├── useWebSocketLED.ts   # Real-time updates
│   └── useResponsive.ts     # Breakpoint detection
│
├── store/                   # Zustand state management
│   ├── designStore.ts       # Main store with selectors
│   └── types.ts             # Store type definitions
│
├── styles/                  # Global styles & themes
│   ├── design-tokens.css    # CSS custom properties
│   ├── theme-cyber.css      # Cyber/futuristic theme
│   ├── theme-nature.css     # Nature/organic theme
│   └── animations.css       # Micro-animation definitions
│
├── utils/                   # Utility functions
│   ├── colors.ts            # Color conversions & helpers
│   ├── animations.ts        # Animation utilities
│   ├── canvas.ts            # Canvas helpers
│   └── performance.ts       # Performance optimization
│
├── types/                   # TypeScript definitions
│   └── index.ts             # All type definitions
│
└── README.md               # This file
```

---

## 🎯 Quick Start

### Access the Design Showcase

The design showcase is available at:
```
http://localhost:5173/future-design
```

This page demonstrates all Phase 1 components and design tokens.

### Initialize the Store

The design store is automatically initialized when any component mounts. To manually initialize:

```typescript
import { initializeDesignStore } from './store/designStore';

useEffect(() => {
  initializeDesignStore();
}, []);
```

### Use Theme Switching

```typescript
import { useThemeSwitch } from './store/designStore';

export function MyComponent() {
  const { theme, toggleTheme, setTheme } = useThemeSwitch();

  return (
    <button onClick={toggleTheme}>
      Switch from {theme} to {theme === 'cyber' ? 'nature' : 'cyber'}
    </button>
  );
}
```

---

## 🎨 Design System

### Color Modes

**1. HUE Mode (Circular Wheel)**
```typescript
const color: Color = { mode: 'HUE', hue: 240 }; // 240° = Blue
```

**2. RGB Mode (Direct Control)**
```typescript
const color: Color = { mode: 'RGB', rgb: [255, 0, 0] }; // Red
```

**3. PRESET Mode (Curated Colors)**
```typescript
const color: Color = { mode: 'PRESET', preset: 'red' };
```

### 20 Preset Colors

```
Basic: red, green, blue, yellow, cyan, magenta
Warm: orange, amber, pink, hot_pink
Cool: purple, violet, indigo
Natural: mint, lime, sky_blue, ocean, lavender
Whites: warm_white, white, cool_white
```

### Themes

**Cyber Theme** (`cybernetic-theme`)
- Colors: Deep black background, cyan/purple/green neon accents
- Feel: Futuristic, circuit-board inspired
- Best for: High-energy, tech-focused users

**Nature Theme** (`nature-theme`)
- Colors: Forest black background, green/orange/gold accents
- Feel: Organic, shamanic, natural
- Best for: Meditation, ambient mood, nature lovers

---

## 🚀 Component Usage

### Using Color Controls

```typescript
import { ColorControlPanel } from './components/ColorControls/ColorControlPanel';
import { useColorController } from './store/designStore';

export function MyColorPicker() {
  const { color, mode, setColor, setMode } = useColorController();

  return (
    <ColorControlPanel
      currentColor={color}
      mode={mode}
      onChange={setColor}
      onModeChange={setMode}
    />
  );
}
```

### Using Animation Controls

```typescript
import { AnimationControlPanel } from './components/AnimationControls/AnimationControlPanel';
import { useAnimationController } from './store/designStore';

export function MyAnimationControl() {
  const { selectedAnimation, parameters, updateParameter } = useAnimationController();

  return (
    <AnimationControlPanel
      selectedAnimation={selectedAnimation}
      parameters={parameters}
      onParameterChange={updateParameter}
      isPlaying={true}
      onPlay={() => {}}
      onPause={() => {}}
      onReset={() => {}}
    />
  );
}
```

### Using Zone Controls

```typescript
import { ZoneCard } from './components/ZoneControls/ZoneCard';
import { useZoneById } from './store/designStore';

export function MyZoneControl({ zoneId }) {
  const zone = useZoneById(zoneId);

  if (!zone) return null;

  return (
    <ZoneCard
      zone={zone}
      onBrightnessChange={(brightness) => {
        // Update via API
      }}
    />
  );
}
```

---

## 🎬 Animations (6 Types)

| ID | Name | Icon | Type | Parameters |
|-----|------|------|------|------------|
| BREATHE | Breathing Pulse | ⊙ | Ambient | Speed, Intensity, Color |
| COLOR_FADE | Rainbow Rotation | 🌈 | Color | Speed, Intensity |
| COLOR_CYCLE | Color Steps | 🎨 | Color | None (hardcoded) |
| SNAKE | Pixel Chase | 🐍 | Motion | Speed, Length, Color |
| COLOR_SNAKE | Rainbow Chase | 🌈🐍 | Motion | Speed, Length, Color, Hue Offset |
| MATRIX | Code Rain | 📟 | Effect | Speed, Length, Intensity, Color |

---

## 🔧 Utility Functions

### Color Conversions

```typescript
import {
  hueToRGB,
  rgbToHue,
  rgbToHex,
  hexToRGB,
  applyBrightness,
  getGlowBoxShadow,
  getDefaultPresets,
  getPresetByName,
} from './utils/colors';

// Hue to RGB
const rgb = hueToRGB(240); // [0, 0, 255] - Blue

// RGB to Hex
const hex = rgbToHex(255, 0, 0); // "#FF0000"

// Get preset color
const redPreset = getPresetByName('red');

// Apply brightness
const dimmedRed = applyBrightness([255, 0, 0], 0.5); // [127, 0, 0]

// Get glow shadow
const shadow = getGlowBoxShadow([0, 245, 255], 200);
```

---

## 📊 State Management

### Main Store

```typescript
import { useDesignStore } from './store/designStore';

export function MyComponent() {
  const zones = useDesignStore((state) => state.zones);
  const updateParameter = useDesignStore((state) => state.updateParameter);

  return <div>Zones: {zones.size}</div>;
}
```

### Convenient Selectors

```typescript
import {
  useDesignTheme,
  useSelectedZone,
  useZones,
  useColorControl,
  useAnimationState,
  useAnimationPresets,
  useSortedZones,
  useZoneCount,
  useTotalPixelCount,
} from './store/designStore';

// These only re-render when their specific values change
const theme = useDesignTheme();
const zones = useZones();
const colorControl = useColorControl();
```

---

## 🎯 Development Guidelines

### Adding a New Component

1. **Create component file**:
   ```
   components/MyComponent/
   ├── MyComponent.tsx
   ├── MyComponent.module.css
   └── useMyComponent.ts (if needed)
   ```

2. **Use TypeScript**:
   ```typescript
   import type { MyComponentProps } from '@/future-design/types';

   export const MyComponent: React.FC<MyComponentProps> = ({ prop1, prop2 }) => {
     // Implementation
   };
   ```

3. **Follow design tokens**:
   ```css
   .myComponent {
     background-color: var(--theme-surface);
     color: var(--theme-text);
     border: 1px solid var(--theme-border);
     border-radius: var(--radius-md);
     padding: var(--space-4);
   }
   ```

4. **Use store selectors for performance**:
   ```typescript
   const myValue = useMyStore((state) => state.myValue);
   ```

### Color Handling

Always use the color utilities for conversions:

```typescript
import { hueToRGB, rgbToHex } from './utils/colors';

// Don't: manually compute hue→RGB
// Do: use hueToRGB()
const rgb = hueToRGB(240);
```

### Performance Tips

1. **Use React.memo for pure components**
2. **Use Zustand selectors to minimize re-renders**
3. **Debounce WebSocket messages (50ms)**
4. **Throttle canvas redraws (16ms = 60 FPS)**
5. **Lazy load heavy components**

---

## 🌐 Integration with Main App

### Accessing from Main App

Add a route in your main app:

```typescript
import { lazy } from 'react';

const DesignShowcase = lazy(() =>
  import('./future-design/pages/DesignShowcase')
);

// In your router:
<Route path="/future-design" element={<DesignShowcase />} />
```

### Avoiding Conflicts

- ✅ Store is isolated (uses `diuna-design-store` persistence key)
- ✅ Styles are scoped (uses class-based theming)
- ✅ Components are in separate folder
- ✅ No modifications to existing app code

---

## 📝 Documentation Index

External documentation is in `.claude/context/5_UX_UI/`:

- **0_design_vision.md** - Complete UX/UI design vision
- **1_component_specifications.md** - Detailed component APIs
- **2_animation_specifications.md** - Animation system details
- **3_technical_architecture.md** - Frontend architecture
- **4_color_system.md** - Color system & design tokens

---

## 🔮 Phase Roadmap

### Phase 1: Foundation (Current)
- ✅ Design vision & specifications
- ✅ Store & utilities
- ✅ Color system
- 🚧 LED Canvas Renderer
- 🚧 Color Control System
- 🚧 Animation Controls
- 🚧 Zone Management

### Phase 2: Multi-Zone
- Zone grouping
- Scene save/load
- Layout editor
- Batch operations

### Phase 3: Advanced
- Animation timeline editor
- Custom animation builder
- Palette creator
- Effect library

### Phase 4: Mobile
- Touch gesture controls
- Mobile-optimized UI
- Quick action widget
- Haptic feedback

### Phase 5: Clothing
- Garment templates
- Freehand LED placement
- 3D preview
- Manufacturing export

---

## 🤝 Contributing

When adding new features:

1. Keep everything in `future-design/` folder
2. Follow design token conventions
3. Update type definitions
4. Write components with TypeScript
5. Create unit tests in `__tests__/`
6. Document complex components
7. Test with both themes

---

## 📞 Questions?

Refer to the documentation in `.claude/context/5_UX_UI/` or check the inline code comments.

---

**Created with 💜 for the Diuna LED Control System**

*Phase 1 Status: Design complete, implementation in progress*
