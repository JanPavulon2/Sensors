/**
 * Animation configuration - single source of truth
 *
 * Defines available animations with metadata for UI components.
 * Add new animations here and they become available in
 * AnimationSelector, AnimationCarousel, and AnimationParametersPanel.
 */

export type AnimationID =
  | 'STATIC'
  | 'BREATHE'
  | 'COLOR_FADE'
  | 'COLOR_CYCLE'
  | 'SNAKE'
  | 'COLOR_SNAKE'
  | 'RAINBOW'
  | 'MATRIX';

export interface AnimationDef {
  id: AnimationID;
  name: string;
  icon: string;
  description: string;
  category: 'basic' | 'color' | 'advanced';
}

export const ANIMATIONS: AnimationDef[] = [
  {
    id: 'STATIC',
    name: 'Static',
    icon: '📍',
    description: 'Solid color, no animation',
    category: 'basic',
  },
  {
    id: 'BREATHE',
    name: 'Breathe',
    icon: '💨',
    description: 'Smooth brightness pulsing',
    category: 'basic',
  },
  {
    id: 'COLOR_FADE',
    name: 'Fade',
    icon: '🌅',
    description: 'Smooth hue fade in/out',
    category: 'color',
  },
  {
    id: 'SNAKE',
    name: 'Snake',
    icon: '🐍',
    description: 'Pixels chase pattern',
    category: 'advanced',
  },
  {
    id: 'COLOR_SNAKE',
    name: 'Color Snake',
    icon: '🌈',
    description: 'Rainbow chase pattern',
    category: 'advanced',
  },
  {
    id: 'RAINBOW',
    name: 'Rainbow',
    icon: '🎨',
    description: 'Full spectrum scrolling rainbow',
    category: 'color',
  },
];

interface ParameterDef {
  id: string;
  label: string;
  type: 'range' | 'enum' | 'bool';
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  options?: string[];
  default?: number | string | boolean;
}

export const ANIMATION_PARAMETERS: Record<AnimationID, ParameterDef[]> = {
  STATIC: [],
  BREATHE: [
    { id: 'speed', label: 'Speed', type: 'range', min: 1, max: 100, step: 1, unit: '%', default: 50 },
    { id: 'intensity', label: 'Intensity', type: 'range', min: 0, max: 100, step: 10, unit: '%', default: 50 },
  ],
  COLOR_FADE: [
    { id: 'speed', label: 'Speed', type: 'range', min: 1, max: 100, step: 1, unit: '%', default: 50 },
  ],
  COLOR_CYCLE: [
    { id: 'speed', label: 'Speed', type: 'range', min: 1, max: 100, step: 1, unit: '%', default: 50 },
  ],
  SNAKE: [
    { id: 'speed', label: 'Speed', type: 'range', min: 1, max: 100, step: 1, unit: '%', default: 50 },
    { id: 'length', label: 'Length', type: 'range', min: 1, max: 10, step: 1, unit: 'px', default: 5 },
    { id: 'primary_color_hue', label: 'Color Hue', type: 'range', min: 0, max: 359, step: 10, unit: '°', default: 30 },
  ],
  COLOR_SNAKE: [
    { id: 'speed', label: 'Speed', type: 'range', min: 1, max: 100, step: 1, unit: '%', default: 50 },
    { id: 'length', label: 'Length', type: 'range', min: 3, max: 15, step: 1, unit: 'px', default: 7 },
    { id: 'primary_color_hue', label: 'Color Hue', type: 'range', min: 0, max: 359, step: 10, unit: '°', default: 30 },
  ],
  RAINBOW: [
    { id: 'speed', label: 'Speed', type: 'range', min: 1, max: 100, step: 1, unit: '%', default: 50 },
  ],
  MATRIX: [
    { id: 'speed', label: 'Speed', type: 'range', min: 1, max: 100, step: 1, unit: '%', default: 50 },
  ],
};
