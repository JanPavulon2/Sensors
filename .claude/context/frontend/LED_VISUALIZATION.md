---
Last Updated: 2025-11-26
Updated By: @agent-uiux-designer
Changes: Initial LED strip visualization and rendering strategy
---

# Diuna App - LED Strip Visualization Strategy

## 🎯 Overview

LED strip visualization is the **hero element** of the dashboard. It must be:
- **Accurate**: Visually matches actual hardware
- **Beautiful**: Professional, refined, not garish
- **Responsive**: Smooth animations, real-time updates
- **Informative**: Shows color, brightness, animation state clearly
- **Elegant**: Subtle glow effects, not party lighting

---

## 📐 Visual Representation Philosophy

### Design Principles

1. **Physical Accuracy**
   - Represent actual LED pixel dimensions
   - Show actual pixel count per zone
   - Reflect color order (BGR, GRB, RGB)

2. **Refined Elegance**
   - LED glow without harsh neon look
   - Subtle shadows and depth
   - Minimal visual clutter
   - Dark background with subtle grid (optional)

3. **Contextual Information**
   - Zone names and boundaries clear
   - Brightness/intensity visible
   - Animation type (if running) indicated
   - Time/timing information (when applicable)

4. **Studio Professionalism**
   - Similar to professional tools (DaVinci Resolve, Ableton)
   - High-end audio equipment aesthetic
   - Technical accuracy without technical clutter

---

## 🖼️ Canvas Container Design

### Overall Canvas Structure

```
┌─────────────────────────────────────────────────────────┐
│ [Canvas Container - bg-input #0F0F0F]                  │
│                                                         │
│   ┌──────────────────────────────────────────────────┐ │
│   │ [Visualization Area]                             │ │
│   │                                                  │ │
│   │   [LED STRIP VISUAL]                            │ │
│   │                                                  │ │
│   │ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○   (FLOOR)    │ │
│   │                                                  │ │
│   │ ● ● ● ● ● ● ● ● ● ● ● ● ● ●     (LEFT)     │ │
│   │                                                  │ │
│   │ [Info overlay]                                  │ │
│   └──────────────────────────────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Dimensions**:
- **Container**: Full width (flexible), height 400-600px (desktop)
- **Background**: `#0F0F0F` (slightly lighter than app background)
- **Padding**: 32px horizontal, 24px vertical
- **Border**: Subtle `border-default` (#2A2A2A), 1px
- **Border Radius**: `rounded-lg` (12px)

---

## 💡 LED Pixel Rendering

### Individual LED Appearance

**Visual Style**:
```
Each LED pixel = small rectangle with glow effect

┌─────────────────────┐
│                     │
│   [LED PIXEL]       │  ← Individual LED with glow
│                     │
└─────────────────────┘
```

**Pixel Dimensions**:
- **Width**: 12px (can scale with zoom)
- **Height**: 20px (can scale with zoom)
- **Border Radius**: 2px (subtle, not fully rounded)
- **Gap between pixels**: 4px
- **Minimum gap between zones**: 16px (visual separator)

### LED Glow Effect (CSS/Canvas)

```javascript
// Each LED pixel receives:
// 1. Main color fill
// 2. Multiple box-shadows for glow
// 3. Inset highlight for dimension

.led-pixel {
  width: 12px;
  height: 20px;
  border-radius: 2px;
  background: <current-color>;

  box-shadow:
    // Inner glow (soft)
    0 0 4px rgba(<color>, 0.6),
    // Mid glow (medium)
    0 0 10px rgba(<color>, 0.4),
    // Outer glow (fading)
    0 0 16px rgba(<color>, 0.2),
    // Inset highlight for dimension
    inset 0 1px 2px rgba(255, 255, 255, 0.2);

  box-sizing: border-box;
}
```

### Color Accuracy

**Color Values**:
- Use exact RGB values from hardware state
- No color space conversions in display
- Apply brightness scaling to color (darken when brightness < 100%)
- Show actual color order (BGR/GRB/RGB) correctly

**Off Pixels**:
- Black pixels (#000000) get slight fill: `rgba(0, 0, 0, 0.4)`
- Border visible: `border: 1px solid rgba(128, 128, 128, 0.2)`
- No glow effect when off
- Provides visual structure without distraction

**Brightness Visualization**:
```
Brightness 100% → Full color saturation + max glow
Brightness 75%  → 75% color intensity + medium glow
Brightness 50%  → 50% color intensity + reduced glow
Brightness 25%  → 25% color intensity + minimal glow
Brightness 0%   → Off (dark with subtle outline)
```

---

## 🏗️ Zone Layout Structure

### Multi-Zone Strip Arrangement

**Horizontal Layout** (default, for most strips):

```
Zone: FLOOR (15 pixels, GPIO 18)
┌─────────────────────────────────┐
│ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○  │
└─────────────────────────────────┘

Zone: LEFT (14 pixels, GPIO 18)
┌───────────────────────────────┐
│ ● ● ● ● ● ● ● ● ● ● ● ● ● ●  │
└───────────────────────────────┘

Zone: TOP (12 pixels, GPIO 18)
┌─────────────────────────┐
│ ◆ ◆ ◆ ◆ ◆ ◆ ◆ ◆ ◆ ◆ ◆ ◆ │
└─────────────────────────┘
```

**Vertical Layout** (for wearables, future):

```
Front Collar   ○ ○ ○ ○
Front Chest    ● ● ● ● ● ● ●
Front Waist    ◆ ◆ ◆ ◆ ◆
Sleeve Right   □ □ □ □
Sleeve Left    ■ ■ ■ ■
Back Upper     △ △ △ △ △
Back Lower     ▲ ▲ ▲ ▲ ▲ ▲ ▲
```

### Zone Header & Labels

**Per-Zone Header**:
```
┌────────────────────────────────────────────┐
│ FLOOR  (15px @ GPIO18)  [Brightness: 78%] │  ← Zone info
├────────────────────────────────────────────┤
│ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○           │  ← Pixels
└────────────────────────────────────────────┘
```

**Label Information**:
- **Zone Name**: Bold, `text-primary`, `text-lg`
- **Pixel Count**: Small gray text, `text-tertiary`
- **GPIO Pin**: Tiny monospace, `text-tertiary`
- **Brightness**: Numeric value, updates in real-time
- **Layout**: Flex row, space-between

**Spacing**:
- Header height: 28px
- Header padding: 8px horizontal
- Zone container spacing: 16px between zones

---

## 🎨 Color Visualization Modes

### Mode 1: Single Color (Default)

**Appearance**: All pixels show current zone color

```
FLOOR (Cyan, 100% brightness)
┌────────────────────────────────────────┐
│ ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●      │  ← All pixels cyan
└────────────────────────────────────────┘
```

**Use Case**: Static mode, solid colors, perfect for tuning brightness

### Mode 2: Animation Preview (Real-Time)

**Appearance**: Shows actual animation frame

```
FLOOR (Breathe animation, 1.2s cycle)
┌────────────────────────────────────────┐
│ ● ● ● ● ● ◌ ◌ ◌ ◌ ◌ ◌ ◌ ◌ ● ●      │  ← Breathing effect
└────────────────────────────────────────┘
```

**Features**:
- Renders actual animation frames (60 FPS)
- Shows color variation across pixels
- Displays animation progression
- Smooth interpolation between frames

### Mode 3: Analysis View (Debug)

**Appearance**: Show pixel index + technical info

```
FLOOR
┌────────────────────────────────────────┐
│ 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15
│ ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●
│ Avg: #00E5FF | Min: #0A8899 | Max: #00FFFF
└────────────────────────────────────────┘
```

**Toggle**: Keyboard `D` or button in debug menu
**Information**:
- Pixel indices below each LED
- Color values (clickable to inspect)
- Animation data (timing, speed, etc.)
- Performance metrics (render time, frame rate)

---

## 🎬 Animation & Motion

### Smooth Rendering

- **Frame Rate**: 60 FPS target (16.67ms per frame)
- **Interpolation**: Linear color interpolation between animation frames
- **Easing**: Use animation's defined easing curve
- **Optimization**: Use `requestAnimationFrame` for smooth updates

### Animation Indicators

**Status Badge** (optional, above zone):
```
▶ Running (Breathe) | Speed: 1.0x | Time: 1.2s / 2.4s
```

**Visual Cues**:
- Subtle pulse around zone container when animating
- Glow intensity matches animation intensity
- Zone border accent color matches animation dominant color

### State Transitions

**Fade-in** (when animation starts):
```css
animation: fade-in 0.3s ease-out;
@keyframes fade-in {
  from { opacity: 0.5; filter: blur(2px); }
  to { opacity: 1; filter: blur(0); }
}
```

**Crossfade** (between animations):
```css
animation: crossfade 0.5s ease-in-out;
@keyframes crossfade {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}
```

---

## 🔍 Interaction & Feedback

### Hover Effects

**On Zone Area**:
```
Default:  Zone cards with subtle border
Hover:    Border glow (cyan), background elevation
          + "Click to select" tooltip appears
```

**On Individual Pixel**:
```
Hover:    Pixel enlarged slightly (110%),
          tooltip shows: "Pixel #5: #00E5FF (Cyan)"
```

### Click & Selection

**Selecting a Zone**:
1. Click on zone pixels or zone header
2. Zone gets highlighted border (accent color)
3. Glow effect applied: `box-shadow: 0 0 20px rgba(0, 229, 255, 0.5)`
4. Zone selected in sidebar (sync with sidebar selection)
5. Inspector updates to show zone details

### Right-Click Context Menu

```
[Zone Context Menu]
├─ Select All Pixels
├─ Copy Color
├─ Paste Color
├─ Reset to Default
├─ Export Zone Animation
└─ Zone Settings...
```

---

## 📊 Additional Visualization Elements

### Below Canvas: Brightness Slider (Global)

```
Brightness
───────●──────────────────────────── 100%

    Current: 78%   [Slider Handle showing exact value]

[Reset to 100%]  [Save as Default]
```

**Behavior**:
- Single slider controls all zones simultaneously
- Applies brightness scaling to LED rendering
- Live preview as dragging
- Tooltip shows percentage
- Double-click to reset to 100%

### Optional: Animation Timeline (If Edit Mode)

```
Time: 0.0s ════════●════════════════ 2.4s

[◀ Prev Frame] [▶ Play/Pause] [Next Frame ▶]
Speed: 1.0x ──●──  [Loop: ⏮]
```

**Only visible in Edit/Debug mode**

---

## 🌈 Color Space Visualization

### RGB Color Display

**Simple**: Single color bar above zone

```
FLOOR
┌────────────────┐
│ [████████████] │ ← Color preview bar (48px height)
└────────────────┘
│ ○ ○ ○ ○ ○ ○ ○ │ ← LED pixels
```

**Detailed** (on hover or click):
```
Color Information Panel
─────────────────────────────────────
RGB:  (0, 229, 255) - Cyan
Hex:  #00E5FF
HSV:  H: 186° | S: 100% | V: 100%
Brightness: 78%
```

### Brightness Visualization

**On LED Pixel**:
```
Full brightness:     ●●●● (bright, max glow)
75% brightness:      ●●●◐ (medium glow)
50% brightness:      ●●◐◐ (reduced glow)
25% brightness:      ●◐◐◐ (minimal glow)
0% brightness:       ◐◐◐◐ (off, no glow)
```

Brightness = glow intensity (visual feedback of actual value)

---

## 🎯 Responsive Behavior

### Desktop (≥1280px)

**Canvas Size**: 1200×500px
**Pixel Size**: 12×20px
**Gap**: 4px
**Zone Gap**: 16px

```
Full detail view, all zones visible
Maximum visual information
```

### Tablet (768-1279px)

**Canvas Size**: 100% width, 400px height
**Pixel Size**: 10×18px
**Gap**: 3px
**Zone Gap**: 12px

```
Scrollable zones if needed
Slightly compressed but readable
```

### Mobile (<768px)

**Canvas Size**: 100% width, 300px height
**Pixel Size**: 8×14px
**Gap**: 2px
**Zone Gap**: 8px

```
Single zone at a time (tabs or swipe)
Vertical stacking
Simple one-zone-focused view
```

---

## 🔧 Technical Implementation Approach

### Canvas Technology Options

#### Option A: React Konva (RECOMMENDED)
```javascript
- 2D canvas library (wrapped for React)
- Optimized rendering for many elements
- Touch gestures built-in
- Perfect for 60 FPS LED animations
- Good performance scaling
```

#### Option B: Canvas API (Direct)
```javascript
- Lower-level, more control
- Maximum performance
- Manual animation loop needed
- More complex but can optimize further
```

#### Option C: SVG
```javascript
- Vector-based (not optimal for many pixels)
- Good for clean rendering, but slower
- Not ideal for 60 FPS animations
- Better for static displays
```

**Recommendation**: Start with **React Konva** for optimal balance of performance, simplicity, and React integration.

---

## 🎨 Styling Details

### LED Pixel Colors (Accurate)

**Active LED**:
```css
fill: <zone-color-rgb>
filter: drop-shadow(0 0 4px rgba(<zone-color>, 0.6))
        drop-shadow(0 0 10px rgba(<zone-color>, 0.4))
        drop-shadow(0 0 16px rgba(<zone-color>, 0.2))
```

**Off LED**:
```css
fill: rgba(0, 0, 0, 0.4)
stroke: rgba(128, 128, 128, 0.2)
stroke-width: 1px
```

**Brightness Scaling**:
```javascript
const rgba = Color.toRGB();
const brightness = zone.brightness / 100;
const scaledRGB = [
  Math.floor(rgba[0] * brightness),
  Math.floor(rgba[1] * brightness),
  Math.floor(rgba[2] * brightness)
];
// Glow intensity also scales with brightness
const glowAlpha = 0.6 * brightness;
```

### Zone Container Styling

```css
background: bg-input (#0F0F0F)
border: 1px solid border-default (#2A2A2A)
border-radius: rounded-lg (12px)

/* On selection */
border-color: accent-primary (#00E5FF)
box-shadow: 0 0 20px rgba(0, 229, 255, 0.3)

/* On animation */
border: 2px solid accent-primary
animation: zone-pulse 2s ease-in-out infinite
```

### Text Labels

```css
/* Zone name */
font-family: Space Grotesk
font-size: text-lg (18px)
font-weight: semibold (600)
color: text-primary (#FFFFFF)

/* Info text (pixel count, GPIO) */
font-family: JetBrains Mono
font-size: text-xs (12px)
color: text-tertiary (#6B6B6B)

/* Brightness value */
font-family: JetBrains Mono
font-size: text-sm (14px)
color: text-secondary (#A1A1A1)
```

---

## 📋 Accessibility Features

### Keyboard Navigation

```
Tab:              Move between zones
←/→:              Change selected zone
↑/↓:              Adjust brightness of selected zone
C:                Open color picker for selected zone
A:                Open animation menu for selected zone
Space:            Play/pause animation
D:                Toggle debug/analysis view
Escape:           Deselect zone
```

### Screen Reader Support

```html
<!-- Zone area -->
<div
  role="region"
  aria-label="Floor Strip LED Zone"
  aria-describedby="floor-info"
>
  <div id="floor-info">15 pixels, cyan color, 78% brightness</div>

  <!-- LED pixels -->
  <canvas
    aria-label="LED visualization"
    role="img"
  />
</div>
```

### Color Contrast

- **Zone Header**: White (#FFFFFF) on dark background → 20.58:1 ✅
- **Zone Info**: Gray (#A1A1A1) on dark → 8.89:1 ✅
- **Accent Glow**: Cyan (#00E5FF) on dark → 13.2:1 ✅

---

## 🚀 Performance Optimization

### Rendering Optimization

1. **Canvas Batching**: Render all LEDs in single canvas call
2. **Dirty Rectangle**: Only redraw changed zones
3. **Frame Skipping**: Can skip frames at >60 FPS if needed
4. **Layer Caching**: Cache static zone backgrounds

### Memory Management

- **LED Count**: 90 pixels max (current) → ~5MB memory for animation cache
- **Zone Zones**: 9 zones max → minimal overhead
- **Animation History**: Keep last 10 frames only

### Network Optimization

- **Update Batching**: Send LED updates every 16.67ms (60 FPS)
- **Partial Updates**: Only send changed zones
- **Compression**: Use delta encoding for animation frames

---

## ✅ Visualization Checklist

Before implementation:
- [ ] LED pixels rendered with correct dimensions
- [ ] Glow effect applied with proper color and intensity
- [ ] Zone labels show name, pixel count, GPIO info
- [ ] Brightness affects glow intensity visually
- [ ] Animation frames render in real-time (60 FPS target)
- [ ] Color accuracy matches zone state exactly
- [ ] Selection state clearly visible (border glow)
- [ ] Hover effects provide clear feedback
- [ ] Responsive scaling works for tablet/mobile
- [ ] Keyboard navigation implemented
- [ ] Screen reader compatible (ARIA labels)
- [ ] Smooth transitions between states
- [ ] Performance acceptable at 60 FPS

---

**Next: Wait for user guidance before starting Control Hierarchy document** ⏳

