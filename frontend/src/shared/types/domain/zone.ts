export type { Color } from './color';
import type { AnimationSnapshot } from './animation';

export interface ZoneSnapshot {
  id: string;
  display_name: string;
  pixel_count: number;

  is_on: boolean;
  brightness: number;

  color: {
    mode: 'RGB' | 'HUE' | 'PRESET';
    rgb?: [number, number, number];
    hue?: number;
    preset_name?: string;
  };
  
  render_mode: 'STATIC' | 'ANIMATION';

  animation?: AnimationSnapshot | null;
}