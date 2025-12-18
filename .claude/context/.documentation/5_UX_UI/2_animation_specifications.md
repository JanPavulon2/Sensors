# 🎬 Animation Specifications & Interaction Patterns

**Date**: 2025-12-10
**Status**: Detailed animation system specifications
**Audience**: Frontend developers, UX/UI designers

---

## Table of Contents
1. [Animation System Overview](#overview)
2. [Per-Animation Details](#per-animation)
3. [Interaction Patterns](#interactions)
4. [Micro-animations & Transitions](#micro)
5. [Accessibility in Motion](#accessibility)

---

## Animation System Overview

### **Supported Animations** (6 total, 5 enabled)

| ID | Name | Type | Status | Visual | Complexity |
|-----|------|------|--------|--------|------------|
| BREATHE | Breathing Pulse | Ambient | ✅ Enabled | Smooth fade in/out | Basic |
| COLOR_FADE | Rainbow Rotation | Color | ✅ Enabled | Hue spectrum sweep | Basic |
| COLOR_CYCLE | Color Steps | Color | ✅ Enabled | RGB cycling | Basic |
| SNAKE | Pixel Chase | Motion | ✅ Enabled | Single snake travel | Intermediate |
| COLOR_SNAKE | Rainbow Chase | Motion | ✅ Enabled | Multi-color gradient | Advanced |
| MATRIX | Code Rain | Effect | ⚠️ Disabled | Falling drops | Advanced |

---

## Per-Animation Details

### **BREATHE Animation**

**Description**: Smooth sine wave fade that mimics breathing/pulsing light

**Parameters**:
- `ANIM_SPEED` (1-100%, step 10%)
  - 1% = 5 seconds per cycle
  - 50% = 1 second per cycle
  - 100% = 0.2 seconds per cycle
  - Default: 50%

- `ANIM_INTENSITY` (0-100%, step 10%)
  - 0% = No brightness variation (stays constant)
  - 50% = Pulse between 50-100% of zone brightness
  - 100% = Pulse between 0-100% of zone brightness
  - Default: 75%

- `ANIM_PRIMARY_COLOR_HUE` (0-360°, step 10°)
  - Selects the breathing color
  - Default: 0° (red)

**Visual Behavior**:
```
100% ╱╲    ╱╲
     ╱  ╲  ╱  ╲
 50% ╱    ╲╱    ╲  ← intensity 75%, so max=100%, min=50%

  0% ╴────────────────  (if intensity=0%, stays flat)
     0s    1s    2s  (at 50% speed)
```

**UI Representation**:
- Icon: ⊙ (pulsing dot)
- Color: Soft glow that pulses
- Preview: Mini strip with gentle fade loop

**Use Cases**:
- Ambient mood lighting
- Sleep/meditation mode
- Attention indicator
- Standby state

---

### **COLOR_FADE Animation**

**Description**: Smooth transition through full hue spectrum (rainbow rotation)

**Parameters**:
- `ANIM_SPEED` (1-100%, step 10%)
  - 1% = 360 seconds full cycle (slow rainbow)
  - 50% = 7.2 seconds full cycle (medium)
  - 100% = 1.44 seconds full cycle (fast)
  - Default: 50%

- `ANIM_INTENSITY` (0-100%, step 10%)
  - Brightness variation (like breathe)
  - 0% = Constant brightness
  - 100% = Pulse while fading
  - Default: 75%

**Visual Behavior**:
```
Red → Orange → Yellow → Green → Cyan → Blue → Magenta → Red...
(continuous smooth transition)
```

**UI Representation**:
- Icon: 🌈 (rainbow arc)
- Color: Rainbow swirl that cycles
- Preview: Mini strip with rainbow rotation

**Use Cases**:
- Trippy/party mode
- Visual feedback for music
- Meditation with color therapy
- Calming continuous motion

---

### **COLOR_CYCLE Animation**

**Description**: Simple step-wise RGB cycling (RED → GREEN → BLUE)

**Parameters**: None (hardcoded)

**Behavior**:
- RED (3 seconds)
- GREEN (3 seconds)
- BLUE (3 seconds)
- Loop

**Visual Behavior**:
```
RED ██████████████   [3s]
GRN ██████████████   [3s]
BLU ██████████████   [3s]
```

**UI Representation**:
- Icon: 🟥 (basic color box)
- Color: Three-color stepped animation
- Preview: Mini strip stepping through colors

**Use Cases**:
- Testing/debugging
- Simple mood indicators
- Clear state transitions
- Beginner-friendly

---

### **SNAKE Animation**

**Description**: Single pixel (or short chain) travels through all pixels with fading tail

**Parameters**:
- `ANIM_SPEED` (1-100%, step 10%)
  - 1% = Very slow crawl
  - 50% = Moderate travel
  - 100% = Very fast zoom
  - Default: 50%

- `ANIM_LENGTH` (1-20px, step 1px)
  - 1px = Single pixel
  - 5px = Typical snake length
  - 20px = Very long tail
  - Default: 5px

- `ANIM_PRIMARY_COLOR_HUE` (0-360°, step 10°)
  - Snake head color
  - Default: 240° (blue)

**Visual Behavior**:
```
Pixel 0: ●●●●●------- [Head at position 0, tail behind]
Pixel 1: ---●●●●●----- [Head at position 1]
Pixel 2: ------●●●●●-- [Head at position 2]
         ...
```

**Color Gradient**:
- Head (position 0 of snake): 100% brightness
- Middle: Linear fade
- Tail: 0% brightness (fades out)

**UI Representation**:
- Icon: 🐍 (snake)
- Color: Single-color snake moving
- Preview: Mini strip with snake traveling

**Use Cases**:
- Loading animation
- Activity indicator
- Chase effect for gaming
- Directional movement visualization

---

### **COLOR_SNAKE Animation**

**Description**: Multi-color snake with rainbow gradient across body

**Parameters**:
- `ANIM_SPEED` (1-100%, step 10%)
  - Same as SNAKE
  - Default: 50%

- `ANIM_LENGTH` (2-5px, step 1px)
  - Range smaller than SNAKE (requires gradient space)
  - Default: 3px

- `ANIM_PRIMARY_COLOR_HUE` (0-360°, step 10°)
  - Starting hue of rainbow
  - Default: 0° (starts at red)

- `ANIM_HUE_OFFSET` (1-180°, step 5°)
  - Hue difference between each pixel in snake
  - 60° = Each pixel is 60° different (R→Y→G)
  - Default: 60°

**Visual Behavior**:
```
Snake with HUE_OFFSET=60°:
●(Red) ●(Yellow) ●(Green) [traveling left→right]

Snake with HUE_OFFSET=30°:
●(Red) ●(Orange) ●(Yellow) ●(Lime) [more colors, smoother)
```

**Continuous Hue Rotation**:
- While moving, hue offset continuously rotates
- Creates "rainbow wave" effect
- All zones synchronized

**UI Representation**:
- Icon: 🌈🐍 (rainbow snake)
- Color: Rainbow-gradient snake moving
- Preview: Mini strip with multi-color snake

**Use Cases**:
- Party/celebration mode
- Psychedelic effects
- High-energy music
- Attention-grabbing indicator

---

### **MATRIX Animation** (Currently Disabled)

**Description**: "Code rain" effect - digital drops falling through zones

**Parameters**:
- `ANIM_SPEED` (1-100%, step 10%)
  - Fall speed
  - Default: 50%

- `ANIM_LENGTH` (2-8px, step 1px)
  - Drop length
  - Default: 4px

- `ANIM_INTENSITY` (0-100%, step 10%)
  - Brightness of drops
  - Default: 75%

- `ANIM_PRIMARY_COLOR_HUE` (0-360°, step 10°)
  - Drop color (typically green)
  - Default: 120° (green)

**Visual Behavior**:
```
Zone 1: -------●●●●----- [drop at position 4]
Zone 2: ------●●●●------- [drop at position 3, same as zone 1]
Zone 3: ---●●●●----------- [drop at position 0]

Each zone has independent drop positions
```

**Per-Zone Independence**:
- Each zone has its own falling drop(s)
- Different start times for staggered effect
- Random spawn probability per frame

**Brightness Gradient**:
- Head (bright): 100%
- Middle: Linear fade
- Tail: 0%

---

## Interaction Patterns

### **Animation Selection Flow**

```
User clicks animation selector dropdown
  ↓
Shows list of 6 animations with icons, names, descriptions
  ↓
User hovers over animation
  ↓
Show thumbnail preview loop (2-second sample)
  ↓
User clicks animation
  ↓
Animation applied to zone
  ↓
Parameter sliders appear/update
  ↓
User adjusts parameters (live preview updates)
```

---

### **Parameter Adjustment Workflow**

**Desktop**:
```
User drags slider
  → Parameter updates (no debounce, live)
  → Mini preview updates immediately
  → WebSocket sends change to backend
  → Canvas shows new animation
```

**Mobile**:
```
User taps slider
  → Slider expands to full-screen interface
  → Drag or use +/- buttons
  → Parameter updates on lift
  → WebSocket sends change
  → Canvas shows new animation
  → Tap outside to close
```

---

### **Preset Management**

**Save Preset Flow**:
```
User clicks "Save Preset" button
  ↓
Modal dialog appears
  ↓
User enters preset name + optional description
  ↓
User clicks "Save"
  ↓
Preset saved locally (localStorage)
  ↓
Added to preset dropdown
  ↓
Toast notification "Preset saved!"
```

**Load Preset Flow**:
```
User clicks preset dropdown
  ↓
Shows: Built-in presets (disabled) | User presets (enabled)
  ↓
User clicks preset
  ↓
Parameters instantly update
  ↓
Zone animation applies immediately
  ↓
Optional: smooth transition over 0.5-1s
```

**Delete Preset Flow**:
```
User right-clicks preset in dropdown
  ↓
Context menu appears
  ↓
User clicks "Delete"
  ↓
Confirmation dialog
  ↓
User confirms
  ↓
Preset deleted
  ↓
Toast notification "Preset deleted!"
```

---

### **Animation Transition**

When switching from one animation to another:

**Option 1: Crossfade** (default, smooth)
```
Old animation fades out (200ms)
  ↓ (simultaneous)
New animation fades in (200ms)
  ↓
New animation fully visible
```

**Option 2: Instant** (for urgent changes)
```
Old animation stops immediately
  ↓
New animation starts immediately
  ↓
No fade effect
```

**Option 3: Pulse** (for energy)
```
Old animation plays
  ↓
Brightness drops to 0 (50ms)
  ↓
New animation starts at full brightness
  ↓
Creates "reset" feel
```

---

## Micro-animations & Transitions

### **Button Press Animations**

**Play Button**:
```
Normal: ▶ (static)
Hover: ▶ (slightly brighter, glow increases)
Press: ▶ (ripple effect radiates outward)
Active: ⏸ (changes to pause)
```

**Animation Dropdown Button**:
```
Normal: "BREATHE ▼" (text + icon)
Hover: Highlight background, glow increases
Press: Background flash
Open: Highlight stays, dropdown appears below
```

---

### **Slider Interactions**

**On Drag Start**:
```
Thumb increases size (scale 1.2x)
Color brightens to accent color
Glow intensifies
Tooltip appears showing current value
```

**On Dragging**:
```
Smooth following of mouse
Parameter updates every 50ms (debounce)
Thumbnail preview updates instantly
Value label follows slider
```

**On Drag End**:
```
Thumb shrinks back to normal
Parameter finalizes
WebSocket sends final value
Glow fades back
```

**Snap Points** (optional visual feedback):
```
As user drags near key values (25%, 50%, 75%, 100%)
Slider "sticks" to snap point momentarily
Visual pulse at snap point
Haptic feedback (if available)
```

---

### **Animation Preview Loop**

**8-Pixel Strip Loop**:
```
Time 0ms:   ● ● ● ● ● ● ● ●  (starting state)
Time 100ms: (smooth transition)
Time 200ms: (updated frame)
...
Loop back to time 0ms after full animation cycle
```

**Timing**:
- Always shows at least 2 full animation cycles
- Minimum loop duration: 1 second
- Maximum loop duration: 5 seconds
- Synced with parameter changes

---

### **Color Change Transitions**

When user changes animation color via hue wheel:

```
Current color held for 100ms
  ↓
Transition to new color (200ms linear fade)
  ↓
New color displayed on canvas
```

Smooth enough to feel responsive, but not jarring.

---

### **Mode Switch Animations**

When switching zone modes (STATIC → ANIMATION → OFF):

**STATIC → ANIMATION**:
```
Zone brightness holds steady
  ↓
Animation parameters appear (fade in, 100ms)
  ↓
Animation starts playing
```

**ANIMATION → STATIC**:
```
Animation fades out (100ms)
  ↓
Static color displayed
  ↓
Animation parameters hide (fade out)
```

**Any → OFF**:
```
Current display fades to black (200ms)
  ↓
Zone disabled indicator shows
  ↓
Controls become slightly grayed out
```

---

## Accessibility in Motion

### **Respects prefers-reduced-motion**

```css
@media (prefers-reduced-motion: reduce) {
  /* Disable glow animations */
  .led-pixel {
    animation: none !important;
    box-shadow: none !important;
  }

  /* Keep structure but no motion */
  .slider {
    transition: none;
  }

  /* Instant color changes */
  .color-change {
    transition: none !important;
  }
}
```

### **Animation Speed Constraints**

- Fastest animation speed: 100% = 1.44 seconds per cycle (safe)
- Slowest: 1% = 360 seconds per cycle (safe)
- No strobe effects (flashing > 3 Hz avoided)
- Color transitions never instantaneous

### **Motion Warnings**

- For intense animations (MATRIX, COLOR_SNAKE fast), consider adding:
  - "⚠️ This animation may cause motion sickness" warning
  - Checkbox to remember "don't show again"
  - Option to reduce speed/intensity automatically

### **Audio Cues** (Optional)

- Animation started: Soft chime (100ms)
- Preset saved: Success chime (200ms)
- Error: Alert tone (100ms)
- Mode changed: Click sound (50ms)

All audio can be toggled in settings.

---

## Animation Parameter Presets (Built-in)

### **Ambient Presets**

**"Zen Breathe"**
- Animation: BREATHE
- ANIM_SPEED: 30% (2s cycle)
- ANIM_INTENSITY: 50%
- ANIM_PRIMARY_COLOR_HUE: 240° (blue)

**"Forest Pulse"**
- Animation: BREATHE
- ANIM_SPEED: 20% (3s cycle)
- ANIM_INTENSITY: 40%
- ANIM_PRIMARY_COLOR_HUE: 120° (green)

---

### **Party Presets**

**"Rainbow Rave"**
- Animation: COLOR_FADE
- ANIM_SPEED: 80% (2s full cycle)
- ANIM_INTENSITY: 100%

**"Neon Snake"**
- Animation: COLOR_SNAKE
- ANIM_SPEED: 70%
- ANIM_LENGTH: 4px
- ANIM_HUE_OFFSET: 45°

---

### **Motion Presets**

**"Loading..."**
- Animation: SNAKE
- ANIM_SPEED: 60%
- ANIM_LENGTH: 3px
- ANIM_PRIMARY_COLOR_HUE: 240°

**"Fast Pulse"**
- Animation: SNAKE
- ANIM_SPEED: 90%
- ANIM_LENGTH: 1px
- ANIM_PRIMARY_COLOR_HUE: 0°

---

### **Work/Gaming Presets**

**"Focus Blue"**
- Animation: BREATHE
- ANIM_SPEED: 40%
- ANIM_INTENSITY: 60%
- ANIM_PRIMARY_COLOR_HUE: 200°

**"Gaming Alert"**
- Animation: SNAKE
- ANIM_SPEED: 80%
- ANIM_LENGTH: 2px
- ANIM_PRIMARY_COLOR_HUE: 300°

---

## Animation Performance Targets

### **Rendering**

- Desktop: 60 FPS (16.67ms per frame)
- Mobile: 30 FPS (33ms per frame), graceful degradation
- Canvas updates throttled to animation update rate
- No jank when adjusting parameters

### **WebSocket**

- Parameter changes debounced 50ms
- Backend receives at most 20 updates/second
- Frames sent at actual animation rate (varies)
- Graceful fallback if WebSocket lags

### **Optimization Strategies**

1. **Request Animation Frame**: Use raf() for smooth rendering
2. **Debouncing**: Delay WebSocket sends by 50ms
3. **Throttling**: Redraw canvas every 16ms max
4. **Caching**: Pre-compute color values
5. **Virtual Rendering**: Only render visible pixels

---

## Future Animation Ideas (Phase 3+)

- **Reactive Animations**: Audio/mic input
- **Keyframe Timeline**: Sequence multiple animations
- **Particle Effects**: Sparks, fire, rain
- **Shader Effects**: Wave, ripple, strobe
- **AI-Generated**: Text-to-animation
- **Waveform Sync**: Sync to music frequency bands

---

*Created for Phase 1 implementation of Diuna UX/UI System*
