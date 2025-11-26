/**
 * Zone Types
 * Defines all zone-related data structures
 */

export interface Color {
  mode: 'RGB' | 'HSV' | 'HUE' | 'PRESET';
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
  enabled: boolean;
}

export interface Zone {
  id: string;
  name: string;
  pixel_count: number;
  enabled: boolean;
  state: ZoneState;
  layout?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface ZoneUpdateRequest {
  name?: string;
  enabled?: boolean;
  color?: Color;
  brightness?: number;
}
