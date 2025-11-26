---
Last Updated: 2025-11-26
Updated By: @agent-uiux-designer
Changes: Initial dashboard layout design for power-user workflow
---

# Diuna App - Dashboard Layout Architecture

## 🎯 Overview

The dashboard is designed for **power-user complexity** with many controls and information displays. The layout adapts the "content-first" principle (canvas is hero) while providing comprehensive control access without overwhelming the interface.

**Design Philosophy**: Professional studio workspace with layered information density. Similar to Ableton Live, Figma, or DaVinci Resolve - tools that balance deep functionality with visual clarity.

---

## 📐 Master Layout Structure

### Desktop (≥1280px) - PRIMARY TARGET

```
┌─────────────────────────────────────────────────────────────────────┐
│                         [Global Header]                             │
│ Logo | Project Name | Mode Selector | System Status | Settings      │
├──────────────┬─────────────────────────────────┬──────────────────┤
│              │                                 │                  │
│   LEFT       │      MAIN CANVAS AREA           │    RIGHT PANEL   │
│   SIDEBAR    │  (LED Preview + Controls)       │   (Inspector)    │
│   (Zones)    │                                 │  (Details/Info)  │
│   (Quick     │                                 │                  │
│   Settings)  │                                 │                  │
│              │                                 │                  │
├──────────────┴─────────────────────────────────┴──────────────────┤
│               [Footer / System Status Bar]                          │
│ Connection • Frame Rate • Power Draw • Mode • Memory               │
└─────────────────────────────────────────────────────────────────────┘
```

**Dimensions**:
- **Left Sidebar**: 320px (fixed, collapsible to 80px for icon-only mode)
- **Main Canvas**: Flexible, remaining width
- **Right Inspector**: 360px (optional, toggleable)
- **Header**: 64px height
- **Footer**: 48px height

---

## 🗂️ Section Deep-Dive

### 1. Global Header (64px)

**Left Section (Navigation)**:
```
┌─────────────────────────────────────────────┐
│ [Diuna Logo] | [Modes: Live | Edit | Debug] │
└─────────────────────────────────────────────┘
```

- **Logo/Branding** (24×24px, left): Diuna wordmark + icon
- **Mode Selector** (3 buttons, horizontal):
  - **Live** - Real-time control (default)
  - **Edit** - Animation/preset editing (future)
  - **Debug** - Frame playback, performance monitoring
  - Active mode highlighted with accent color + underline

**Right Section (System)**:
```
┌───────────────────────────────────────────────────────────────────┐
│ ● Connected | 60 FPS | 18W | [Settings ⚙] | [Menu ≡]           │
└───────────────────────────────────────────────────────────────────┘
```

- **Status Indicator** (12px dot + text): Connection status, clickable to expand
- **Performance Metrics** (text-sm, monospace): FPS, power draw (collapsible)
- **Settings Icon** (32×32px): Opens settings modal
- **Menu Icon** (32×32px): Overflow menu (keyboard shortcuts, about, help)

**Spacing**: 16px padding, 8px gaps between elements

---

### 2. Left Sidebar (320px - Fixed or Collapsible)

**Sections (top to bottom)**:

#### A. Project Info (48px header)
```
┌──────────────────────────────┐
│ Project ▼                    │
│ "My LED Jacket"              │
│ Last saved 2 min ago         │
└──────────────────────────────┘
```
- Dropdown to switch projects
- Quick save status
- Auto-save indicator (subtle)

#### B. Zone Selector (Scrollable, 200-400px)

**Each Zone Card** (320px wide, ~96px each):
```
┌────────────────────────────┐
│ Floor Strip          [●]  │  ← Toggle (enabled/disabled)
├────────────────────────────┤
│ ███████████████████████    │  ← RGB color bar (16px height)
│                            │
│ Brightness: 78%            │  ← Label + value
│ ─────●──────────────────   │  ← Slider (16px track)
│                            │
│ [🎨] [⚡] [🌈] [⏱]      │  ← Quick action buttons (32px each)
└────────────────────────────┘
```

**Zone Card States**:
- **Default**: `bg-panel` with subtle border
- **Hover**: `bg-elevated`, shadow-md
- **Selected**: `border-accent-primary` with glow effect
- **Disabled**: opacity-50, grayscale

**Quick Action Buttons** (left to right):
1. **🎨 Color** - Open color picker
2. **⚡ Effect** - Quick animation select
3. **🌈 Palette** - Color palette selection
4. **⏱ Speed** - Animation speed (if active)

#### C. Zone Groups (Collapsible)

Allow grouping zones for batch control:
```
▼ Wearable Zones (3 zones)
  ├─ Jacket Front
  ├─ Jacket Back
  └─ Sleeve Accent
▶ Environmental (6 zones)  ← Collapsed, click to expand
```

#### D. Sidebar Footer (48px)

```
┌────────────────────────────┐
│ [+ New Zone] | [⚙ Config] │
└────────────────────────────┘
```

**Spacing**:
- Sidebar padding: 12px
- Between cards: 8px
- Internal card padding: 12px

---

### 3. Main Canvas Area (Flexible)

**Purpose**: Central stage for LED visualization and primary interaction

**Layout**:
```
┌────────────────────────────────────────────────┐
│                   [Tab Bar]                    │
│ [▶ Live Preview] | [🎨 Color Panel] | [⚙ Ex...]
├────────────────────────────────────────────────┤
│                                                │
│          [LED STRIP VISUALIZATION]             │ ← Large preview (400-600px height)
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │ [LED Render with animations]             │ │
│  │                                          │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  [Brightness Slider - Full Width]             │ ← Global brightness control
│  ─────●──────────────────────────── 100%     │
│                                                │
│  [Timeline / Playback Controls] (if Edit mode)│
│                                                │
└────────────────────────────────────────────────┘
```

**Tabs** (switchable panels):
1. **▶ Live Preview** - Real-time LED visualization (default)
2. **🎨 Color Panel** - Detailed color picker and palette
3. **⚙ Extended Controls** - Advanced settings (future)

**Main Preview Panel**:
- Minimum height: 300px (mobile) → 600px (desktop)
- Aspect ratio flexible
- Center content with subtle padding
- Dark background with subtle grid (optional)
- LED animation rendering with full visual fidelity

---

### 4. Right Inspector Panel (360px - Toggleable)

**Purpose**: Detailed information and property editing for selected zone

**Sections**:

#### A. Selected Zone Header (56px)
```
┌──────────────────────────────┐
│ Floor Strip              [×] │  ← Close button
├──────────────────────────────┤
```

#### B. Zone Properties (Expandable sections)

```
▼ Color & Brightness
  Current Color: #00E5FF (Cyan)
  [Color picker button]

  Brightness: [Slider] 78%
  Saturation: [Slider] 100%
  Opacity: [Slider] 100%

▼ Animation
  Status: Running
  Type: Breathe
  Speed: [Slider] 1.0x
  Duration: [Slider] 2.0s
  Loop: [Toggle] On

▼ Hardware Info
  GPIO: 18
  Pixel Range: 0-14
  Voltage: 12V
  Color Order: BGR
  Total Pixels: 15

▼ Sync & Save
  Last Modified: 2 min ago
  [Sync to Device] [Save Preset]
```

**Interaction**:
- Click section headers to expand/collapse
- Sliders inline with labels
- Action buttons at bottom of section
- Monospace font for technical values

#### C. Footer Actions (48px)
```
┌──────────────────────────────┐
│ [Reset] [Save as Preset] [Delete]
└──────────────────────────────┘
```

**Spacing**:
- Panel padding: 16px
- Section gaps: 12px
- Internal padding: 8px

---

## 📱 Tablet Adaptation (768px - 1279px)

Layout shifts to **vertical stacking**:

```
┌──────────────────────────────────┐
│         [Global Header]          │
├──────────────────────────────────┤
│       [Main Canvas - Full Width] │
│      (LED Preview dominates)     │
├──────────────────────────────────┤
│  [Left Sidebar] | [Right Panel]  │
│  (Side by side, narrower)        │
├──────────────────────────────────┤
│      [Footer / Status Bar]       │
└──────────────────────────────────┘
```

**Changes**:
- Sidebar: 280px → 240px
- Inspector: 360px → 300px
- Canvas: Full width between sidebar/inspector
- Scrollable zones list instead of fixed height
- Single-column layout for mobile

---

## 📱 Mobile Adaptation (<768px)

Complete redesign for touch:

```
┌──────────────────────────────┐
│   [Header - Compact]         │
├──────────────────────────────┤
│   [Main Canvas - Full Width] │
│   (LED preview, full screen) │
├──────────────────────────────┤
│  [Bottom Tab Navigation]     │
│ [Zones] [Colors] [Effects]   │
└──────────────────────────────┘
```

**Behavior**:
- Sidebar becomes bottom tab bar (48px height)
- Inspector slides in from bottom (bottom sheet modal)
- Canvas uses full viewport width
- Touch targets minimum 44×44px
- Vertical scrolling for zone list
- Swipe gestures for tab switching

---

## 🎨 Color & Typography Applied

### Header Section
- **Background**: `bg-app` (#0A0A0A)
- **Text**: `text-primary` (#FFFFFF) for headings, `text-secondary` for meta
- **Borders**: `border-default` (#2A2A2A) at bottom
- **Accent**: Cyan (#00E5FF) for active mode indicator

### Sidebar
- **Background**: `bg-panel` (#141414)
- **Card Default**: `bg-elevated` (#1E1E1E) on hover
- **Text**: `text-primary` for zone names, `text-secondary` for labels
- **Toggles**: Green (#00E676) when enabled, gray when disabled
- **Borders**: Subtle `border-default`

### Main Canvas
- **Background**: `bg-app` (#0A0A0A)
- **Canvas Area**: Slightly lighter `bg-elevated` (#1E1E1E) for contrast
- **Preview Region**: Black `bg-input` (#0F0F0F) for LED rendering
- **Controls**: Accent colors for sliders and buttons

### Inspector
- **Background**: `bg-panel` (#141414)
- **Sections**: Expand with subtle animation
- **Values**: Monospace `font-mono text-sm` in `text-secondary`
- **Actions**: Primary buttons in accent cyan (#00E5FF)

### Footer / Status Bar
- **Background**: `bg-app` (#0A0A0A)
- **Text**: Small `text-secondary` and `text-tertiary`
- **Status Indicator**: Green dot (●) connected, yellow (⚠) warning, red (✕) offline
- **Borders**: `border-default` at top

---

## 🔄 Information Density Levels

### Level 1: Minimal (Focused Creation)
- Show only: Canvas + selected zone card
- Hide sidebar and inspector
- Keyboard: `H` to toggle sidebar, `I` to toggle inspector
- Ideal for editing animations

### Level 2: Standard (Default View)
- Show: Canvas + sidebar + inspector
- All controls visible
- Ideal for design and testing

### Level 3: Maximum (Deep Analysis)
- Show: All panels expanded
- Add: Timeline view, performance graph, detailed logs
- Inspector shows all properties and history
- Ideal for debugging and optimization

**Shortcuts**:
- `H` - Toggle sidebar
- `I` - Toggle inspector
- `L1`/`L2`/`L3` or `Ctrl+1`/`Ctrl+2`/`Ctrl+3` - Quick switch density level

---

## 🎯 Interaction Workflow

### Typical User Flow (You, the Power User)

1. **Start**: See all zones in sidebar, canvas showing current state
2. **Select Zone**: Click a zone card in sidebar
   - Inspector updates with zone details
   - Canvas highlights the selected zone
3. **Adjust Brightness**: Drag slider in sidebar or inspector
   - Live preview in canvas
   - Sends to device in real-time
4. **Change Color**: Click 🎨 button
   - Color picker modal opens
   - Canvas updates live as you pick
5. **Apply Animation**: Click ⚡ button
   - Quick animation menu appears
   - Select and preview animation
6. **Fine-tune Speed**: Drag speed slider in inspector
   - Animation updates in real-time
7. **Save**: Click "Save as Preset" in inspector
   - Dialog to name and organize preset
8. **Next Zone**: Click next zone card, repeat

**Total time to adjust one zone**: ~10-15 seconds

---

## 🔐 State Management Strategy

### What Lives in Sidebar (Always Visible)
- Zone list and enabled/disabled state
- Quick brightness slider per zone
- Quick animation selector per zone

### What Lives in Inspector (Detail-Oriented)
- Full zone configuration
- Color space selection (RGB, HSV, etc.)
- Animation parameters and timing
- Hardware configuration
- Preset management

### What Lives in Canvas (Visualization)
- Real-time LED preview
- Global brightness slider
- Timeline (when in Edit mode)
- Playback controls

**Principle**: Information appears where it's needed, not everywhere. Sidebar = quick changes, Inspector = detailed tweaking, Canvas = validation.

---

## 📊 Performance Considerations

- **Sidebar**: Max 15-20 zones before scrolling (prevents huge sidebar)
- **Canvas**: 60 FPS LED preview rendering
- **Inspector**: Only renders when visible (toggle off when not needed)
- **Tabs**: Content renders on-demand (color panel loads only when tab active)

---

## 🎬 Animation & Transitions

### Panel Transitions
- **Sidebar collapse**: 300ms ease-out
- **Inspector slide-in/out**: 250ms ease-out
- **Tab switch**: Fade + slide (150ms)
- **Zone selection**: Subtle glow on canvas (200ms)

### Hover States
- **Sidebar Zone Cards**: Scale 1.02, elevation change
- **Inspector Sliders**: Handle grows, color highlights
- **Canvas Preview**: Subtle grid appears on hover

---

## 🚀 Future Expandability

### Phase 2: Animation Editor
- **Canvas area expansion**: Timeline + waveform editor below preview
- **Right panel**: Animation property browser
- **New tab**: Animation timeline/keyframe editor

### Phase 3: Wearable Designer
- **Canvas upgrade**: 3D garment preview (Three.js)
- **Sidebar expansion**: Garment zones (front, back, sleeves, etc.)
- **New inspector tab**: Garment configuration

### Phase 4: Mobile Companion
- **Bottom tab bar**: Zones, Colors, Effects, Settings
- **Canvas**: Full-screen LED preview
- **Sidebar**: Swipeable zone cards

---

## ✅ Layout Checklist

Before implementation, verify:
- [ ] Header includes logo, modes, status indicators, settings
- [ ] Sidebar shows all zones with quick controls
- [ ] Canvas dominates central area for LED preview
- [ ] Inspector provides detailed property editing
- [ ] Footer displays system status (connection, FPS, power)
- [ ] Responsive breakpoints work (desktop, tablet, mobile)
- [ ] Keyboard shortcuts implemented for power users
- [ ] Information density levels (minimize/maximize)
- [ ] Color palette consistent with design guide
- [ ] Spacing follows 8px grid throughout
- [ ] Touch targets minimum 44×44px on mobile

---

**Ready for LED Visualization Design (Document #2)** ✅

