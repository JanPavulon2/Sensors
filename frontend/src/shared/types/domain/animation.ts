/**
 * Animation Types
 * Defines all animation-related data structures
 */

export interface AnimationParameter {
  name: string;
  type: 'number' | 'color' | 'boolean' | 'select';
  min?: number;
  max?: number;
  default?: unknown;
  options?: string[];
}

export interface Animation {
  id: string;
  name: string;
  description: string;
  category: 'color' | 'motion' | 'effect' | 'interactive';
  parameters: AnimationParameter[];
  preview_url?: string;
}

export interface AnimationInstance {
  animation_id: string;
  zone_id?: string;
  running: boolean;
  parameters: Record<string, unknown>;
}

export interface AnimationStartRequest {
  animation_id: string;
  zone_id?: string;
  parameters?: Record<string, unknown>;
}
