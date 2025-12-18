# 🏗️ Technical Architecture

**Date**: 2025-12-10
**Status**: Frontend architecture for Phase 1+
**Audience**: Frontend developers, architects

---

## Table of Contents
1. [Technology Stack](#stack)
2. [Folder Structure](#structure)
3. [State Management](#state)
4. [Component Hierarchy](#hierarchy)
5. [Data Flow & WebSocket](#dataflow)
6. [Performance Strategy](#performance)

---

## Technology Stack

### **Core Frontend**
- **Framework**: React 18+ (already in use)
- **TypeScript**: Strict mode
- **Package Manager**: npm

### **UI & Styling**
- **Component Library**: Shadcn/UI (already in use)
- **Styling**: Tailwind CSS + CSS-in-JS (dynamic colors)
- **Icons**: Lucide React (already in use)
- **Animations**: Framer Motion (existing dependency)

### **Canvas Rendering**
- **Option 1**: HTML Canvas + vanilla JS (simple, no deps)
- **Option 2**: Konva.js (more features, ~100KB)
- **Option 3**: Three.js (overkill for Phase 1, but extensible)
- **Recommendation**: HTML Canvas for Phase 1, upgrade to Konva for Phase 2

### **State Management**
- **Store**: Zustand (already in use)
- **State**: Separate design store isolated from existing app

### **Real-Time Communication**
- **WebSocket**: Socket.io-client or native WebSocket
- **HTTP**: Axios (already in use)

### **Testing**
- **Framework**: Vitest (already configured)
- **Component Testing**: React Testing Library (already configured)
- **E2E**: Cypress (optional, for Phase 3+)

### **Development Tools**
- **Build**: Vite (already in use)
- **Linting**: ESLint (already configured)
- **Formatting**: Prettier (already configured)
- **Type Checking**: TypeScript strict mode

---

## Folder Structure

### **Complete Layout**

```
frontend/src/
├── components/                         # Existing app components
│   └── (untouched)
│
├── pages/                              # Existing app pages
│   └── (untouched)
│
├── future-design/                      # ← NEW UX/UI PROTOTYPE
│   ├── components/                     # Reusable components
│   │   ├── LEDVisualization/
│   │   │   ├── LEDCanvas.tsx           # Main canvas renderer
│   │   │   ├── LEDPixel.tsx            # Individual pixel
│   │   │   ├── LEDZoneOverlay.tsx      # Zone boundaries
│   │   │   ├── LEDCanvas.module.css
│   │   │   └── useCanvasRenderer.ts
│   │   │
│   │   ├── ColorControls/
│   │   │   ├── ColorControlPanel.tsx   # Tab switcher
│   │   │   ├── HueWheelPicker.tsx      # Hue selector
│   │   │   ├── RGBSliderGroup.tsx      # RGB sliders
│   │   │   ├── PresetColorGrid.tsx     # 20 presets
│   │   │   ├── ColorControls.module.css
│   │   │   └── colorUtils.ts
│   │   │
│   │   ├── AnimationControls/
│   │   │   ├── AnimationControlPanel.tsx  # Main panel
│   │   │   ├── AnimationSelector.tsx      # Dropdown
│   │   │   ├── ParameterSlider.tsx        # Single param
│   │   │   ├── AnimationPreview.tsx       # Mini strip
│   │   │   ├── AnimationControls.module.css
│   │   │   └── useAnimationPreview.ts
│   │   │
│   │   ├── ZoneControls/
│   │   │   ├── ZoneCard.tsx
│   │   │   ├── ZonesList.tsx
│   │   │   ├── BrightnessSlider.tsx
│   │   │   ├── ZoneRenderModeToggle.tsx
│   │   │   ├── ZoneControls.module.css
│   │   │   └── zoneUtils.ts
│   │   │
│   │   ├── Layout/
│   │   │   ├── DesignHeader.tsx         # Top nav
│   │   │   ├── DesignSidebar.tsx        # Left nav
│   │   │   ├── ResponsiveContainer.tsx  # Adaptive layout
│   │   │   └── Layout.module.css
│   │   │
│   │   └── Shared/
│   │       ├── ThemeToggle.tsx          # Cyber/Nature
│   │       ├── StatCard.tsx             # Info cards
│   │       └── Shared.module.css
│   │
│   ├── pages/                          # Page components
│   │   ├── DesignShowcase.tsx           # Component library
│   │   ├── DesignShowcase.module.css
│   │   ├── ControlPanel.tsx             # Live control interface
│   │   ├── ControlPanel.module.css
│   │   └── index.tsx                    # Router setup
│   │
│   ├── hooks/                          # Custom hooks
│   │   ├── useLEDCanvas.ts              # Canvas rendering logic
│   │   ├── useColorPicker.ts            # Color selection
│   │   ├── useAnimationPreview.ts       # Animation loop
│   │   ├── useWebSocketLED.ts           # Real-time updates
│   │   ├── useZoneManager.ts            # Zone operations
│   │   └── useResponsive.ts             # Breakpoint detection
│   │
│   ├── store/                          # Zustand stores
│   │   ├── designStore.ts               # Main design state
│   │   ├── types.ts                     # Type definitions
│   │   └── index.ts                     # Export barrel
│   │
│   ├── styles/                         # Global styles
│   │   ├── design-tokens.css            # Color/spacing vars
│   │   ├── theme-cyber.css              # Cyber theme
│   │   ├── theme-nature.css             # Nature theme
│   │   ├── animations.css               # UI animations
│   │   └── index.css
│   │
│   ├── utils/                          # Utility functions
│   │   ├── colors.ts                    # Color conversion
│   │   ├── animations.ts                # Animation helpers
│   │   ├── canvas.ts                    # Canvas utilities
│   │   └── performance.ts               # RAF, debounce, etc.
│   │
│   ├── types/                          # TypeScript types
│   │   ├── animation.ts
│   │   ├── color.ts
│   │   ├── zone.ts
│   │   └── index.ts
│   │
│   └── README.md                        # Phase-specific docs
│
├── (existing structure untouched)
```

---

## State Management

### **Zustand Design Store**

```typescript
// store/designStore.ts

interface DesignState {
  // UI State
  theme: 'cyber' | 'nature';
  selectedZoneId: ZoneID | null;
  selectedAnimation: AnimationID | null;
  showAnimationPreview: boolean;

  // Data State
  zones: Map<ZoneID, ZoneCombined>;
  animationParameters: Map<ParamID, any>;
  colorMode: ColorMode; // 'HUE' | 'RGB' | 'PRESET'
  currentColor: Color;

  // Local Presets
  animationPresets: AnimationPreset[];
  colorPresets: ColorPreset[];

  // Actions
  actions: {
    // Theme
    setTheme: (theme: 'cyber' | 'nature') => void;

    // Zone Selection
    selectZone: (zoneId: ZoneID) => void;
    updateZoneColor: (zoneId: ZoneID, color: Color) => void;
    updateZoneBrightness: (zoneId: ZoneID, brightness: number) => void;
    updateZoneMode: (zoneId: ZoneID, mode: ZoneRenderMode) => void;

    // Animation
    selectAnimation: (animId: AnimationID) => void;
    updateParameter: (paramId: ParamID, value: any) => void;
    playAnimation: () => void;
    pauseAnimation: () => void;
    resetAnimation: () => void;

    // Presets
    saveAnimationPreset: (name: string, config: AnimationPreset) => void;
    loadAnimationPreset: (presetId: string) => void;
    deleteAnimationPreset: (presetId: string) => void;

    // Real-time Sync
    syncZonesFromBackend: (zones: ZoneCombined[]) => void;
  };
}

export const useDesignStore = create<DesignState>((set, get) => ({
  theme: 'cyber',
  selectedZoneId: null,
  selectedAnimation: null,
  showAnimationPreview: true,
  zones: new Map(),
  animationParameters: new Map(),
  colorMode: 'HUE',
  currentColor: { mode: 'HUE', hue: 0 },
  animationPresets: [],
  colorPresets: [],

  actions: {
    setTheme: (theme) => set({ theme }),
    selectZone: (zoneId) => set({ selectedZoneId: zoneId }),
    updateZoneColor: (zoneId, color) => {
      // Update via WebSocket to backend
      // Then sync back to store
    },
    // ... other actions
  },
}));
```

### **Store Selectors**

```typescript
// Selectors for performance (only re-render if selected value changes)
export const useTheme = () => useDesignStore((s) => s.theme);
export const useSelectedZone = () => useDesignStore((s) => s.selectedZoneId);
export const useZones = () => useDesignStore((s) => s.zones);
export const useAnimationParams = () =>
  useDesignStore((s) => s.animationParameters);
```

---

## Component Hierarchy

### **Page Level**

```
DesignShowcasePage (/)
├── DesignHeader
├── DesignSidebar (nav)
└── ComponentLibrary
    ├── LEDCanvasShowcase
    ├── ColorControlsShowcase
    ├── AnimationControlsShowcase
    └── ZoneControlsShowcase

ControlPanelPage (/control)
├── DesignHeader
└── ResponsiveContainer
    ├── LEDCanvasRenderer (main)
    ├── RightPanel (desktop) / BottomPanel (mobile)
    │   ├── ColorControlPanel
    │   ├── AnimationControlPanel
    │   └── ZonesList
    └── Sidebars
```

### **Component Composition**

```
LEDCanvasRenderer
├── Canvas (HTML canvas element)
├── LEDZoneOverlay
│   ├── ZoneLabel (per zone)
│   └── BoundaryHandle (per boundary)
└── Tooltip (pixel info on hover)

ColorControlPanel
├── Tabs (HUE | RGB | PRESET)
├── HueWheelPicker
│   ├── Canvas (hue wheel)
│   ├── Crosshair cursor
│   ├── Input field (0-360°)
│   └── Recent colors
├── RGBSliderGroup
│   ├── Slider (R)
│   ├── Slider (G)
│   ├── Slider (B)
│   ├── Input fields
│   └── Hex preview
└── PresetColorGrid
    ├── Category (expandable)
    ├── ColorSwatch (per preset)
    └── Search input

AnimationControlPanel
├── AnimationSelector (dropdown)
├── AnimationPreview (mini strip)
├── ParameterSlider (per param)
│   ├── Slider
│   ├── Input field
│   ├── Lock button
│   └── Unit label
└── PlaybackControls
    ├── Play button
    ├── Pause button
    ├── Reset button
    └── Preset buttons

ZonesList
├── ZoneCard (per zone)
│   ├── Zone name + pixel count
│   ├── Color preview
│   ├── Mode indicator
│   ├── Brightness slider
│   ├── Quick action buttons
│   └── ExpandableContent
│       └── Full controls
```

---

## Data Flow & WebSocket

### **Real-time Update Flow**

```
Backend LED System
       │
       │ WebSocket: frame_update
       ↓
LEDCanvas Component
       │
       ├→ Stores frame in buffer
       │
       └→ requestAnimationFrame
           │
           ├→ Render pixels from buffer
           │
           ├→ Apply glow effects
           │
           └→ Display on canvas (60 FPS)
```

### **User Input Flow**

```
User adjusts color picker
       │
       ├→ Dispatches store action
       │
       ├→ Store updates color
       │
       ├→ Component re-renders (live preview)
       │
       └→ Debounce (50ms)
           │
           └→ Send WebSocket message to backend
               │
               └→ Backend updates LED
                   │
                   └→ Broadcasts update
                       │
                       └→ All clients receive update
```

### **WebSocket Message Format**

**Server → Client (Real-time Frame Data)**:
```json
{
  "type": "frame_update",
  "timestamp": 1702224600000,
  "zones": {
    "floor": {
      "pixels": [[255, 0, 0], [200, 0, 50], ...],
      "brightness": 200
    },
    "lamp": { ... }
  }
}
```

**Client → Server (Parameter Change)**:
```json
{
  "type": "zone_update",
  "zone_id": "floor",
  "color": {
    "mode": "HUE",
    "hue": 240
  }
}
```

---

## Performance Strategy

### **1. Canvas Rendering Optimization**

**Technique**: Double buffering
```typescript
const renderFrame = () => {
  // Draw to off-screen canvas
  offscreenCanvas.clearRect(0, 0, width, height);
  for (const zone of zones) {
    for (const pixel of zone.pixels) {
      drawPixel(offscreenCanvas, pixel);
    }
  }

  // Blit to main canvas
  mainContext.drawImage(offscreenCanvas, 0, 0);
};
```

**Technique**: Throttle updates
```typescript
let lastFrameTime = 0;
const targetFPS = 60;
const frameDelay = 1000 / targetFPS;

const animate = (now) => {
  if (now - lastFrameTime >= frameDelay) {
    renderFrame();
    lastFrameTime = now;
  }
  requestAnimationFrame(animate);
};
```

### **2. Component Rendering Optimization**

**Technique**: React.memo for components that don't need re-renders
```typescript
const LEDPixel = React.memo(({ color, brightness }: LEDPixelProps) => {
  return <div className="led-pixel" style={{ ... }} />;
});
```

**Technique**: Zustand selectors to prevent unnecessary re-renders
```typescript
// Only re-render if selectedZoneId changes
const zoneId = useDesignStore((s) => s.selectedZoneId);
```

### **3. WebSocket Optimization**

**Technique**: Frame buffer with skip logic
```typescript
const frameBuffer: Frame[] = [];
const maxBufferSize = 5;

const onFrameUpdate = (frame: Frame) => {
  if (frameBuffer.length >= maxBufferSize) {
    frameBuffer.shift(); // Drop oldest
  }
  frameBuffer.push(frame);
};

const renderFrame = () => {
  if (frameBuffer.length > 0) {
    const frame = frameBuffer.shift();
    render(frame);
  }
};
```

**Technique**: Debounce parameter changes
```typescript
import { debounce } from '../utils/performance';

const debouncedUpdate = debounce((value) => {
  sendWebSocketUpdate(value);
}, 50);

const handleSliderChange = (value) => {
  updateLocalState(value);
  debouncedUpdate(value);
};
```

### **4. Memory Optimization**

**Technique**: Reuse canvas context
```typescript
const canvas = useRef<HTMLCanvasElement>(null);
const ctx = useRef<CanvasRenderingContext2D | null>(null);

useEffect(() => {
  ctx.current = canvas.current?.getContext('2d');
}, []);
```

**Technique**: Lazy load components
```typescript
const ColorControlPanel = lazy(() =>
  import('./ColorControls/ColorControlPanel')
);

// In JSX:
<Suspense fallback={<div>Loading...</div>}>
  <ColorControlPanel />
</Suspense>
```

### **5. CSS Performance**

**Technique**: Use CSS transforms for smooth animations
```css
.led-pixel {
  will-change: transform; /* Hint to browser */
  transition: transform 0.05s ease-out;
}

.slider-thumb:active {
  transform: scale(1.1); /* GPU-accelerated */
}
```

**Technique**: Minimize repaints
```css
/* Bad: changes layout on hover */
.button:hover {
  padding: 12px 16px;
}

/* Good: uses transform */
.button:hover {
  transform: scale(1.05);
}
```

### **Performance Targets**

| Metric | Target | Acceptable |
|--------|--------|------------|
| Canvas FPS | 60 | 30+ |
| Parameter slider response | < 50ms | < 100ms |
| Color picker update | < 16ms | < 30ms |
| Zone card re-render | < 16ms | < 30ms |
| WebSocket latency | < 50ms | < 200ms |
| First paint | < 1s | < 2s |
| Time to interactive | < 2s | < 3s |

---

## Build & Deployment

### **Development**

```bash
npm run dev              # Start Vite dev server
npm run type-check      # Check TypeScript
npm run lint            # ESLint
npm run format          # Prettier
npm run test            # Run tests
```

### **Production**

```bash
npm run build           # Bundle for production
npm run preview         # Preview production build
```

### **Code Splitting**

```typescript
// Lazy load heavy components
const DesignShowcase = lazy(() => import('./pages/DesignShowcase'));
const ControlPanel = lazy(() => import('./pages/ControlPanel'));

// Use in router
<Routes>
  <Route path="/future-design" element={<DesignShowcase />} />
  <Route path="/future-design/control" element={<ControlPanel />} />
</Routes>
```

---

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile: iOS Safari 14+, Chrome Android 90+

**Features that may require polyfills**:
- Canvas (built-in)
- WebSocket (built-in)
- CSS Grid (built-in)
- CSS Custom Properties (built-in)

---

## Testing Strategy

### **Unit Tests**

```typescript
// colorUtils.test.ts
describe('Color Utilities', () => {
  test('converts HUE to RGB correctly', () => {
    expect(hueToRGB(240)).toEqual([0, 0, 255]);
  });
});
```

### **Component Tests**

```typescript
// LEDPixel.test.tsx
describe('LEDPixel', () => {
  test('renders with correct color', () => {
    render(<LEDPixel color={[255, 0, 0]} brightness={255} />);
    const element = screen.getByRole('img');
    expect(element).toHaveStyle('background: rgb(255, 0, 0)');
  });
});
```

### **Integration Tests**

```typescript
// ColorControlPanel.test.tsx
describe('ColorControlPanel', () => {
  test('updates preview when hue wheel changes', async () => {
    render(<ColorControlPanel />);
    const canvas = screen.getByRole('img');
    fireEvent.click(canvas, { clientX: 100, clientY: 100 });
    await waitFor(() => {
      expect(screen.getByDisplayValue(/^#[0-9a-f]{6}$/i)).toBeInTheDocument();
    });
  });
});
```

---

## Documentation

### **README.md Structure**

```
# Future Design - Phase 1

## Quick Start
- Installation
- Running the showcase

## Features
- LED Canvas Renderer
- Color Controls
- Animation Controls
- Zone Management

## Component API
- [LEDCanvasRenderer]
- [ColorControlPanel]
- [AnimationControlPanel]
- [ZoneCard]

## Adding New Components
- Directory structure
- File naming
- TypeScript patterns
- Testing

## Performance Tips
- Canvas rendering
- Component optimization
- WebSocket best practices

## Roadmap
- Phase 2
- Phase 3
- Phase 4
- Phase 5
```

---

*Created for Phase 1 implementation of Diuna UX/UI System*
