# LED Zones Control UI – UX Requirements Analysis

**Date**: 2025-12-18
**Status**: Analysis Complete - Ready for Design & Implementation
**Target Theme**: Main production theme (Matrix Green #39ff14, Dark #09090b)

---

## Executive Summary

The UX requirements document defines a sophisticated zone control system with:
- **Dashboard overview** (Zone Cards with live previews)
- **Detailed editing** (Zone Detail Panel)
- **Color controls** (Hue + Preset modes, NOT RGB)
- **Animation support** (Grid selection + dynamic parameters)
- **Live preview** (Real-time LED visualization)

**Current Status**:
- ❌ Production UI: ~30% compliant (basic card, no preview/animation/detail)
- ⚠️ Future-design: ~70% compliant (good structure, wrong theme)
- ✅ Theme system: Fully compliant (matrix green + dark mode ready)

---

## 1. Zone Card (Dashboard View)

### Requirements
```
┌──────────────────────────────┐
│ Floor Strip          [⚪]    │  ← Name + On/Off toggle
│ 12 pixels • BREATHE          │  ← Pixel count + Mode
│ [████████████████]           │  ← Live preview strip
│ Brightness: 80%              │  ← Read-only brightness indicator
│ [Ctrl] [•••]                 │  ← Action buttons
└──────────────────────────────┘
```

**Key Points**:
- Medium-sized tiles (responsive grid)
- Shows: name, pixel count, current mode (STATIC/ANIMATION)
- Live preview strip (pixels as dots/squares)
- On/Off toggle (always visible)
- Brightness indicator (read-only, not editable)
- Hover effects (subtle glow/border)
- Click opens Zone Detail Panel
- **NO embedded color/animation controls**

### Current Implementation Analysis

**File**: `frontend/src/components/zones/ZoneCard.tsx`

#### ✅ What We Have
- Zone name display ✓
- Pixel count display ✓
- Hover border effect ✓
- On/Off status indicator ✓
- Brightness display ✓
- Card component structure ✓

#### ❌ What's Missing
1. **Live preview strip** - No LED visualization
   - Need: Compact preview (32-48px height)
   - Should show: Current pixels with actual colors/animation
   - NO static color box, should be animated strip

2. **Mode indicator** - No way to see if STATIC or ANIMATION
   - Need: Text like "• BREATHE" or "• STATIC"
   - Placed in subtitle area

3. **On/Off toggle** - Currently read-only status
   - Need: Clickable toggle button (not just indicator)
   - Should be prominent in header

4. **Brightness as read-only** - Currently has editable slider
   - Current: Brightness slider in card ❌
   - Required: Brightness percentage display only (read-only bar)
   - Slider should ONLY be in Detail Panel

5. **No color preview** - Should NOT show static color
   - Current: Shows hex color box + color picker ❌
   - Required: ONLY live preview (no embedded picker)
   - Color controls belong in Detail Panel

#### ⚠️ What Needs Changes
- Remove embedded color picker
- Remove editable brightness slider
- Replace static color box with live preview strip
- Add mode indicator
- Move "Details" button to open Detail Panel (implement handler)

### Desired Card Size
- **Desktop**: ~280px width, responsive grid
- **Tablet**: Larger cards, 2-3 per row
- **Mobile**: Full width, single column

---

## 2. Zone Detail Panel

### Requirements
```
╔════════════════════════════════╗
║ Floor Strip              [✕]   ║  ← Header with close button
╠════════════════════════════════╣
║ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░║  ← Live preview (full width)
║ [████████████████] 80%         ║
╠════════════════════════════════╣
║ ▼ Status                       ║  ← Collapsible sections
║   ◉ On/Off  [Toggle Button]   ║
║   Mode:     [STATIC | ANIM]   ║
╠════════════════════════════════╣
║ ▼ Color                        ║
║   [Hue Wheel / Presets]        ║
║   Brightness Slider            ║
╠════════════════════════════════╣
║ ▼ Animation (if ANIMATION)     ║
║   [Grid of animations]         ║
║   [Dynamic parameters]         ║
╚════════════════════════════════╝
```

**Key Points**:
- Side panel or centered overlay (modal)
- Persistent live preview at top
- Scrollable content sections
- Collapsible sections: Status, Color, Animation
- Mode selector (STATIC vs ANIMATION)
- Brightness slider (applies to both static color + animation)
- Optional transition selector (future)
- Navigation arrows (previous/next zone)

### Current Implementation Analysis

**Status**: ❌ DOES NOT EXIST

- No detail panel component exists
- "Details" button in ZoneCard is not implemented
- All controls currently in card (should be in panel)

### What Needs to Be Built

1. **ZoneDetailPanel component**
   - Modal or side panel layout
   - Header with zone name + close button
   - Live preview section
   - Scrollable body with collapsible sections
   - Status section (on/off toggle, mode selector)
   - Color section (ColorControlPanel)
   - Animation section (AnimationControlPanel)
   - Navigation controls (prev/next zone)

2. **Live preview rendering**
   - Compact LED visualization at top
   - Shows actual animation output
   - Reflects brightness changes
   - Shape-aware (strip, circle, matrix)

3. **Section management**
   - Collapsible sections (expand/collapse)
   - Smooth animations
   - Remember user preferences

---

## 3. Color Controls

### Requirements

#### Hue Mode
```
    [Hue Wheel - Circular 360°]
         or
    [Hue Slider - Horizontal]

    NO saturation/value control
    Display: Hue value (0-360°)
```

#### Preset Mode
```
┌──────────────────────────────────┐
│ Preset Colors                    │
│ [●] [●] [●] [●] [●]             │  Red, Green, Blue, Yellow, Cyan
│ [●] [●] [●] [●] [●]             │  Magenta, White, Orange, Purple...
│ [●] [●] [●] [●] [●]             │  (Grid layout, expandable)
└──────────────────────────────────┘
```

#### Brightness (Separate)
```
Brightness  [─────●───────] 80%
```

**Key Points**:
- Two color input methods: **Hue** OR **Preset**
- NO RGB mode (requirements don't include it)
- Brightness is independent control
- Applied globally (static + animation both use it)
- Fast color selection

### Current Implementation Analysis

**File**: `frontend/src/components/zones/ZoneCard.tsx`

#### ✅ What We Have
- HexColorPicker from react-colorful ✓
- Brightness slider ✓
- Separate brightness control ✓

#### ❌ What's Missing
1. **Hue-only picker** - Only has RGB hex picker
   - Need: Circular hue wheel (0-360°)
   - Should show: Single value (hue)
   - No saturation/value control needed

2. **Preset colors** - No grid of presets
   - Need: 15-20 curated colors
   - Categories: Basic, Warm, Cool, Natural, White
   - Click to select instantly

3. **Color control removed from card**
   - Move ALL color controls to Detail Panel
   - Card shows only preview (not editable)

### What Needs to Be Built

1. **HueColorPicker component**
   - Canvas-based circular wheel (280px diameter compact, 360px full)
   - Shows current hue as indicator
   - Click/drag to change
   - Displays hue value (0-360°)
   - Smooth interactions
   - Mobile-friendly

2. **PresetColorGrid component**
   - 4-5 columns responsive grid
   - Preset color blocks with labels
   - Show selected state (border/glow)
   - Categories: Basic, Warm, Cool, Natural, White
   - ~20 colors total

3. **ColorControlPanel (integrate)**
   - Tabs: [🎨 Hue] [⭐ Preset]
   - One picker shown at a time
   - Seamless switching
   - Brightness slider below

### Recommended Presets (20 colors)

**Basic (8)**: Red, Green, Blue, Yellow, Cyan, Magenta, White, Black
**Warm (4)**: Orange, Coral, Gold, Amber
**Cool (4)**: Sky Blue, Teal, Indigo, Purple
**Natural (2)**: Forest Green, Lime Green
**White (2)**: Warm White, Cool White

---

## 4. Animation Controls

### Requirements

```
┌────────────────────────────────────┐
│ Animation Selection                │
│                                    │
│ Basic Animations:                  │
│ [📍 STATIC]  [💨 BREATHE]         │
│ [🌅 FADE]    [🔄 CYCLE]           │
│                                    │
│ Advanced:                          │
│ [🐍 SNAKE]   [🐍 COLOR_SNAKE]     │
│ [🟩 MATRIX]                        │
│                                    │
│ Animation Controls:                │
│ Speed: [────●──────] 50ms          │
│ Intensity: [───●───] 75%           │
│ Length: [───●───] 10 pixels        │
│                                    │
└────────────────────────────────────┘
```

**Key Points**:
- Grid of animation tiles (name + icon)
- Selection applies immediately
- Preview updates in real-time
- Parameters shown dynamically
- Parameter types: Range (slider), Enum (select), Bool (toggle)
- Brightness applies to animation output
- Base color MAY be used (depends on animation)

### Current Implementation Analysis

**Status**: ❌ DOES NOT EXIST

- No animation selection UI in production
- No animation parameters
- No animation preview

### What Needs to Be Built

1. **AnimationSelector component**
   - Grid layout of animation tiles
   - Each tile: Icon + Name + Brief description
   - Click to select (applies immediately)
   - Shows current selection
   - Organized by category (Basic, Color, Advanced)

2. **AnimationParametersPanel component**
   - Dynamically generated from backend metadata
   - Slider for range parameters
   - Dropdown for enum parameters
   - Toggle for boolean parameters
   - Show parameter name + value
   - Live preview as user adjusts

3. **Parameter metadata from backend** (NEW API NEEDED)
   - Each animation includes:
     - Name, ID, description
     - Array of parameters with:
       - ID, label, type
       - Min/max for ranges
       - Options for enums
       - Default values

### Animation Types (7 total)

1. **STATIC** - Solid color, no animation
2. **BREATHE** - Brightness pulsing (slow, smooth)
3. **COLOR_FADE** - Hue fade in/out (smooth)
4. **COLOR_CYCLE** - Fast hue rotation (loop)
5. **SNAKE** - Pixels chase pattern
6. **COLOR_SNAKE** - Rainbow chase pattern
7. **MATRIX** - Matrix rain effect

### Parameter Examples

| Animation | Parameters |
|-----------|------------|
| STATIC | (none) |
| BREATHE | Speed (100-1000ms), Intensity (0-100%) |
| COLOR_FADE | Speed (100-1000ms), Length (pixels) |
| COLOR_CYCLE | Speed (100-1000ms), Hue Offset (0-360°) |
| SNAKE | Speed, Length, Intensity |
| COLOR_SNAKE | Speed, Length, Hue Offset |
| MATRIX | Speed, Intensity |

---

## 5. Live Preview System

### Requirements

```
┌────────────────────────────────────┐
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│ ████████████████████████████████  │  ← Real LEDs rendered
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│                                    │
│ Brightness: [────●──────] 80%      │
│ Mode: BREATHE                      │
└────────────────────────────────────┘
```

**Key Points**:
- Always visible in Zone Detail Panel
- Reflects actual rendered frames
- Shows animation in real-time
- Applies brightness changes
- NO overlays or indicators
- Purely visual output
- Respects zone shape (strip, ring, matrix)

### Current Implementation Analysis

#### ✅ What We Have (from future-design reference)
- LEDShapeRenderer component (renders shapes)
- LEDCanvasRenderer component (canvas-based)
- Canvas-based rendering (60 FPS capable)
- Shape support: Strip, Circle, Matrix
- Color transitions
- Glow effects

#### ❌ What's Missing
- NOT in production UI
- NO live preview in current ZoneCard
- NO animation simulation in card

### What Needs to Be Built

1. **Compact LED Preview** (for Zone Card)
   - Height: 32-48px
   - Shows entire zone as horizontal strip
   - Uses LEDShapeRenderer
   - Updates in real-time
   - Very smooth (requestAnimationFrame)

2. **Full LED Preview** (for Zone Detail Panel)
   - Height: 80-120px
   - Full-width rendering
   - Shows shapes: Strip, Circle, Matrix
   - Full animation preview
   - Brightness applied
   - Responsive sizing

3. **Integration points**
   - Receive: Current mode, animation, parameters
   - Display: Real-time animation output
   - Update: On every frame change
   - Optional: WebSocket frame streaming (future)

---

## 6. Design System Integration

### Theme (KEEP AS-IS)

**File**: `frontend/src/index.css` + `frontend/tailwind.config.js`

```javascript
// Primary Color
--primary: 87.6 100% 45.7%    /* #39ff14 - Matrix Green */

// Backgrounds
--background: 0 0% 3.9%        /* #09090b - Near black */
--card: 0 0% 3.9%              /* #09090b */
--muted: 0 0% 20.9%            /* #18181b - Slightly lighter */

// Borders
--border: 217.2 32.6% 17.5%    /* #1e293b - Slate 800 */

// Glow Shadow
box-shadow: 0 0 20px rgba(57, 255, 20, 0.4)  /* Matrix green glow */
```

**Custom colors available**:
- `text-primary`, `text-secondary`, `text-tertiary`
- `bg-app`, `bg-panel`, `bg-elevated`, `bg-input`
- `accent-primary`, `accent-hover`, `accent-active`, `accent-glow`
- `success`, `warning`, `error`, `info`
- Status colors for zone types: `zone-floor`, `zone-lamp`, `zone-desk`, `zone-hood`

### Components to Use

1. **shadcn/ui** (existing library)
   - Button, Card, Slider, Label, Dialog, etc.
   - Already themed to dark mode + matrix green

2. **Icons**
   - Use emoji for animations (📍 🐍 🌅 etc.)
   - Or Lucide React icons if needed

3. **Accessibility**
   - Semantic HTML
   - ARIA labels for interactive elements
   - Keyboard navigation support
   - Focus states (ring-2 ring-primary)

---

## 7. API Requirements

### New Endpoints Needed

#### 1. Animation Metadata
```
GET /api/animations/metadata
Response:
[
  {
    id: "BREATHE",
    name: "Breathe",
    icon: "💨",
    description: "Smooth brightness pulsing",
    category: "Basic",
    parameters: [
      { id: "speed", label: "Speed", type: "range", min: 100, max: 1000, unit: "ms" },
      { id: "intensity", label: "Intensity", type: "range", min: 0, max: 100, unit: "%" }
    ]
  },
  ...
]
```

#### 2. WebSocket Live Frames (Future)
```
ws://api/zones/frames?zoneId=floor

Message:
{
  timestamp: 1234567890,
  zoneId: "floor",
  pixels: [[255, 0, 0], [255, 0, 0], ...],
  animation: "BREATHE",
  brightness: 200
}
```

### Existing Endpoints to Enhance

#### Zone Update
Current: Only brightness + color
Needed: Add mode, animation, parameters

```
PATCH /api/zones/{id}
{
  brightness: 200,
  color: { mode: "HUE", hue: 120 },  // NOT RGB
  state: {
    is_on: true,
    mode: "ANIMATION",  // NEW
    animation: "BREATHE",  // NEW
    parameters: { speed: 500, intensity: 75 }  // NEW
  }
}
```

---

## 8. Component Implementation Order

### Phase 1: Foundation
1. **HueColorPicker** - Circular hue wheel (reusable)
2. **PresetColorGrid** - Color preset grid (reusable)
3. **ColorControlPanel** - Hue + Preset switching
4. **CompactLEDPreview** - Small preview strip for cards

### Phase 2: Detail Panel
1. **ZoneDetailPanel** - Modal wrapper + structure
2. **StatusSection** - On/off, mode selector
3. **ColorSection** - Integrate ColorControlPanel
4. **BrightnessSection** - Slider + indicator
5. **FullLEDPreview** - Full zone visualization

### Phase 3: Animation Controls
1. **AnimationSelector** - Grid of animation tiles
2. **AnimationParametersPanel** - Dynamic parameter controls
3. **AnimationSection** - Integrate into detail panel

### Phase 4: Card Updates
1. Remove embedded controls from ZoneCard
2. Add CompactLEDPreview
3. Add mode indicator
4. Update on/off interaction
5. Wire "Details" button to ZoneDetailPanel

### Phase 5: Integration
1. Connect to backend API
2. Handle WebSocket frames (future)
3. Add error boundaries
4. Performance optimization
5. Mobile responsiveness
6. Accessibility audit

---

## 9. Gap Summary Table

| Feature | Required | Current Prod | Future Design | Status |
|---------|----------|--------------|---------------|--------|
| Zone Card | Yes | 30% | N/A | ❌ Needs work |
| Live Preview (Card) | Yes | 0% | N/A | ❌ Missing |
| Mode Indicator | Yes | 0% | ✓ | ❌ Missing |
| On/Off Toggle | Yes | Read-only | N/A | ⚠️ Partial |
| Detail Panel | Yes | 0% | ✓ | ❌ Missing |
| Hue Picker | Yes | 0% | ✓ | ❌ Missing |
| Preset Grid | Yes | 0% | N/A | ❌ Missing |
| Animation Selector | Yes | 0% | ✓ | ❌ Missing |
| Animation Parameters | Yes | 0% | ✓ | ⚠️ Hardcoded |
| Live LED Preview | Yes | 0% | ✓ | ❌ Missing |
| Brightness Slider | Yes | ✓ Card | ✓ Panel | ⚠️ Wrong place |
| Color from Card | No | ✓ | N/A | ❌ Remove |
| Shape Support | Yes | No | ✓ | ⚠️ Future |
| WebSocket | Future | No | Types only | ❌ Missing |

---

## 10. Design Decisions

### Color Input Choice: WHY Hue + Preset, NOT RGB?

1. **Hue is intuitive** - Users think "I want red" not "I want (255, 0, 0)"
2. **Presets are fast** - Common colors one-click away
3. **RGB is technical** - Confuses non-technical users
4. **Less UI clutter** - Two modes instead of three
5. **Maintains brand** - Matrix green accent highlights hue wheel

### Live Preview Priority

1. **Always visible** - Users see impact immediately
2. **Responsive** - 60 FPS target (requestAnimationFrame)
3. **Real** - Shows actual animation, not simulation
4. **Simple** - No controls in preview area
5. **Educational** - Users learn LED behavior by seeing it

### Collapsible Sections in Detail Panel

1. **Focus** - User edits one thing at a time
2. **Clean** - Less visual overload
3. **Cognitive** - "Status", "Color", "Animation" are clear categories
4. **Future-proof** - Easy to add more sections (transitions, effects)
5. **Mobile** - Works better on small screens

---

## 11. Accessibility Notes

### Keyboard Navigation
```
Tab/Shift+Tab    - Navigate between sections
Enter/Space      - Toggle on/off, select animation
Escape           - Close detail panel
Arrow Keys       - Adjust sliders, select presets
C                - Open color picker (future shortcut)
A                - Open animation selector (future shortcut)
```

### ARIA Labels
- On/off toggle: `aria-pressed="true/false"`
- Sliders: `aria-valuemin`, `aria-valuemax`, `aria-valuenow`
- Color buttons: `aria-label="Select red"` + `aria-current="true"`
- Animation tiles: `aria-selected="true"` for active

### Color Contrast (WCAG AA)
- Text on matrix green: #09090b on #39ff14 → 10.5:1 ✓
- All text meets 4.5:1 minimum ratio
- Status indicators have text labels (not color-only)

---

## 12. Files to Create/Modify

### New Components
- `frontend/src/components/zones/HueColorPicker.tsx`
- `frontend/src/components/zones/PresetColorGrid.tsx`
- `frontend/src/components/zones/ColorControlPanel.tsx`
- `frontend/src/components/zones/CompactLEDPreview.tsx`
- `frontend/src/components/zones/ZoneDetailPanel.tsx`
- `frontend/src/components/zones/AnimationSelector.tsx`
- `frontend/src/components/zones/AnimationParametersPanel.tsx`
- `frontend/src/components/zones/LEDPreviewRenderer.tsx` (wrapper)

### Modify
- `frontend/src/components/zones/ZoneCard.tsx` - Remove controls, add preview
- `frontend/src/pages/Dashboard.tsx` - Add detail panel modal
- `frontend/src/hooks/useZones.ts` - Add new queries/mutations
- `frontend/src/types/zone.ts` - Add animation-related types
- Backend API - Add animation metadata + WebSocket

### Keep
- `frontend/src/index.css` - Theme (no changes)
- `frontend/tailwind.config.js` - Config (no changes)
- `frontend/src/components/layout/MainLayout.tsx` - Layout (no changes)

---

## 13. Success Criteria

- ✅ Zone cards show live preview strip
- ✅ Zone cards show mode indicator (STATIC/ANIMATION/etc)
- ✅ Zone detail panel opens from card
- ✅ Detail panel shows persistent live preview
- ✅ Color controls in detail panel only
- ✅ Hue picker allows 0-360° selection
- ✅ Preset grid with 20 curated colors
- ✅ Animation selector with 7 types
- ✅ Animation parameters adjust live preview
- ✅ Brightness applies globally
- ✅ All in matrix green theme (#39ff14)
- ✅ Keyboard navigation works
- ✅ Mobile responsive (touch targets 44px+)
- ✅ Accessibility passes WCAG AA
- ✅ 60 FPS smooth animations

---

## 14. Notes for Implementation

### Performance Considerations
- Use `requestAnimationFrame` for preview updates
- Memoize color calculations
- Canvas rendering for LED preview (not SVG)
- Lazy load animation grid items if many
- Debounce slider inputs

### State Management
- Current zone selection in store
- Detail panel open/close state
- Color mode preference (persist to localStorage)
- Recent colors history
- Animation preferences

### Browser Compatibility
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

### Testing
- Unit tests for color conversions (hue ↔ RGB)
- Integration tests for zone updates
- Visual regression tests for preview
- Accessibility audit (axe, WAVE)
- Performance profiling (Lighthouse)

---

**End of Analysis**

---

## Quick Reference: What to Build

```
┌─────────────────────────────────────┐
│ PRODUCTION ZONES UI REDESIGN        │
├─────────────────────────────────────┤
│                                     │
│ KEEP (Working):                     │
│ • Theme system (matrix green)       │
│ • Zone list/cards container         │
│ • API integration pattern           │
│ • Tailwind + shadcn/ui setup       │
│                                     │
│ REMOVE (Move to detail panel):      │
│ • Embedded color picker             │
│ • Editable brightness slider        │
│ • Static color box                  │
│ • Hex color display                 │
│                                     │
│ ADD TO CARD:                        │
│ • Live preview strip (32-48px)      │
│ • Mode indicator (BREATHE, etc)     │
│ • On/off toggle button              │
│ • Read-only brightness indicator    │
│                                     │
│ BUILD NEW PANEL:                    │
│ • Zone detail modal/panel           │
│ • Hue color wheel picker            │
│ • Preset color grid                 │
│ • Animation selector grid           │
│ • Animation parameters              │
│ • Full LED preview (80-120px)       │
│ • Status section (on/off, mode)     │
│ • Navigation (prev/next zone)       │
│                                     │
│ API CHANGES:                        │
│ • Animation metadata endpoint       │
│ • Zone mode + animation fields      │
│ • Parameter structure               │
│ • WebSocket frames (future)         │
│                                     │
└─────────────────────────────────────┘
```

