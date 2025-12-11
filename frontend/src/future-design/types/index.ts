/**
 * Type definitions for Future Design UX/UI System
 * Aligned with backend models but tailored for frontend use
 */

// ============ Color System ============

export type ColorMode = 'HUE' | 'RGB' | 'PRESET' | 'PALETTE';
export type RGB = [number, number, number];

export interface Color {
  mode: ColorMode;
  hue?: number; // 0-360 for HUE mode
  rgb?: RGB; // for RGB mode
  preset?: string; // preset name for PRESET mode
  paletteName?: string; // palette name for PALETTE mode
}

export interface ColorPreset {
  name: string;
  rgb: [number, number, number];
  category: 'basic' | 'warm' | 'cool' | 'white' | 'natural';
  isWhite?: boolean;
  hex?: string;
}

// ============ Zone System ============

export type ZoneID = string;

export interface ZoneConfig {
  id: ZoneID;
  displayName: string;
  pixelCount: number;
  enabled: boolean;
  reversed: boolean;
  order: number;
  startIndex: number;
  endIndex: number;
  gpio: number;
}

export interface ZoneState {
  id: ZoneID;
  color: Color;
  brightness: number; // 0-255
  mode: RenderMode;
}

export interface ZoneCombined extends ZoneConfig, ZoneState {
  // Combines config and state
}

// ============ Animation System ============

export const RenderMode = {
  STATIC: 'STATIC',
  BREATHE: 'BREATHE',
  COLOR_FADE: 'COLOR_FADE',
  COLOR_CYCLE: 'COLOR_CYCLE',
  SNAKE: 'SNAKE',
  COLOR_SNAKE: 'COLOR_SNAKE',
  MATRIX: 'MATRIX',
} as const;

export type RenderMode = typeof RenderMode[keyof typeof RenderMode];

export type AnimationID =
  | 'STATIC'
  | 'BREATHE'
  | 'COLOR_FADE'
  | 'COLOR_CYCLE'
  | 'SNAKE'
  | 'COLOR_SNAKE'
  | 'MATRIX';

export const ParamID = {
  ANIM_SPEED: 'ANIM_SPEED',
  ANIM_INTENSITY: 'ANIM_INTENSITY',
  ANIM_LENGTH: 'ANIM_LENGTH',
  ANIM_HUE_OFFSET: 'ANIM_HUE_OFFSET',
  ANIM_PRIMARY_COLOR_HUE: 'ANIM_PRIMARY_COLOR_HUE',
  ANIM_SECONDARY_COLOR_HUE: 'ANIM_SECONDARY_COLOR_HUE',
  ANIM_TERTIARY_COLOR_HUE: 'ANIM_TERTIARY_COLOR_HUE',
} as const;

export type ParamID = typeof ParamID[keyof typeof ParamID];

export interface AnimationParameters {
  speed?: number;
  intensity?: number;
  length?: number;
  hue_offset?: number;
}

export interface AnimationConfig {
  id: AnimationID;
  displayName: string;
  description: string;
  parameters: ParamID[];
  icon?: string;
  enabled?: boolean;
}

export interface AnimationState {
  id: AnimationID;
  parameterValues: Map<ParamID, any>;
}

export interface AnimationPreset {
  id: string;
  name: string;
  description?: string;
  animationId: AnimationID;
  parameters: Record<string, any>;
  createdAt: number;
  updatedAt: number;
}

// ============ UI State ============

export type ThemeType = 'cyber' | 'nature';

export interface DesignState {
  // Theme
  theme: ThemeType;

  // Selection
  selectedZoneId: ZoneID | null;
  selectedAnimation: AnimationID | null;

  // Display
  showAnimationPreview: boolean;
  colorMode: ColorMode;
  currentColor: Color;

  // Data
  zones: Map<ZoneID, ZoneCombined>;
  animationParameters: Map<ParamID, any>;
  animationPresets: AnimationPreset[];

  // Local settings
  showGlowEffect: boolean;
  enableColorBleeding: boolean;
  targetFPS: number;
}

// ============ Canvas Rendering ============

export interface FrameData {
  timestamp: number;
  zones: Record<ZoneID, {
    pixels: [number, number, number][]; // RGB per pixel
    brightness: number; // 0-255
  }>;
}

export interface LEDPixelData {
  color: [number, number, number]; // RGB
  brightness: number; // 0-255
  x: number; // Position on canvas
  y: number;
}

// ============ Component Props ============

export interface LEDCanvasProps {
  zones: Map<ZoneID, ZoneCombined> | ZoneCombined[];
  selectedZoneId?: ZoneID;
  orientation?: 'horizontal' | 'vertical';
  pixelSize?: number;
  gapBetweenZones?: number;
  zoom?: number;
  onZoneSelect?: (zoneId: ZoneID) => void;
  onPixelHover?: (zoneId: ZoneID, pixelIndex: number) => void;
}

export interface ColorControlPanelProps {
  currentColor: Color;
  mode: ColorMode;
  onChange: (color: Color) => void;
  onModeChange: (mode: ColorMode) => void;
}

export interface AnimationControlPanelProps {
  selectedAnimation?: AnimationID;
  parameters: Map<ParamID, any>;
  isPlaying: boolean;
  onAnimationSelect: (animId: AnimationID) => void;
  onParameterChange: (paramId: ParamID, value: any) => void;
  onPlay: () => void;
  onPause: () => void;
  onReset: () => void;
}

export interface ZoneCardProps {
  zone: ZoneCombined;
  isSelected?: boolean;
  isExpanded?: boolean;
  onSelect?: () => void;
  onExpand?: () => void;
  onBrightnessChange?: (brightness: number) => void;
  onModeChange?: (mode: RenderMode) => void;
}

// ============ API Response Types ============

export interface ZoneAPIResponse {
  id: ZoneID;
  name: string;
  pixelCount: number;
  state: {
    color: { mode: string; hue?: number; rgb?: [number, number, number] };
    brightness: number;
    enabled: boolean;
    mode: RenderMode;
  };
  gpio: number;
}

export interface AnimationAPIResponse {
  id: AnimationID;
  displayName: string;
  description: string;
  parameters: string[];
}

// ============ WebSocket Messages ============

export interface WebSocketMessage {
  type: string;
  timestamp?: number;
  data?: any;
}

export interface FrameUpdateMessage extends WebSocketMessage {
  type: 'frame_update';
  zones: Record<ZoneID, {
    pixels: [number, number, number][];
    brightness: number;
  }>;
}

export interface ZoneUpdateMessage extends WebSocketMessage {
  type: 'zone_update';
  zoneId: ZoneID;
  color?: Color;
  brightness?: number;
  mode?: RenderMode;
}

// ============ Utility Types ============

export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;

export interface AsyncState<T> {
  data: Nullable<T>;
  loading: boolean;
  error: Nullable<Error>;
}

export type ThemeVariant = {
  background: string;
  surface: string;
  accentPrimary: string;
  accentSecondary: string;
  accentTertiary: string;
  text: string;
  textDim: string;
  textMuted: string;
};
