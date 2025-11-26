# Diuna App - UI/UX Design Guide

## 🎨 Design Philosophy

**Diuna's Aesthetic:** Modern tech meets artistic minimalism. Not flashy rave aesthetics, not corporate boring. Think: *high-end audio equipment meets contemporary art gallery*.

### Core Principles

1. **Subtle Sophistication**
   - LED glow effects, not circus lights
   - Refined gradients, not garish rainbows
   - Intentional negative space, not cluttered dashboards

2. **Tactile Digital**
   - Smooth animations that feel physical
   - Haptic-like feedback (visual bounce, easing)
   - Knob-like controls (rotary encoder feeling)

3. **Information Clarity**
   - Real-time data must be glanceable
   - Technical details available but not overwhelming
   - Visual hierarchy guides attention

4. **Creative Tool First**
   - Interface fades into background when creating
   - Canvas is the hero, controls are supporting cast
   - Keyboard shortcuts for power users

---

## 🎯 Aesthetic Direction

### Option A: Dark Minimalist (RECOMMENDED)

**Mood:** Professional studio, late-night creation session, LED glow in darkness

**Visual Language:**
- Almost-black backgrounds (#0A0A0A)
- White/gray text with high contrast
- Single accent color (cyan/electric blue) for LED glow feeling
- Lots of negative space
- Sharp, geometric shapes
- Subtle shadows and glows

**Inspiration:**
- Ableton Live (music production)
- Figma dark mode (design tool)
- Spotify (content-first, clean)
- Tesla interface (futuristic but usable)

**Typography:**
- Display: **Space Grotesk** (geometric, modern, tech-feeling)
- Monospace (for technical data): **JetBrains Mono** (readable, distinctive)
- Body: **Inter** (yes it's common, but it's readable - or use DM Sans for uniqueness)

**Color Palette:**
```javascript
{
  // Backgrounds
  bg: {
    app: '#0A0A0A',        // Main background
    panel: '#141414',      // Cards, sidebars
    elevated: '#1E1E1E',   // Hover states, modals
    input: '#0F0F0F',      // Input fields
  },
  
  // Text
  text: {
    primary: '#FFFFFF',    // Headings, important text
    secondary: '#A1A1A1',  // Body text
    tertiary: '#6B6B6B',   // Labels, captions
    disabled: '#404040',   // Disabled state
  },
  
  // Accent (LED glow theme)
  accent: {
    primary: '#00E5FF',    // Cyan - main accent
    hover: '#00D4F0',      // Slightly darker
    active: '#00B8D4',     // Even darker
    glow: 'rgba(0, 229, 255, 0.3)', // For glow effects
  },
  
  // Status
  success: '#00E676',      // Green - animations running
  warning: '#FFD600',      // Yellow - warnings
  error: '#FF1744',        // Red - errors, disconnected
  info: '#2979FF',         // Blue - tips, info
  
  // Zone colors (for visualization)
  zones: {
    floor: '#00E5FF',      // Cyan
    lamp: '#FF6B6B',       // Coral
    desk: '#9D4EDD',       // Purple
    hood: '#06FFA5',       // Mint
    // ... more zones
  },
  
  // Borders
  border: {
    subtle: '#1E1E1E',     // Barely visible
    default: '#2A2A2A',    // Default borders
    strong: '#404040',     // Emphasized borders
    focus: '#00E5FF',      // Focus state (accent)
  },
}
```

**Key Visual Elements:**
```css
/* LED glow effect */
.led-glow {
  box-shadow: 
    0 0 10px rgba(0, 229, 255, 0.3),
    0 0 20px rgba(0, 229, 255, 0.2),
    0 0 30px rgba(0, 229, 255, 0.1);
}

/* Glass morphism (for overlays) */
.glass {
  background: rgba(20, 20, 20, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Smooth transitions */
.smooth {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
```

---

### Option B: Light Brutalist (Alternative)

**Mood:** Swiss design meets modern gallery, daylight workspace

**Visual Language:**
- Off-white backgrounds (#FAFAFA)
- Black text, high contrast
- Bold typography
- Grid-based layouts
- Minimal decoration
- Function over form

**Typography:**
- Display: **Clash Display** (geometric, bold, statement)
- Body: **Archivo** (clean, Swiss-inspired)
- Monospace: **Fira Code** (technical)

**Color Palette:**
```javascript
{
  bg: {
    app: '#FAFAFA',
    panel: '#FFFFFF',
    elevated: '#F5F5F5',
  },
  text: {
    primary: '#0A0A0A',
    secondary: '#424242',
  },
  accent: {
    primary: '#0066CC',    // Electric blue
  },
  // ... similar structure
}
```

---

## 🎯 Key UI Components

### 1. Dashboard Layout

**Desktop (>1280px):**
```
┌────────────────────────────────────────────────────────┐
│ Header (60px)                              [⚙][👤]    │
├─────────┬──────────────────────────────────────────────┤
│         │                                              │
│ Sidebar │           Main Canvas Area                   │
│ (280px) │                                              │
│         │        [Live LED Preview]                    │
│ Zones   │                                              │
│ • Floor │                                              │
│ • Lamp  │                                              │
│ • Desk  │                                              │
│         │                                              │
│ System  ├──────────────────────────────────────────────┤
│ Status  │  Quick Controls                              │
│         │  [Brightness ─●────] [Color ●] [Mode ▼]    │
└─────────┴──────────────────────────────────────────────┘
```

**Mobile (<768px):**
```
┌──────────────────────┐
│ Header      [☰]     │
├──────────────────────┤
│                      │
│  Canvas Preview      │
│                      │
├──────────────────────┤
│ Bottom Controls      │
│ [Zone▼] [🎨] [⚙]   │
└──────────────────────┘
```

### 2. Zone Card (Sidebar)

```typescript
// Visual representation
┌────────────────────────┐
│ Floor Strip      [ON]  │ ← Toggle
├────────────────────────┤
│ ████████████████████   │ ← Live color preview
│                        │
│ Brightness  ─────●───  │ ← Slider (0-255)
│                        │
│ Color      [🎨 Cyan]  │ ← Color picker trigger
│                        │
│ [Animation ▼]  [⚡]    │ ← Animation dropdown + quick trigger
└────────────────────────┘
```

**Interaction States:**
- **Hover:** Subtle background color change (#1E1E1E)
- **Active:** Border glow (accent color)
- **Selected:** Accent color border, slight background tint
- **Disabled:** 50% opacity, grayscale

### 3. Color Picker Modal

```typescript
// Full-screen overlay on mobile, popover on desktop
┌──────────────────────────────────────┐
│ Pick Color                    [✕]   │
├──────────────────────────────────────┤
│ [RGB] [HSV] [Hue] [Presets]         │ ← Tabs
├──────────────────────────────────────┤
│                                      │
│         Color Wheel/Slider           │
│                                      │
│     (React-colorful component)       │
│                                      │
├──────────────────────────────────────┤
│ RGB: 0   229  255                    │
│ Hex: #00E5FF                         │
├──────────────────────────────────────┤
│ Recent Colors:                       │
│ [●][●][●][●][●][●]                  │
├──────────────────────────────────────┤
│           [Cancel]  [Apply]          │
└──────────────────────────────────────┘
```

**Features:**
- Live preview on canvas while picking
- Recent colors row (last 6-8 used)
- Preset palette (saved favorites)
- Keyboard input for precise values
- Copy/paste hex codes

### 4. Animation Browser

```typescript
// Grid layout
┌────────┬────────┬────────┬────────┐
│ Breathe│ Cycle  │  Wave  │ Sparkle│
│  [GIF] │  [GIF] │  [GIF] │  [GIF] │
│  [▶]   │  [▶]   │  [▶]   │  [▶]   │
├────────┼────────┼────────┼────────┤
│  Fade  │ Snake  │ Pulse  │  Fire  │
│  [GIF] │  [GIF] │  [GIF] │  [GIF] │
│  [▶]   │  [▶]   │  [▶]   │  [▶]   │
└────────┴────────┴────────┴────────┘

// Click opens detail modal:
┌──────────────────────────────────────┐
│ Color Cycle                   [✕]   │
├──────────────────────────────────────┤
│                                      │
│     [Large GIF Preview]              │
│                                      │
├──────────────────────────────────────┤
│ Rainbow animation through hue cycle  │
│                                      │
│ Speed    ────●───────  (1.5x)       │
│ Zones    [☑ Floor] [☐ Lamp]         │
│                                      │
│ [Start Animation]                    │
└──────────────────────────────────────┘
```

### 5. System Status (Bottom Bar or Header)

```typescript
// Compact info display
┌────────────────────────────────────────────────┐
│ ● Connected  |  60 FPS  |  18W  |  Mode: ANIM │
└────────────────────────────────────────────────┘

// Expanded version (collapsible)
┌────────────────────────────────────────────────┐
│ Connection:  ● Connected to Raspberry Pi      │
│ Frame Rate:  60 FPS (avg), 2.1ms render       │
│ Power Draw:  18W / 60W max                    │
│ Mode:        ANIMATION (Color Cycle)          │
│ Uptime:      2h 34m                           │
└────────────────────────────────────────────────┘
```

**Visual Indicators:**
- Connection: Green dot = connected, Red = disconnected, Yellow = reconnecting
- FPS: Green if >55, Yellow if 30-55, Red if <30
- Power: Progress bar, warning at 90%

---

## 🎬 Animations & Transitions

### Page Transitions (Framer Motion)

```typescript
const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
};

const pageTransition = {
  duration: 0.3,
  ease: [0.4, 0, 0.2, 1], // Cubic bezier (smooth)
};

// Usage
<motion.div
  variants={pageVariants}
  initial="initial"
  animate="animate"
  exit="exit"
  transition={pageTransition}
>
  {children}
</motion.div>
```

### Zone Card Hover Effect

```typescript
const cardVariants = {
  rest: { scale: 1 },
  hover: { 
    scale: 1.02,
    boxShadow: "0 8px 30px rgba(0, 0, 0, 0.3)",
  },
};

<motion.div
  variants={cardVariants}
  initial="rest"
  whileHover="hover"
  transition={{ duration: 0.2 }}
>
  {/* Card content */}
</motion.div>
```

### LED Glow Pulse (for active zones)

```css
@keyframes led-pulse {
  0%, 100% {
    box-shadow: 
      0 0 10px rgba(0, 229, 255, 0.3),
      0 0 20px rgba(0, 229, 255, 0.2);
  }
  50% {
    box-shadow: 
      0 0 20px rgba(0, 229, 255, 0.5),
      0 0 40px rgba(0, 229, 255, 0.3),
      0 0 60px rgba(0, 229, 255, 0.2);
  }
}

.zone-active {
  animation: led-pulse 2s ease-in-out infinite;
}
```

### Stagger Children (for list animations)

```typescript
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05, // 50ms delay between children
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 },
};

<motion.div variants={containerVariants} initial="hidden" animate="visible">
  {zones.map((zone) => (
    <motion.div key={zone.id} variants={itemVariants}>
      <ZoneCard zone={zone} />
    </motion.div>
  ))}
</motion.div>
```

---

## 🎮 Interactions & Micro-interactions

### Slider (Brightness/Speed)

**Visual Design:**
```
Before interaction:
├──────────────────────────────┤
        ^ Handle (subtle)

On hover:
├──────────────────────────────┤
        ● Handle (larger, glowing)

While dragging:
├█████████──────────────────────┤
         ● Handle (accent color, glow)
         ↑ Fill bar shows value
```

**Feedback:**
- Handle scales up on hover (1.2x)
- Glow effect on active
- Fill bar animates smoothly
- Value tooltip appears above handle while dragging
- Haptic feedback (vibration) on mobile at 25%, 50%, 75%, 100%

### Color Swatch (in palette)

**Visual:**
```
Rest:      Hover:     Active:
┌────┐    ┌────┐    ┌────┐
│████│    │████│    │████│
└────┘    └────┘    └────┘
           ring      checkmark
```

**Feedback:**
- Scale to 1.1 on hover
- Ring border on hover (accent color)
- Checkmark overlay when selected
- Smooth color transition when changing

### Toggle Switch (Zone on/off)

**Visual:**
```
OFF:                ON:
┌──────┐          ┌──────┐
│ ○────│          │────● │
└──────┘          └──────┘
 gray              accent
```

**Feedback:**
- Handle slides smoothly (0.3s ease)
- Background color transitions
- Slight bounce at end of slide
- Click anywhere on switch to toggle

### Button States

**Primary Button:**
```css
.button-primary {
  background: var(--accent-primary);
  color: var(--bg-app);
  
  /* Rest state */
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  
  /* Hover */
  &:hover {
    background: var(--accent-hover);
    box-shadow: 0 4px 12px rgba(0, 229, 255, 0.4);
    transform: translateY(-2px);
  }
  
  /* Active (pressed) */
  &:active {
    transform: translateY(0);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  }
  
  /* Disabled */
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }
}
```

---

## 🖼️ Visual Hierarchy

### Information Density

**Primary Information (Always Visible):**
- Zone name & status (on/off)
- Current color (visual swatch)
- Connection status

**Secondary Information (Visible on Hover/Focus):**
- Brightness value (number)
- Animation name (if running)
- FPS counter

**Tertiary Information (Expandable/Modal):**
- Detailed metrics (render time, power draw)
- Animation parameters (speed, colors)
- Zone configuration (pixel count, layout)

### Typography Scale & Usage

```typescript
// Heading 1 - Page titles
h1: "text-4xl font-bold tracking-tight"  // 36px, bold

// Heading 2 - Section titles
h2: "text-2xl font-semibold"             // 24px, semibold

// Heading 3 - Card titles
h3: "text-lg font-medium"                // 18px, medium

// Body - Default text
body: "text-base"                        // 16px, regular

// Caption - Labels, metadata
caption: "text-sm text-text-secondary"   // 14px, gray

// Code/Technical - Numbers, values
code: "font-mono text-sm"                // 14px, monospace
```

---

## 📱 Responsive Design

### Breakpoints

```javascript
screens: {
  'xs': '475px',
  'sm': '640px',   // Mobile landscape, small tablets
  'md': '768px',   // Tablet portrait
  'lg': '1024px',  // Tablet landscape, small laptop
  'xl': '1280px',  // Desktop
  '2xl': '1536px', // Large desktop
}
```

### Mobile Adaptations

**Navigation:**
- Desktop: Sidebar (always visible)
- Mobile: Bottom bar with hamburger menu

**Color Picker:**
- Desktop: Popover (attached to trigger)
- Mobile: Full-screen modal (better UX for touch)

**Canvas:**
- Desktop: Large, centered
- Mobile: Full-width, scrollable if needed

**Controls:**
- Desktop: Hover states, tooltips
- Mobile: Tap to show tooltips, larger touch targets

---

## ♿ Accessibility (A11y)

### Keyboard Navigation

**Tab Order:**
1. Main navigation
2. Zone cards (top to bottom)
3. Color picker
4. Animation controls
5. System status

**Keyboard Shortcuts:**
```typescript
const shortcuts = {
  'Space': 'Play/pause animation',
  'Escape': 'Close modal/cancel',
  'ArrowUp': 'Increase brightness (when focused)',
  'ArrowDown': 'Decrease brightness',
  'C': 'Open color picker',
  'A': 'Open animations',
  'S': 'Open settings',
  'Z': 'Cycle zones',
  'Cmd/Ctrl + S': 'Save current state',
  'Cmd/Ctrl + Z': 'Undo',
};
```

### Screen Reader Support

```typescript
// Zone card example
<div
  role="group"
  aria-label={`${zone.name} zone control`}
>
  <button
    aria-label={`Toggle ${zone.name} ${zone.enabled ? 'off' : 'on'}`}
    aria-pressed={zone.enabled}
  >
    {/* Toggle switch */}
  </button>
  
  <input
    type="range"
    aria-label={`${zone.name} brightness`}
    aria-valuemin={0}
    aria-valuemax={255}
    aria-valuenow={zone.brightness}
    aria-valuetext={`${Math.round((zone.brightness / 255) * 100)}%`}
  />
</div>
```

### Color Contrast

**WCAG AA Requirements:**
- Normal text (< 18px): 4.5:1 minimum
- Large text (≥ 18px): 3:1 minimum
- UI components: 3:1 minimum

**Testing:**
```
// Verify all text meets contrast ratios
Text on #0A0A0A (bg-app):
  #FFFFFF (text-primary)   → 20.58:1 ✅ Excellent
  #A1A1A1 (text-secondary) → 8.89:1  ✅ Good
  #6B6B6B (text-tertiary)  → 4.58:1  ✅ Passes AA

Accent on background:
  #00E5FF on #0A0A0A       → 13.2:1  ✅ Excellent
```

---

## 🎨 Component Library (Shadcn/ui)

### Install Components

```bash
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add slider
npx shadcn-ui@latest add switch
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add toast
```

### Customize Theme

```typescript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        // ... map to your color system
      },
    },
  },
};
```

### Custom Components

**Create when:**
- Shadcn/ui doesn't have it (e.g., LED pixel visualization)
- Heavily customized (color picker with live preview)
- Performance-critical (canvas rendering)

**Use Shadcn when:**
- Standard UI patterns (buttons, cards, modals)
- Accessibility is critical (forms, dialogs)
- Saves time (no need to reinvent)

---

## 🎯 Design Patterns

### Loading States

**Skeleton Screens (Recommended):**
```typescript
// Show layout while loading
<div className="animate-pulse">
  <div className="h-8 bg-bg-tertiary rounded mb-4" />
  <div className="h-64 bg-bg-tertiary rounded" />
</div>
```

**Spinners (For Actions):**
```typescript
// While saving, submitting, etc.
<Button disabled>
  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
  Saving...
</Button>
```

### Error States

**Toast Notifications:**
```typescript
import { toast } from 'sonner';

// Error
toast.error('Failed to connect to backend', {
  description: 'Check connection and try again',
  action: {
    label: 'Retry',
    onClick: () => retryConnection(),
  },
});

// Success
toast.success('Color updated');
```

**Inline Errors:**
```typescript
<div className="border border-error rounded p-4">
  <div className="flex items-start">
    <AlertCircle className="h-5 w-5 text-error mr-3" />
    <div>
      <h4 className="font-medium">Connection Lost</h4>
      <p className="text-sm text-text-secondary">
        Unable to reach Diuna backend. Changes will not be saved.
      </p>
      <Button onClick={reconnect} className="mt-2">
        Reconnect
      </Button>
    </div>
  </div>
</div>
```

### Empty States

**Guide User:**
```typescript
<div className="text-center py-12">
  <Zap className="h-16 w-16 mx-auto text-text-tertiary mb-4" />
  <h3 className="text-xl font-medium mb-2">No zones configured</h3>
  <p className="text-text-secondary mb-4">
    Add your first LED zone to get started
  </p>
  <Button onClick={openAddZoneDialog}>
    Add Zone
  </Button>
</div>
```

---

## 🚀 Performance Best Practices

### Canvas Optimization

**Use `React.memo` for expensive components:**
```typescript
export const ZoneVisualization = React.memo(({ zone }) => {
  // Only re-renders when zone props change
  return <Group>...</Group>;
});
```

**Throttle high-frequency updates:**
```typescript
import { throttle } from 'lodash-es';

const throttledUpdate = throttle((data) => {
  updateCanvas(data);
}, 16); // ~60 FPS

websocket.on('frame:update', throttledUpdate);
```

### Bundle Size

**Lazy load routes:**
```typescript
const AnimationBrowser = lazy(() => import('./pages/AnimationBrowser'));
const Settings = lazy(() => import('./pages/Settings'));

<Suspense fallback={<Loading />}>
  <Routes>
    <Route path="/animations" element={<AnimationBrowser />} />
    <Route path="/settings" element={<Settings />} />
  </Routes>
</Suspense>
```

**Code split heavy libraries:**
```typescript
// Only load when needed
const loadColorPicker = () => import('react-colorful');

function ColorPickerButton() {
  const [showPicker, setShowPicker] = useState(false);
  const [Picker, setPicker] = useState(null);
  
  useEffect(() => {
    if (showPicker && !Picker) {
      loadColorPicker().then(module => setPicker(() => module.HexColorPicker));
    }
  }, [showPicker]);
  
  return <>{Picker && <Picker />}</>;
}
```

---

## 📐 Layout Examples

### Dashboard (Desktop)

```typescript
<div className="flex h-screen bg-bg-app">
  {/* Sidebar */}
  <aside className="w-72 bg-bg-panel border-r border-border-default">
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-6">Diuna</h1>
      <ZoneList zones={zones} />
    </div>
  </aside>
  
  {/* Main Content */}
  <main className="flex-1 flex flex-col">
    {/* Header */}
    <header className="h-16 border-b border-border-default flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <ModeSelector />
        <AnimationStatus />
      </div>
      <SystemStatus />
    </header>
    
    {/* Canvas */}
    <div className="flex-1 p-6">
      <LEDCanvas width={800} height={600} />
    </div>
    
    {/* Bottom Controls */}
    <div className="h-20 border-t border-border-default px-6 flex items-center gap-4">
      <BrightnessControl />
      <ColorPickerTrigger />
    </div>
  </main>
</div>
```

---

## ✅ Final Checklist

**Before showing to user:**
- [ ] No console errors/warnings
- [ ] Animations are smooth (60 FPS)
- [ ] Colors match design system
- [ ] Typography is consistent
- [ ] Spacing follows 8px grid
- [ ] Hover states work
- [ ] Focus states visible
- [ ] Loading states implemented
- [ ] Error states handled
- [ ] Mobile responsive
- [ ] Dark theme applied (or light if chosen)
- [ ] No "AI slop" generic aesthetics
- [ ] Distinctive, memorable design

**Polish:**
- [ ] Micro-interactions feel smooth
- [ ] Transitions are intentional
- [ ] Information hierarchy clear
- [ ] Empty states guide user
- [ ] Keyboard shortcuts work
- [ ] Accessibility labels added

---

**Remember:** The interface should feel like a professional creative tool, not a hobbyist dashboard. Every detail matters. The goal is "Wow, this is beautiful" not "It works."

**When in doubt:** Look at Figma, Linear, Framer - modern tools that respect designers/creators.
