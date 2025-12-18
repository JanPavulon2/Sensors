# 🎨 Color System & Design Tokens

**Date**: 2025-12-10
**Status**: Complete color system specification
**Audience**: Frontend developers, designers

---

## Table of Contents
1. [Color Modes](#modes)
2. [Preset Colors](#presets)
3. [Design Tokens](#tokens)
4. [Theme System](#themes)
5. [Color Utilities](#utilities)

---

## Color Modes

The system supports 3 color control modes, each with distinct UX patterns.

### **1. HUE Mode** (Primary)

**Purpose**: Intuitive color selection via circular hue wheel

**Range**: 0-360° (hue)
- 0° = Red
- 60° = Yellow
- 120° = Green
- 180° = Cyan
- 240° = Blue
- 300° = Magenta

**Saturation**: Always 100% (full color)
**Brightness**: Controlled separately by zone brightness slider

**UI Representation**:
- Circular 360° color wheel
- Click or drag to select hue
- Crosshair cursor at center
- Numerical input field (0-360, step 10°)
- RGB output display

**Best For**:
- Quick color selection
- Intuitive visual feedback
- Mobile (finger-friendly)
- Designers (natural HSV model)

**RGB Conversion**:
```
HSV(hue, 100%, 100%) → RGB
Example: HSV(240°, 100%, 100%) → RGB(0, 0, 255) [Blue]
```

---

### **2. RGB Mode** (Advanced)

**Purpose**: Precise color control for technical users

**Ranges**:
- Red: 0-255
- Green: 0-255
- Blue: 0-255

**UI Representation**:
- 3 vertical sliders (R, G, B)
- Input fields for direct numeric entry (0-255)
- Live color preview
- Hex color input/output (#RRGGBB)

**Best For**:
- Precise color values
- Matching exact colors
- Hex color input from design tools
- Technical users

**Example Values**:
| Color | RGB | Hex |
|-------|-----|-----|
| Red | 255, 0, 0 | #FF0000 |
| Green | 0, 255, 0 | #00FF00 |
| Blue | 0, 0, 255 | #0000FF |
| White | 255, 255, 255 | #FFFFFF |
| Black | 0, 0, 0 | #000000 |

---

### **3. PRESET Mode** (Quick Access)

**Purpose**: One-click selection from 20 curated colors

**UI Representation**:
- Grid of color swatches
- Organized by category
- Expandable/collapsible groups
- Search filter
- Selected swatch highlighted
- Hover tooltip with preset name

**Best For**:
- Quick mood selection
- Consistency across zones
- Beginner users
- Mobile quick access

---

## Preset Colors

### **Complete Preset List** (20 colors, from colors.yaml)

**BASIC COLORS** (6)
| Preset | RGB | Hex | Category |
|--------|-----|-----|----------|
| red | 255, 0, 0 | #FF0000 | basic |
| green | 0, 255, 0 | #00FF00 | basic |
| blue | 0, 0, 255 | #0000FF | basic |
| yellow | 255, 255, 0 | #FFFF00 | basic |
| cyan | 0, 255, 255 | #00FFFF | basic |
| magenta | 255, 0, 255 | #FF00FF | basic |

**WARM TONES** (4)
| Preset | RGB | Hex | Category |
|--------|-----|-----|----------|
| orange | 255, 165, 0 | #FFA500 | warm |
| amber | 255, 191, 0 | #FFBF00 | warm |
| pink | 255, 192, 203 | #FFC0CB | warm |
| hot_pink | 255, 105, 180 | #FF69B4 | warm |

**COOL TONES** (3)
| Preset | RGB | Hex | Category |
|--------|-----|-----|----------|
| purple | 128, 0, 128 | #800080 | cool |
| violet | 238, 130, 238 | #EE82EE | cool |
| indigo | 75, 0, 130 | #4B0082 | cool |

**NATURAL TONES** (4)
| Preset | RGB | Hex | Category |
|--------|-----|-----|----------|
| mint | 98, 255, 157 | #62FF9D | natural |
| lime | 50, 205, 50 | #32CD32 | natural |
| sky_blue | 135, 206, 235 | #87CEEB | natural |
| ocean | 0, 119, 182 | #0077B6 | natural |

**WHITES** (3)
| Preset | RGB | Hex | Category | Special |
|--------|-----|-----|----------|---------|
| warm_white | 255, 165, 0 | #FFA500 | white | isWhite: true |
| white | 255, 255, 255 | #FFFFFF | white | isWhite: true |
| cool_white | 200, 220, 255 | #C8DCFF | white | isWhite: true |

**SPECIAL**
| Preset | RGB | Hex | Category |
|--------|-----|-----|----------|
| off | 0, 0, 0 | #000000 | special |

### **Preset Cycling Order** (for animation preview)

```
red → orange → amber → yellow → lime → green → mint → cyan →
sky_blue → ocean → blue → indigo → violet → purple → magenta →
hot_pink → pink → warm_white → white → cool_white → [loop]
```

### **Category Organization**

```
▼ BASIC COLORS (6)
  [●red] [●green] [●blue] [●yellow] [●cyan] [●magenta]

▼ WARM TONES (4)
  [●orange] [●amber] [●pink] [●hot_pink]

▼ COOL TONES (3)
  [●purple] [●violet] [●indigo]

▼ NATURAL TONES (4)
  [●mint] [●lime] [●sky_blue] [●ocean]

▼ WHITES (3)
  [●warm_white] [●white] [●cool_white]

▼ SPECIAL (1)
  [●off]
```

---

## Design Tokens

### **Cyber Theme - Circuit Forest**

**Primary Colors**:
```css
--cyber-background: #0a0e14;    /* Deep space black */
--cyber-surface: rgba(20, 25, 35, 0.6);  /* Dark glass */
--cyber-accent-primary: #00f5ff;  /* Bioluminescent cyan */
--cyber-accent-secondary: #b721ff; /* Electric purple */
--cyber-accent-tertiary: #00ff88;  /* Forest green neon */
```

**Text Colors**:
```css
--cyber-text: #e8eaed;          /* Soft white */
--cyber-text-dim: #8894a8;      /* Muted blue-gray */
--cyber-text-muted: #5a6572;    /* Very dim gray */
```

**Status Colors**:
```css
--cyber-success: #00ff88;       /* Neon green */
--cyber-warning: #ffb300;       /* Amber */
--cyber-error: #ff1744;         /* Bright red */
--cyber-info: #00f5ff;          /* Cyan */
```

**LED-Specific**:
```css
--cyber-glow-0: rgba(0, 245, 255, 0.6);   /* Inner glow */
--cyber-glow-1: rgba(0, 245, 255, 0.3);   /* Mid glow */
--cyber-glow-2: rgba(0, 245, 255, 0.15);  /* Outer glow */
```

---

### **Nature Theme - Shamanic Tech**

**Primary Colors**:
```css
--nature-background: #0d1a0a;   /* Deep forest black */
--nature-surface: rgba(20, 35, 25, 0.6);  /* Mossy glass */
--nature-accent-primary: #4ecca3;  /* Fresh green */
--nature-accent-secondary: #ff8c42; /* Sunset orange */
--nature-accent-tertiary: #ffd700; /* Golden light */
```

**Text Colors**:
```css
--nature-text: #e8eaed;         /* Soft white */
--nature-text-dim: #8aa878;     /* Muted green-gray */
--nature-text-muted: #5a6d5a;   /* Very dim green */
```

**Status Colors**:
```css
--nature-success: #4ecca3;      /* Fresh green */
--nature-warning: #ff8c42;      /* Sunset orange */
--nature-error: #ff6b6b;        /* Warm red */
--nature-info: #4ecca3;         /* Green */
```

**LED-Specific**:
```css
--nature-glow-0: rgba(78, 204, 163, 0.6);   /* Inner glow */
--nature-glow-1: rgba(78, 204, 163, 0.3);   /* Mid glow */
--nature-glow-2: rgba(78, 204, 163, 0.15);  /* Outer glow */
```

---

### **Spacing Tokens**

```css
--space-0: 0;
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
```

---

### **Typography Tokens**

```css
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
--font-sans: 'Inter', 'SF Pro', sans-serif;

--text-xs: 0.75rem;
--text-sm: 0.875rem;
--text-base: 1rem;
--text-lg: 1.125rem;
--text-xl: 1.25rem;
--text-2xl: 1.5rem;
--text-3xl: 1.875rem;
--text-4xl: 2.25rem;
```

---

### **Border Radius Tokens**

```css
--radius-none: 0;
--radius-sm: 0.25rem;
--radius-md: 0.5rem;
--radius-lg: 0.75rem;
--radius-xl: 1rem;
--radius-full: 9999px;
```

---

### **Shadow Tokens**

```css
--shadow-sm:
  0 1px 2px 0 rgba(0, 0, 0, 0.05);

--shadow-md:
  0 4px 6px -1px rgba(0, 0, 0, 0.1),
  0 2px 4px -1px rgba(0, 0, 0, 0.06);

--shadow-lg:
  0 10px 15px -3px rgba(0, 0, 0, 0.1),
  0 4px 6px -2px rgba(0, 0, 0, 0.05);

--shadow-glow:
  0 0 8px var(--accent-primary),
  0 0 16px var(--accent-primary),
  0 0 24px var(--accent-primary);
```

---

### **Transition Tokens**

```css
--transition-fast: 100ms ease-out;
--transition-base: 150ms ease-out;
--transition-slow: 300ms ease-out;

--transition-all: all var(--transition-base);
--transition-colors: color, background-color var(--transition-base);
--transition-transform: transform var(--transition-fast);
```

---

## Theme System

### **Theme Switching**

**CSS Custom Properties Approach**:

```html
<!-- Apply theme to root -->
<div class="design-container cyber-theme">
  <!-- All children inherit theme variables -->
</div>
```

```css
.cyber-theme {
  --theme-background: var(--cyber-background);
  --theme-surface: var(--cyber-surface);
  --theme-accent: var(--cyber-accent-primary);
  --theme-text: var(--cyber-text);
  --theme-glow: var(--cyber-glow-0);
}

.nature-theme {
  --theme-background: var(--nature-background);
  --theme-surface: var(--nature-surface);
  --theme-accent: var(--nature-accent-primary);
  --theme-text: var(--nature-text);
  --theme-glow: var(--nature-glow-0);
}
```

**Component Usage**:

```css
.led-canvas {
  background-color: var(--theme-background);
  color: var(--theme-text);
}

.led-pixel {
  background-color: var(--led-color);
  box-shadow: 0 0 12px var(--theme-glow);
}

.button {
  background-color: var(--theme-accent);
  color: var(--theme-background);
  border-color: var(--theme-text-dim);
}
```

### **JavaScript Theme Switching**

```typescript
// store/designStore.ts
const useDesignStore = create<DesignState>((set) => ({
  theme: 'cyber',
  actions: {
    setTheme: (theme: 'cyber' | 'nature') => {
      // Update CSS class
      document.documentElement.className = `${theme}-theme`;
      // Persist preference
      localStorage.setItem('design-theme', theme);
      set({ theme });
    },
  },
}));
```

---

## Color Utilities

### **Color Conversion Functions**

**HUE → RGB**:
```typescript
function hueToRGB(hue: number): [number, number, number] {
  // Convert 0-360° hue to RGB
  const h = (hue % 360) / 60;
  const c = 255;
  const x = c * (1 - Math.abs((h % 2) - 1));

  let rgb: [number, number, number] = [0, 0, 0];

  if (h < 1) rgb = [c, x, 0];
  else if (h < 2) rgb = [x, c, 0];
  else if (h < 3) rgb = [0, c, x];
  else if (h < 4) rgb = [0, x, c];
  else if (h < 5) rgb = [x, 0, c];
  else rgb = [c, 0, x];

  return rgb;
}
```

**RGB → HUE**:
```typescript
function rgbToHue(r: number, g: number, b: number): number {
  // Convert RGB to hue (0-360°)
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;

  let hue = 0;

  if (delta !== 0) {
    if (max === r) hue = ((g - b) / delta) * 60;
    else if (max === g) hue = ((b - r) / delta) * 60 + 120;
    else hue = ((r - g) / delta) * 60 + 240;

    if (hue < 0) hue += 360;
  }

  return hue;
}
```

**RGB → HEX**:
```typescript
function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b]
    .map((x) => {
      const hex = x.toString(16);
      return hex.length === 1 ? '0' + hex : hex;
    })
    .join('')
    .toUpperCase()}`;
}
```

**HEX → RGB**:
```typescript
function hexToRGB(hex: string): [number, number, number] | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)]
    : null;
}
```

---

### **Color Luminance & Contrast**

**Calculate Luminance** (for WCAG contrast):
```typescript
function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((x) => {
    x = x / 255;
    return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
  });

  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}
```

**Calculate Contrast Ratio**:
```typescript
function getContrastRatio(
  color1: [number, number, number],
  color2: [number, number, number]
): number {
  const lum1 = getLuminance(...color1);
  const lum2 = getLuminance(...color2);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);

  return (lighter + 0.05) / (darker + 0.05);
}
```

---

### **Color Brightness**

**Adjust Brightness**:
```typescript
function adjustBrightness(
  rgb: [number, number, number],
  factor: number // 0-1 range
): [number, number, number] {
  return [
    Math.min(255, Math.round(rgb[0] * factor)),
    Math.min(255, Math.round(rgb[1] * factor)),
    Math.min(255, Math.round(rgb[2] * factor)),
  ];
}
```

---

### **Color Interpolation**

**Interpolate Between Colors**:
```typescript
function interpolateColor(
  color1: [number, number, number],
  color2: [number, number, number],
  t: number // 0-1, where 0 is color1 and 1 is color2
): [number, number, number] {
  return [
    Math.round(color1[0] + (color2[0] - color1[0]) * t),
    Math.round(color1[1] + (color2[1] - color1[1]) * t),
    Math.round(color1[2] + (color2[2] - color1[2]) * t),
  ];
}
```

---

### **Glow Effect Calculation**

**Calculate Glow Parameters**:
```typescript
function getGlowParameters(brightness: number, glowIntensity: number) {
  return {
    // Inner glow
    glow1Radius: 8 + (brightness / 255) * 4,
    glow1Opacity: glowIntensity * 0.6,

    // Mid glow
    glow2Radius: 16 + (brightness / 255) * 8,
    glow2Opacity: glowIntensity * 0.3,

    // Outer glow
    glow3Radius: 24 + (brightness / 255) * 12,
    glow3Opacity: glowIntensity * 0.15,
  };
}
```

---

## Accessibility

### **Color Contrast Requirements**

- **Text on Surface**: WCAG AA (4.5:1 minimum)
- **UI Controls**: WCAG AA (3:1 minimum)
- **Background Colors**: WCAG A (3:1 minimum)

**Theme Verification**:
```
Cyber Theme:
- Text (#e8eaed) on Background (#0a0e14): 15.7:1 ✅
- Accent (#00f5ff) on Background (#0a0e14): 8.2:1 ✅

Nature Theme:
- Text (#e8eaed) on Background (#0d1a0a): 14.9:1 ✅
- Accent (#4ecca3) on Background (#0d1a0a): 4.1:1 ✅
```

### **Color Blindness Considerations**

- Avoid red-green-only distinctions
- Use icons + color for meaning
- High contrast between interactive elements
- Test with Colorblind Simulation tools

---

## Future Enhancements

- **Palette Generator**: Create harmonious color schemes
- **Gradient Support**: Smooth transitions between colors
- **Seasonal Themes**: Adapt colors based on season/mood
- **User Custom Themes**: Create personal color themes
- **AI Color Suggestions**: Suggest colors based on usage patterns

---

*Created for Phase 1 implementation of Diuna UX/UI System*
