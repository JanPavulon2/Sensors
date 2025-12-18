/**
 * Zone Types
 * Defines all zone-related data structures
 * Constants must match src/models/enums.py in backend
 */

// Color modes (must match ColorMode enum in src/models/enums.py)
export const ColorMode = {
  HUE: 'HUE',
  PRESET: 'PRESET',
  RGB: 'RGB',
} as const;
export type ColorMode = typeof ColorMode[keyof typeof ColorMode];

// Zone render modes (must match ZoneRenderMode enum in src/models/enums.py)
export const ZoneRenderMode = {
  STATIC: 'STATIC',
  ANIMATION: 'ANIMATION',
  OFF: 'OFF',
} as const;
export type ZoneRenderMode = typeof ZoneRenderMode[keyof typeof ZoneRenderMode];

export interface Color {
  mode: ColorMode | 'HSV'; // HSV is converted to HUE internally
  rgb?: [number, number, number];
  hsv?: {
    h: number;
    s: number;
    v: number;
  };
  hue?: number;
  preset_name?: string;
}

export interface ZoneState {
  color: Color;
  brightness: number; // 0-255
  is_on: boolean;
  render_mode: ZoneRenderMode;
  animation_id?: string | null;
}

export interface Zone {
  id: string;
  name: string;
  pixel_count: number;
  state: ZoneState;
  gpio: number;
  layout?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface ZoneUpdateRequest {
  name?: string;
  is_on?: boolean;
  color?: Color;
  brightness?: number;
}
