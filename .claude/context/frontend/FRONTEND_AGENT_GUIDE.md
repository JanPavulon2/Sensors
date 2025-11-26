# Diuna App - Frontend Development Guide

## 🎯 Project Overview

**Diuna App** is a web-based LED animation design and control application for wearables, home lighting, automotive, and art installations. This is the frontend demonstration layer for the Diuna LED System backend.

**Purpose:** Real-time visual LED control, animation design, and preset management  
**Target Users:** LED enthusiasts, makers, fashion designers, artists, home automation users  
**Key Differentiator:** Hardware-agnostic design tool that exports to multiple platforms (FastLED, WLED, native)

---

## 🏗️ Tech Stack

### Core Framework
```
React 18.2+            # Modern React with hooks, concurrent features
TypeScript 5.0+        # Type safety throughout
Vite 5.0+              # Fast build tool, HMR, optimized production builds
```

### UI & Styling
```
Tailwind CSS 3.4+      # Utility-first styling
Shadcn/ui              # Beautiful, accessible components (Radix UI primitives)
Lucide React           # Icon library (lightweight, consistent)
Framer Motion 11+      # Smooth animations, gestures
```

### State Management
```
Zustand 4.5+           # Lightweight global state (< 1KB!)
TanStack Query v5      # Server state, caching, automatic refetching
Jotai 2.0+             # Atomic state for complex forms (optional, use sparingly)
```

### Canvas & Visualization
```
React Konva 18+        # 2D canvas for LED visualization (React wrapper for Konva.js)
Konva 9+               # Canvas rendering engine
```

**Alternative Options (evaluate based on needs):**
```
Fabric.js              # If advanced canvas manipulation needed
Three.js + R3F         # If 3D garment preview needed (Phase 2+)
```

### Color Tools
```
Culori 4.0+            # Color space conversions (HSV, HSL, LAB, etc.)
react-colorful 5.6+    # Lightweight color picker (< 3KB)
```

### Communication
```
Socket.IO Client 4.7+  # WebSocket for real-time state sync
Axios 1.6+             # HTTP client for REST API
```

### Development Tools
```
ESLint 8+              # Linting (with TypeScript rules)
Prettier 3+            # Code formatting
Vitest 1.0+            # Unit testing (Vite-native, fast)
Playwright 1.40+       # E2E testing
```

---

## 📁 Project Structure

```
frontend/
├── public/
│   ├── favicon.ico
│   └── assets/           # Static assets (images, fonts)
│
├── src/
│   ├── main.tsx          # Entry point
│   ├── App.tsx           # Root component with routing
│   │
│   ├── components/       # Reusable UI components
│   │   ├── ui/          # Shadcn/ui components (Button, Card, etc.)
│   │   ├── canvas/      # LED visualization components
│   │   │   ├── LEDCanvas.tsx
│   │   │   ├── ZoneVisualization.tsx
│   │   │   └── LivePreview.tsx
│   │   ├── zones/       # Zone control components
│   │   │   ├── ZoneList.tsx
│   │   │   ├── ZoneCard.tsx
│   │   │   └── ZoneEditor.tsx
│   │   ├── animations/  # Animation browser/editor
│   │   │   ├── AnimationGrid.tsx
│   │   │   ├── AnimationCard.tsx
│   │   │   ├── AnimationEditor.tsx
│   │   │   └── ParameterControls.tsx
│   │   ├── colors/      # Color pickers
│   │   │   ├── ColorPicker.tsx
│   │   │   ├── HuePicker.tsx
│   │   │   ├── RGBPicker.tsx
│   │   │   └── PresetPalette.tsx
│   │   ├── system/      # System status, controls
│   │   │   ├── SystemStatus.tsx
│   │   │   ├── ConnectionIndicator.tsx
│   │   │   └── PerformanceMetrics.tsx
│   │   └── layout/      # Layout components
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── MainLayout.tsx
│   │
│   ├── pages/           # Route pages
│   │   ├── Dashboard.tsx
│   │   ├── ZoneControl.tsx
│   │   ├── AnimationBrowser.tsx
│   │   ├── Settings.tsx
│   │   └── NotFound.tsx
│   │
│   ├── hooks/           # Custom React hooks
│   │   ├── useDiuna.ts         # Main backend connection hook
│   │   ├── useWebSocket.ts     # WebSocket connection management
│   │   ├── useZones.ts         # Zone state & operations
│   │   ├── useAnimations.ts    # Animation state & operations
│   │   ├── useColors.ts        # Color utilities
│   │   └── useKeyboard.ts      # Keyboard shortcuts
│   │
│   ├── stores/          # Zustand stores
│   │   ├── zoneStore.ts
│   │   ├── animationStore.ts
│   │   ├── systemStore.ts
│   │   └── uiStore.ts
│   │
│   ├── services/        # API services
│   │   ├── api.ts              # Axios instance configuration
│   │   ├── websocket.ts        # WebSocket client
│   │   ├── zoneService.ts      # Zone API calls
│   │   ├── animationService.ts # Animation API calls
│   │   └── systemService.ts    # System API calls
│   │
│   ├── types/           # TypeScript type definitions
│   │   ├── zone.ts
│   │   ├── animation.ts
│   │   ├── color.ts
│   │   ├── api.ts
│   │   └── websocket.ts
│   │
│   ├── utils/           # Utility functions
│   │   ├── colorConvert.ts     # Color space conversions
│   │   ├── formatters.ts       # Display formatters
│   │   └── validators.ts       # Input validation
│   │
│   ├── config/          # Configuration
│   │   └── constants.ts        # API URLs, app constants
│   │
│   └── styles/          # Global styles
│       ├── index.css           # Tailwind directives + global styles
│       └── animations.css      # Reusable animations
│
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
└── README.md
```

---

## 🎨 Design System

### Typography

**Font Families:**
- **Display/Headers:** Choose something distinctive (NOT Inter, NOT Roboto)
  - Options: Space Grotesk, Instrument Sans, Satoshi, Clash Display, Cabinet Grotesk
  - For tech aesthetic: JetBrains Mono, Fira Code, IBM Plex Mono
- **Body Text:** Legible, clean
  - Options: Inter (yes, it's common but readable), Public Sans, DM Sans
  - For uniqueness: Archivo, Plus Jakarta Sans, Manrope

**Scale:**
```css
/* Tailwind custom config */
fontSize: {
  'xs': '0.75rem',     // 12px
  'sm': '0.875rem',    // 14px
  'base': '1rem',      // 16px
  'lg': '1.125rem',    // 18px
  'xl': '1.25rem',     // 20px
  '2xl': '1.5rem',     // 24px
  '3xl': '1.875rem',   // 30px
  '4xl': '2.25rem',    // 36px
  '5xl': '3rem',       // 48px
}
```

### Colors

**Aesthetic Direction:** Modern, tech-forward, slightly futuristic but not cyberpunk circus

**Palette Options:**

**Option 1: Dark Theme (Recommended)**
```javascript
colors: {
  // Background layers
  bg: {
    primary: '#0A0A0A',      // Almost black
    secondary: '#141414',    // Slightly lighter
    tertiary: '#1E1E1E',     // Cards, panels
  },
  // Text
  text: {
    primary: '#FFFFFF',      // White
    secondary: '#A1A1A1',    // Gray
    tertiary: '#6B6B6B',     // Darker gray
  },
  // Accent (choose ONE dominant color)
  accent: {
    primary: '#00E5FF',      // Cyan (LED glow feeling)
    hover: '#00B8D4',
    active: '#00ACC1',
  },
  // Status colors
  success: '#00E676',        // Green
  warning: '#FFD600',        // Yellow
  error: '#FF1744',          // Red
  info: '#2979FF',           // Blue
}
```

**Option 2: Light Theme (Alternative)**
```javascript
colors: {
  bg: {
    primary: '#FAFAFA',
    secondary: '#F5F5F5',
    tertiary: '#EEEEEE',
  },
  text: {
    primary: '#0A0A0A',
    secondary: '#424242',
    tertiary: '#757575',
  },
  accent: {
    primary: '#0066CC',      // Electric blue
    hover: '#0052A3',
    active: '#004080',
  },
}
```

### Spacing Scale

```javascript
spacing: {
  '0': '0',
  '1': '0.25rem',    // 4px
  '2': '0.5rem',     // 8px
  '3': '0.75rem',    // 12px
  '4': '1rem',       // 16px
  '6': '1.5rem',     // 24px
  '8': '2rem',       // 32px
  '12': '3rem',      // 48px
  '16': '4rem',      // 64px
  '24': '6rem',      // 96px
}
```

### Border Radius

```javascript
borderRadius: {
  'none': '0',
  'sm': '0.25rem',   // 4px
  'md': '0.5rem',    // 8px (default for cards)
  'lg': '0.75rem',   // 12px
  'xl': '1rem',      // 16px
  'full': '9999px',  // Pills, circles
}
```

### Shadows

```javascript
boxShadow: {
  'sm': '0 1px 2px rgba(0, 0, 0, 0.05)',
  'DEFAULT': '0 4px 6px rgba(0, 0, 0, 0.1)',
  'md': '0 6px 12px rgba(0, 0, 0, 0.15)',
  'lg': '0 10px 25px rgba(0, 0, 0, 0.2)',
  'glow': '0 0 20px rgba(0, 229, 255, 0.5)',  // LED glow effect
}
```

---

## 🔌 Backend Communication

### WebSocket Connection

**Purpose:** Real-time bidirectional communication for live preview and state sync

**Connection:**
```typescript
// services/websocket.ts
import { io, Socket } from 'socket.io-client';

const WEBSOCKET_URL = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000';

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect() {
    this.socket = io(WEBSOCKET_URL, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: this.maxReconnectAttempts,
    });

    this.setupListeners();
  }

  private setupListeners() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
    });

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });
  }

  // Zone state updates (Server → Client)
  onZoneStateChanged(callback: (data: ZoneStateUpdate) => void) {
    this.socket?.on('zone:state_changed', callback);
  }

  // Animation events (Server → Client)
  onAnimationStarted(callback: (data: AnimationEvent) => void) {
    this.socket?.on('animation:started', callback);
  }

  onAnimationStopped(callback: (data: AnimationEvent) => void) {
    this.socket?.on('animation:stopped', callback);
  }

  // Frame updates for live preview (Server → Client, 60 FPS)
  onFrameUpdate(callback: (data: FrameData) => void) {
    this.socket?.on('frame:update', callback);
  }

  // Send commands (Client → Server)
  setZoneColor(zoneId: string, color: Color) {
    this.socket?.emit('zone:set_color', { zone_id: zoneId, color });
  }

  setZoneBrightness(zoneId: string, brightness: number) {
    this.socket?.emit('zone:set_brightness', { zone_id: zoneId, brightness });
  }

  startAnimation(animationId: string, params?: Record<string, any>) {
    this.socket?.emit('animation:start', { animation_id: animationId, params });
  }

  stopAnimation(animationId: string) {
    this.socket?.emit('animation:stop', { animation_id: animationId });
  }

  disconnect() {
    this.socket?.disconnect();
    this.socket = null;
  }
}

export const websocketService = new WebSocketService();
```

### REST API

**Purpose:** CRUD operations, configuration, preset management

**Configuration:**
```typescript
// services/api.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor (for auth tokens, etc.)
api.interceptors.request.use(
  (config) => {
    // Add auth token if exists
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor (for error handling)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

**API Services:**
```typescript
// services/zoneService.ts
import { api } from './api';
import type { Zone, ZoneUpdateRequest } from '@/types/zone';

export const zoneService = {
  // Get all zones
  getAll: async (): Promise<Zone[]> => {
    const response = await api.get('/api/zones');
    return response.data;
  },

  // Get single zone
  getById: async (zoneId: string): Promise<Zone> => {
    const response = await api.get(`/api/zones/${zoneId}`);
    return response.data;
  },

  // Update zone color
  updateColor: async (zoneId: string, color: Color): Promise<void> => {
    await api.put(`/api/zones/${zoneId}/color`, { color });
  },

  // Update zone brightness
  updateBrightness: async (zoneId: string, brightness: number): Promise<void> => {
    await api.put(`/api/zones/${zoneId}/brightness`, { brightness });
  },

  // Toggle zone on/off
  toggle: async (zoneId: string): Promise<void> => {
    await api.post(`/api/zones/${zoneId}/toggle`);
  },
};
```

---

## 🎣 Custom Hooks

### useWebSocket Hook

```typescript
// hooks/useWebSocket.ts
import { useEffect } from 'react';
import { websocketService } from '@/services/websocket';
import { useZoneStore } from '@/stores/zoneStore';
import { useAnimationStore } from '@/stores/animationStore';
import { useSystemStore } from '@/stores/systemStore';

export function useWebSocket() {
  const updateZone = useZoneStore((state) => state.updateZone);
  const updateAnimation = useAnimationStore((state) => state.updateAnimation);
  const setConnectionStatus = useSystemStore((state) => state.setConnectionStatus);

  useEffect(() => {
    // Connect
    websocketService.connect();
    setConnectionStatus('connected');

    // Subscribe to zone updates
    websocketService.onZoneStateChanged((data) => {
      updateZone(data.zone_id, data.state);
    });

    // Subscribe to animation events
    websocketService.onAnimationStarted((data) => {
      updateAnimation(data.animation_id, { running: true });
    });

    websocketService.onAnimationStopped((data) => {
      updateAnimation(data.animation_id, { running: false });
    });

    // Cleanup on unmount
    return () => {
      websocketService.disconnect();
      setConnectionStatus('disconnected');
    };
  }, [updateZone, updateAnimation, setConnectionStatus]);

  return {
    connected: true, // Could derive from store
    sendCommand: websocketService,
  };
}
```

### useZones Hook (with React Query)

```typescript
// hooks/useZones.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { zoneService } from '@/services/zoneService';
import type { Zone, Color } from '@/types/zone';

export function useZones() {
  return useQuery({
    queryKey: ['zones'],
    queryFn: zoneService.getAll,
    staleTime: 5000, // Consider data fresh for 5 seconds
    refetchInterval: 10000, // Fallback polling (WebSocket is primary)
  });
}

export function useZone(zoneId: string) {
  return useQuery({
    queryKey: ['zones', zoneId],
    queryFn: () => zoneService.getById(zoneId),
  });
}

export function useUpdateZoneColor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ zoneId, color }: { zoneId: string; color: Color }) =>
      zoneService.updateColor(zoneId, color),
    
    // Optimistic update
    onMutate: async ({ zoneId, color }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['zones'] });

      // Snapshot previous value
      const previousZones = queryClient.getQueryData<Zone[]>(['zones']);

      // Optimistically update
      queryClient.setQueryData<Zone[]>(['zones'], (old) =>
        old?.map((zone) =>
          zone.id === zoneId ? { ...zone, state: { ...zone.state, color } } : zone
        )
      );

      return { previousZones };
    },

    // Rollback on error
    onError: (err, variables, context) => {
      if (context?.previousZones) {
        queryClient.setQueryData(['zones'], context.previousZones);
      }
    },

    // Refetch on success
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
}
```

---

## 🎨 Key Components

### LEDCanvas (Main Visualization)

```typescript
// components/canvas/LEDCanvas.tsx
import { Stage, Layer } from 'react-konva';
import { ZoneVisualization } from './ZoneVisualization';
import { useZones } from '@/hooks/useZones';
import { useWebSocket } from '@/hooks/useWebSocket';

interface LEDCanvasProps {
  width: number;
  height: number;
}

export function LEDCanvas({ width, height }: LEDCanvasProps) {
  const { data: zones, isLoading } = useZones();
  const { connected } = useWebSocket();

  if (isLoading) {
    return <div>Loading canvas...</div>;
  }

  return (
    <div className="relative">
      {/* Connection indicator */}
      {!connected && (
        <div className="absolute top-4 right-4 px-3 py-1 bg-red-500 text-white rounded">
          Disconnected
        </div>
      )}

      {/* Konva Stage */}
      <Stage width={width} height={height}>
        <Layer>
          {zones?.map((zone) => (
            <ZoneVisualization key={zone.id} zone={zone} />
          ))}
        </Layer>
      </Stage>
    </div>
  );
}
```

### ZoneVisualization (Individual Zone Rendering)

```typescript
// components/canvas/ZoneVisualization.tsx
import { Group, Rect } from 'react-konva';
import type { Zone } from '@/types/zone';
import { colorToRGB } from '@/utils/colorConvert';

interface ZoneVisualizationProps {
  zone: Zone;
}

export function ZoneVisualization({ zone }: ZoneVisualizationProps) {
  const { r, g, b } = colorToRGB(zone.state.color);
  const alpha = zone.state.brightness / 255;

  // Simple horizontal strip (customize based on zone layout)
  const pixelWidth = 10;
  const pixelHeight = 20;
  const gap = 2;

  return (
    <Group x={zone.layout?.x || 0} y={zone.layout?.y || 0}>
      {Array.from({ length: zone.pixel_count }).map((_, index) => (
        <Rect
          key={index}
          x={index * (pixelWidth + gap)}
          y={0}
          width={pixelWidth}
          height={pixelHeight}
          fill={`rgba(${r}, ${g}, ${b}, ${alpha})`}
          cornerRadius={2}
          shadowColor="rgba(0, 0, 0, 0.5)"
          shadowBlur={5}
          shadowOffset={{ x: 0, y: 2 }}
        />
      ))}
    </Group>
  );
}
```

### ColorPicker Component

```typescript
// components/colors/ColorPicker.tsx
import { useState } from 'react';
import { HexColorPicker } from 'react-colorful';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { HuePicker } from './HuePicker';
import { RGBPicker } from './RGBPicker';
import type { Color } from '@/types/color';

interface ColorPickerProps {
  color: Color;
  onChange: (color: Color) => void;
}

export function ColorPicker({ color, onChange }: ColorPickerProps) {
  const [mode, setMode] = useState<'rgb' | 'hue' | 'preset'>(color.mode);

  return (
    <div className="w-full">
      <Tabs value={mode} onValueChange={(v) => setMode(v as any)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="rgb">RGB</TabsTrigger>
          <TabsTrigger value="hue">Hue</TabsTrigger>
          <TabsTrigger value="preset">Presets</TabsTrigger>
        </TabsList>

        <TabsContent value="rgb" className="mt-4">
          <RGBPicker color={color} onChange={onChange} />
        </TabsContent>

        <TabsContent value="hue" className="mt-4">
          <HuePicker color={color} onChange={onChange} />
        </TabsContent>

        <TabsContent value="preset" className="mt-4">
          {/* Preset palette grid */}
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

---

## 🎯 MVP Feature Checklist

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Project setup (Vite + React + TypeScript)
- [ ] Design system (Tailwind config, colors, typography)
- [ ] Component library setup (Shadcn/ui)
- [ ] Routing setup (React Router)
- [ ] WebSocket connection (Socket.IO client)
- [ ] REST API client (Axios)
- [ ] Basic stores (Zustand)

### Phase 2: Zone Control (Week 3-4)
- [ ] LEDCanvas with Konva
- [ ] ZoneVisualization (live preview)
- [ ] ZoneList sidebar
- [ ] ZoneCard with controls
- [ ] ColorPicker (RGB, Hue modes)
- [ ] Brightness slider
- [ ] Real-time updates via WebSocket

### Phase 3: System Features (Week 5-6)
- [ ] System status display (FPS, connection, metrics)
- [ ] Animation browser (grid view)
- [ ] Animation control (start/stop/params)
- [ ] Settings page (config, preferences)
- [ ] Error handling & notifications
- [ ] Loading states & skeletons

### Phase 4: Polish & Testing (Week 7-8)
- [ ] Animations & transitions (Framer Motion)
- [ ] Keyboard shortcuts
- [ ] Responsive design (mobile, tablet)
- [ ] Dark/light theme toggle
- [ ] Unit tests (Vitest)
- [ ] E2E tests (Playwright)
- [ ] Documentation
- [ ] Performance optimization

---

## ⚡ Performance Considerations

### Canvas Rendering
- **60 FPS target** for live preview
- Use `shouldComponentUpdate` or `React.memo` for zone visualizations
- Throttle WebSocket frame updates if needed
- Consider using Web Workers for heavy color calculations

### Bundle Size
- Code-split routes with `React.lazy()`
- Tree-shake unused Shadcn/ui components
- Optimize images/assets
- Use dynamic imports for large dependencies

### Network
- Compress WebSocket messages (consider MessagePack)
- Batch API calls where possible
- Use service workers for offline support (future)

---

## 🎨 UI/UX Guidelines

### Feedback & Responsiveness
- **Instant feedback** - show optimistic updates immediately
- **Loading states** - always show progress (spinners, skeletons)
- **Error states** - clear error messages with recovery actions
- **Empty states** - guide user on what to do next

### Accessibility
- **Keyboard navigation** - tab order, focus states
- **Screen reader support** - ARIA labels, semantic HTML
- **Color contrast** - WCAG AA minimum (4.5:1 for text)
- **Focus indicators** - visible keyboard focus

### Mobile Considerations
- **Touch targets** - minimum 44x44px
- **Gestures** - swipe, pinch-to-zoom on canvas
- **Bottom navigation** - easier thumb reach
- **Simplified layouts** - stack vertically on mobile

---

## 🐛 Error Handling

### WebSocket Disconnection
```typescript
// Show reconnecting indicator
// Retry connection with exponential backoff
// Cache unsaved changes locally
// Auto-apply cached changes when reconnected
```

### API Errors
```typescript
// Display toast notification
// Log error for debugging
// Rollback optimistic updates
// Provide retry action
```

### Validation Errors
```typescript
// Inline form validation
// Clear error messages
// Highlight invalid fields
// Prevent submission until valid
```

---

## 📝 Code Style Guidelines

### TypeScript
- **Strict mode enabled** - no implicit any
- **Explicit return types** for functions
- **Interface over type** for objects (consistency)
- **Use enums** for string unions with many values

### React
- **Functional components** with hooks
- **Named exports** for components (easier to search)
- **Props interfaces** defined above component
- **Extract custom hooks** for reusable logic

### CSS/Tailwind
- **Utility classes** over custom CSS
- **Component classes** for repeated patterns
- **CSS variables** for theme values
- **No inline styles** (except for dynamic values)

### File Naming
- **Components:** PascalCase (e.g., `ZoneCard.tsx`)
- **Hooks:** camelCase with `use` prefix (e.g., `useZones.ts`)
- **Utilities:** camelCase (e.g., `colorConvert.ts`)
- **Types:** PascalCase (e.g., `Zone`, `Animation`)

---

## 🚀 Deployment

### Environment Variables
```bash
# .env.development
VITE_API_URL=http://localhost:8000
VITE_WEBSOCKET_URL=ws://localhost:8000

# .env.production
VITE_API_URL=https://api.diuna.io
VITE_WEBSOCKET_URL=wss://api.diuna.io
```

### Build
```bash
npm run build
# Output: dist/ folder (static files)
```

### Serve Static Files (via Backend)
```python
# FastAPI can serve frontend
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")
```

---

## 🎯 Success Criteria

**MVP is done when:**
- ✅ User can see live LED preview on canvas
- ✅ User can control zone colors and brightness
- ✅ Changes reflect on physical LEDs within 50ms
- ✅ App works on desktop (Chrome, Firefox, Safari)
- ✅ No console errors or warnings
- ✅ Responsive on mobile (basic functionality)
- ✅ Clean, professional UI (not "AI slop")

---

## 📚 Resources

### Documentation
- [React Docs](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Shadcn/ui](https://ui.shadcn.com)
- [Konva.js](https://konvajs.org/docs/)
- [Socket.IO Client](https://socket.io/docs/v4/client-api/)
- [TanStack Query](https://tanstack.com/query/latest/docs/react/overview)

### Learning
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Zustand Examples](https://github.com/pmndrs/zustand#readme)
- [Framer Motion Examples](https://www.framer.com/motion/examples/)

---

**Questions? Ask the backend team about:**
- WebSocket message formats
- API endpoint specifications
- Color format details (RGB vs HSV vs Hue)
- Zone layout coordinate system
- Animation parameter structures
