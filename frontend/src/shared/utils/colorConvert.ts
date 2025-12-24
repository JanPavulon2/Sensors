/**
 * Color Conversion Utilities
 * Convert between different color formats
 */

import type { Color } from '@/types/zone';

/**
 * Convert Color object to RGB tuple if possible
 */
export function colorToRGB(color: Color): [number, number, number] {
  if (color.rgb) {
    return color.rgb;
  }

  // If we have HSV, convert to RGB
  if (color.hsv) {
    return hsvToRgb(color.hsv.h, color.hsv.s, color.hsv.v);
  }

  // Default to white if unable to determine color
  return [255, 255, 255];
}

/**
 * Convert HSV to RGB
 */
export function hsvToRgb(h: number, s: number, v: number): [number, number, number] {
  // Normalize hue to 0-360 if needed
  const hNorm = h % 360;
  const sNorm = s / 100;
  const vNorm = v / 100;

  const c = vNorm * sNorm;
  const x = c * (1 - Math.abs(((hNorm / 60) % 2) - 1));
  const m = vNorm - c;

  let r = 0;
  let g = 0;
  let b = 0;

  if (hNorm >= 0 && hNorm < 60) {
    [r, g, b] = [c, x, 0];
  } else if (hNorm >= 60 && hNorm < 120) {
    [r, g, b] = [x, c, 0];
  } else if (hNorm >= 120 && hNorm < 180) {
    [r, g, b] = [0, c, x];
  } else if (hNorm >= 180 && hNorm < 240) {
    [r, g, b] = [0, x, c];
  } else if (hNorm >= 240 && hNorm < 300) {
    [r, g, b] = [x, 0, c];
  } else {
    [r, g, b] = [c, 0, x];
  }

  return [
    Math.round((r + m) * 255),
    Math.round((g + m) * 255),
    Math.round((b + m) * 255),
  ];
}

/**
 * Convert RGB to HSV
 */
export function rgbToHsv(r: number, g: number, b: number): { h: number; s: number; v: number } {
  const rNorm = r / 255;
  const gNorm = g / 255;
  const bNorm = b / 255;

  const max = Math.max(rNorm, gNorm, bNorm);
  const min = Math.min(rNorm, gNorm, bNorm);
  const delta = max - min;

  let h = 0;
  let s = 0;
  const v = max;

  if (delta !== 0) {
    s = delta / max;

    if (max === rNorm) {
      h = ((gNorm - bNorm) / delta) % 6;
    } else if (max === gNorm) {
      h = (bNorm - rNorm) / delta + 2;
    } else {
      h = (rNorm - gNorm) / delta + 4;
    }

    h = h * 60;
    if (h < 0) h += 360;
  }

  return {
    h: Math.round(h),
    s: Math.round(s * 100),
    v: Math.round(v * 100),
  };
}

/**
 * Convert RGB to Hex string
 */
export function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map((x) => x.toString(16).padStart(2, '0')).join('')}`.toUpperCase();
}

/**
 * Convert Color object to Hex
 */
export function colorToHex(color: Color): string {
  const [r, g, b] = colorToRGB(color);
  return rgbToHex(r, g, b);
}

/**
 * Convert Hex to RGB tuple
 */
export function hexToRgb(hex: string): [number, number, number] {
  const cleanHex = hex.replace('#', '');

  if (cleanHex.length === 3) {
    // Handle shorthand hex (#RGB)
    const [r, g, b] = cleanHex.split('').map((char) => parseInt(char + char, 16));
    return [r, g, b];
  }

  const r = parseInt(cleanHex.substring(0, 2), 16);
  const g = parseInt(cleanHex.substring(2, 4), 16);
  const b = parseInt(cleanHex.substring(4, 6), 16);

  return [r, g, b];
}

/**
 * Create a Color object from RGB values
 */
export function createRgbColor(r: number, g: number, b: number): Color {
  return {
    mode: 'RGB',
    rgb: [r, g, b],
  };
}

/**
 * Create a Color object from HSV values
 */
export function createHsvColor(h: number, s: number, v: number): Color {
  return {
    mode: 'HSV',
    hsv: { h, s, v },
  };
}

/**
 * Create a Color object from Hue value
 */
export function createHueColor(hue: number): Color {
  return {
    mode: 'HUE',
    hue,
  };
}
