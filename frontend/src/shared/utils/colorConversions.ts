/**
 * Color Conversion and Manipulation Utilities
 * Handles HUE ↔ RGB conversions, hex parsing, brightness calculations
 * Reusable across all zone UI components
 */

export type RGB = [number, number, number];

export interface ColorPreset {
  name: string;
  rgb: RGB;
  category: 'basic' | 'warm' | 'cool' | 'white' | 'natural';
  isWhite?: boolean;
  hex?: string;
}

// ============ Color Conversion ============

/**
 * Convert HSV hue (0-360°) to RGB
 * Assumes full saturation (100%) and full brightness
 */
export function hueToRGB(hue: number): RGB {
  const h = ((hue % 360) + 360) % 360; // Normalize to 0-360
  const hh = h / 60;
  const i = Math.floor(hh);
  const ff = hh - i;

  const c = 255; // Chroma (full saturation)
  const x = c * (1 - ff);
  const y = c * (1 - (1 - ff));

  let r = 0,
    g = 0,
    b = 0;

  switch (i) {
    case 0:
      r = c;
      g = y;
      b = 0;
      break;
    case 1:
      r = x;
      g = c;
      b = 0;
      break;
    case 2:
      r = 0;
      g = c;
      b = y;
      break;
    case 3:
      r = 0;
      g = x;
      b = c;
      break;
    case 4:
      r = y;
      g = 0;
      b = c;
      break;
    case 5:
    default:
      r = c;
      g = 0;
      b = x;
      break;
  }

  return [Math.round(r), Math.round(g), Math.round(b)];
}

/**
 * Convert RGB to HSV hue (0-360°)
 * Returns only the hue component (assumes we work with full saturation)
 */
export function rgbToHue(r: number, g: number, b: number): number {
  const rr = r / 255;
  const gg = g / 255;
  const bb = b / 255;

  const max = Math.max(rr, gg, bb);
  const min = Math.min(rr, gg, bb);
  const delta = max - min;

  let hue = 0;

  if (delta !== 0) {
    if (max === rr) {
      hue = ((gg - bb) / delta) * 60;
    } else if (max === gg) {
      hue = ((bb - rr) / delta) * 60 + 120;
    } else {
      hue = ((rr - gg) / delta) * 60 + 240;
    }
  }

  // Normalize to 0-360
  hue = ((hue % 360) + 360) % 360;

  return Math.round(hue);
}

/**
 * Convert RGB to hexadecimal string
 */
export function rgbToHex(r: number, g: number, b: number): string {
  const toHex = (n: number) => {
    const hex = Math.round(Math.max(0, Math.min(255, n))).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  };

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`.toUpperCase();
}

/**
 * Convert hexadecimal string to RGB
 */
export function hexToRGB(hex: string): RGB | null {
  // Remove '#' if present
  const clean = hex.replace(/^#/, '');

  // Handle 3-digit hex (#FFF → #FFFFFF)
  if (clean.length === 3) {
    const [r, g, b] = clean.split('');
    return [parseInt(r + r, 16), parseInt(g + g, 16), parseInt(b + b, 16)];
  }

  // Handle 6-digit hex
  if (clean.length === 6) {
    return [parseInt(clean.slice(0, 2), 16), parseInt(clean.slice(2, 4), 16), parseInt(clean.slice(4, 6), 16)];
  }

  return null;
}

/**
 * Clamp RGB values to valid range (0-255)
 */
export function clampRGB(r: number, g: number, b: number): RGB {
  return [
    Math.max(0, Math.min(255, Math.round(r))),
    Math.max(0, Math.min(255, Math.round(g))),
    Math.max(0, Math.min(255, Math.round(b))),
  ];
}

/**
 * Clamp hue to valid range (0-360)
 */
export function clampHue(hue: number): number {
  return ((hue % 360) + 360) % 360;
}

// ============ Color Brightness ============

/**
 * Apply brightness factor to RGB color (0-1 range)
 */
export function applyBrightness(rgb: RGB, brightness: number): RGB {
  const factor = Math.max(0, Math.min(1, brightness));
  return [Math.round(rgb[0] * factor), Math.round(rgb[1] * factor), Math.round(rgb[2] * factor)];
}

// ============ Color Space Conversion ============

/**
 * Convert RGB to CSS color string
 */
export function rgbToCSS(r: number, g: number, b: number, alpha?: number): string {
  if (alpha !== undefined) {
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * Parse CSS color string (limited support)
 */
export function parseCSS(color: string): RGB | null {
  // Handle rgb()
  const rgbMatch = color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (rgbMatch) {
    return [parseInt(rgbMatch[1]), parseInt(rgbMatch[2]), parseInt(rgbMatch[3])];
  }

  // Handle #FFFFFF
  return hexToRGB(color);
}

// ============ Color Preset Management ============

const DEFAULT_PRESETS: ColorPreset[] = [
  // Basic colors
  { name: 'red', rgb: [255, 0, 0], category: 'basic' },
  { name: 'green', rgb: [0, 255, 0], category: 'basic' },
  { name: 'blue', rgb: [0, 0, 255], category: 'basic' },
  { name: 'yellow', rgb: [255, 255, 0], category: 'basic' },
  { name: 'cyan', rgb: [0, 255, 255], category: 'basic' },
  { name: 'magenta', rgb: [255, 0, 255], category: 'basic' },

  // Warm tones
  { name: 'orange', rgb: [255, 165, 0], category: 'warm' },
  { name: 'amber', rgb: [255, 191, 0], category: 'warm' },
  { name: 'pink', rgb: [255, 192, 203], category: 'warm' },
  { name: 'hot_pink', rgb: [255, 105, 180], category: 'warm' },

  // Cool tones
  { name: 'purple', rgb: [128, 0, 128], category: 'cool' },
  { name: 'violet', rgb: [238, 130, 238], category: 'cool' },
  { name: 'indigo', rgb: [75, 0, 130], category: 'cool' },

  // Natural tones
  { name: 'mint', rgb: [98, 255, 157], category: 'natural' },
  { name: 'lime', rgb: [50, 205, 50], category: 'natural' },
  { name: 'sky_blue', rgb: [135, 206, 235], category: 'natural' },
  { name: 'ocean', rgb: [0, 119, 182], category: 'natural' },

  // Whites
  { name: 'warm_white', rgb: [255, 165, 0], category: 'white', isWhite: true },
  { name: 'white', rgb: [255, 255, 255], category: 'white', isWhite: true },
  { name: 'cool_white', rgb: [200, 220, 255], category: 'white', isWhite: true },
];

/**
 * Get all default color presets
 */
export function getDefaultPresets(): ColorPreset[] {
  return DEFAULT_PRESETS.map((p) => ({
    ...p,
    hex: rgbToHex(p.rgb[0], p.rgb[1], p.rgb[2]),
  }));
}

/**
 * Get preset by name
 */
export function getPresetByName(name: string): ColorPreset | undefined {
  return getDefaultPresets().find((p) => p.name === name);
}

/**
 * Get presets by category
 */
export function getPresetsByCategory(category: ColorPreset['category']): ColorPreset[] {
  return getDefaultPresets().filter((p) => p.category === category);
}

/**
 * Get all preset categories
 */
export function getPresetCategories(): Array<ColorPreset['category']> {
  const categories = new Set<ColorPreset['category']>();
  getDefaultPresets().forEach((p) => categories.add(p.category));
  return Array.from(categories) as Array<ColorPreset['category']>;
}

/**
 * Get presets in cycling order
 */
export function getPresetsInCycleOrder(): ColorPreset[] {
  const cycleOrder = [
    'red',
    'orange',
    'amber',
    'yellow',
    'lime',
    'green',
    'mint',
    'cyan',
    'sky_blue',
    'ocean',
    'blue',
    'indigo',
    'violet',
    'purple',
    'magenta',
    'hot_pink',
    'pink',
    'warm_white',
    'white',
    'cool_white',
  ];

  return cycleOrder
    .map((name) => getPresetByName(name))
    .filter((p) => p !== undefined) as ColorPreset[];
}

/**
 * Get preset at index (for cycling)
 */
export function getPresetByIndex(index: number): ColorPreset | undefined {
  const presets = getPresetsInCycleOrder();
  return presets[index % presets.length];
}

/**
 * Get next preset in cycle order
 */
export function getNextPreset(currentName: string): ColorPreset | undefined {
  const presets = getPresetsInCycleOrder();
  const currentIndex = presets.findIndex((p) => p.name === currentName);
  return presets[(currentIndex + 1) % presets.length];
}

/**
 * Get previous preset in cycle order
 */
export function getPreviousPreset(currentName: string): ColorPreset | undefined {
  const presets = getPresetsInCycleOrder();
  const currentIndex = presets.findIndex((p) => p.name === currentName);
  return presets[(currentIndex - 1 + presets.length) % presets.length];
}

/**
 * Check if color is valid (not black/off)
 */
export function isColorOn(rgb: RGB): boolean {
  return rgb[0] > 0 || rgb[1] > 0 || rgb[2] > 0;
}

/**
 * Check if color is white (used for special handling)
 */
export function isWhitePreset(presetName: string): boolean {
  const preset = getPresetByName(presetName);
  return preset?.isWhite ?? false;
}

/**
 * Check if color is approximately white (high values on all channels)
 */
export function isApproximatelyWhite(rgb: RGB, threshold: number = 200): boolean {
  return rgb[0] >= threshold && rgb[1] >= threshold && rgb[2] >= threshold;
}
