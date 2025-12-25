/**
 * Animation Parameters Panel - Dynamic parameter controls
 *
 * Shows controls for animation-specific parameters
 * Supports: Range sliders, Enum dropdowns, Boolean toggles
 */

import React from 'react';
import { Slider } from '@/shared/ui/slider';
import { Label } from '@/shared/ui/label';
import type { AnimationID } from './AnimationSelector';

// Parameter specs for each animation
const ANIMATION_PARAMETERS: Record<AnimationID, ParameterDef[]> = {
  STATIC: [],
  BREATHE: [
    {
      id: 'speed',
      label: 'Speed',
      type: 'range',
      min: 100,
      max: 2000,
      step: 100,
      unit: 'ms',
      default: 500,
    },
    {
      id: 'intensity',
      label: 'Intensity',
      type: 'range',
      min: 10,
      max: 100,
      step: 5,
      unit: '%',
      default: 75,
    },
  ],
  COLOR_FADE: [
    {
      id: 'speed',
      label: 'Speed',
      type: 'range',
      min: 100,
      max: 2000,
      step: 100,
      unit: 'ms',
      default: 500,
    },
    {
      id: 'length',
      label: 'Length',
      type: 'range',
      min: 1,
      max: 100,
      step: 1,
      unit: 'px',
      default: 20,
    },
  ],
  COLOR_CYCLE: [
    {
      id: 'speed',
      label: 'Speed',
      type: 'range',
      min: 100,
      max: 2000,
      step: 100,
      unit: 'ms',
      default: 1000,
    },
    {
      id: 'hue_offset',
      label: 'Hue Offset',
      type: 'range',
      min: 0,
      max: 360,
      step: 5,
      unit: '°',
      default: 0,
    },
  ],
  SNAKE: [
    {
      id: 'speed',
      label: 'Speed',
      type: 'range',
      min: 100,
      max: 2000,
      step: 100,
      unit: 'ms',
      default: 500,
    },
    {
      id: 'length',
      label: 'Length',
      type: 'range',
      min: 1,
      max: 50,
      step: 1,
      unit: 'px',
      default: 10,
    },
    {
      id: 'intensity',
      label: 'Intensity',
      type: 'range',
      min: 10,
      max: 100,
      step: 5,
      unit: '%',
      default: 75,
    },
  ],
  COLOR_SNAKE: [
    {
      id: 'speed',
      label: 'Speed',
      type: 'range',
      min: 100,
      max: 2000,
      step: 100,
      unit: 'ms',
      default: 500,
    },
    {
      id: 'length',
      label: 'Length',
      type: 'range',
      min: 1,
      max: 50,
      step: 1,
      unit: 'px',
      default: 10,
    },
    {
      id: 'hue_offset',
      label: 'Hue Offset',
      type: 'range',
      min: 0,
      max: 360,
      step: 5,
      unit: '°',
      default: 0,
    },
  ],
  MATRIX: [
    {
      id: 'speed',
      label: 'Speed',
      type: 'range',
      min: 100,
      max: 2000,
      step: 100,
      unit: 'ms',
      default: 500,
    },
    {
      id: 'intensity',
      label: 'Intensity',
      type: 'range',
      min: 10,
      max: 100,
      step: 5,
      unit: '%',
      default: 75,
    },
  ],
};

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

interface AnimationParametersPanelProps {
  animationId: AnimationID;
  parameters?: Record<string, number | string | boolean>;
  onParameterChange?: (parameterId: string, value: number | string | boolean) => void;
  disabled?: boolean;
}

/**
 * AnimationParametersPanel Component
 * Renders dynamic controls based on animation parameters
 */
export const AnimationParametersPanel: React.FC<AnimationParametersPanelProps> = ({
  animationId,
  parameters = {},
  onParameterChange,
  disabled = false,
}) => {
  const parameterDefs = ANIMATION_PARAMETERS[animationId] || [];

  // If no parameters, show message
  if (parameterDefs.length === 0) {
    return (
      <div className="p-3 bg-bg-elevated rounded-md text-center">
        <p className="text-sm text-text-tertiary italic">No parameters for this animation</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {parameterDefs.map((paramDef) => {
        const currentValue = parameters[paramDef.id] ?? paramDef.default ?? 0;

        return (
          <div key={paramDef.id} className="space-y-2">
            {/* Label */}
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium text-text-primary">{paramDef.label}</Label>
              <span className="text-sm font-mono text-accent-primary">
                {typeof currentValue === 'number' ? Math.round(currentValue * 100) / 100 : currentValue}
                {paramDef.unit ? ` ${paramDef.unit}` : ''}
              </span>
            </div>

            {/* Control */}
            {paramDef.type === 'range' && (
              <>
                <Slider
                  value={[typeof currentValue === 'number' ? currentValue : 0]}
                  onValueChange={(value) => onParameterChange?.(paramDef.id, value[0])}
                  min={paramDef.min ?? 0}
                  max={paramDef.max ?? 100}
                  step={paramDef.step ?? 1}
                  disabled={disabled}
                  className="w-full"
                />
                {/* Range indicator */}
                <div className="text-xs text-text-tertiary flex justify-between">
                  <span>{paramDef.min ?? 0}</span>
                  <span>{paramDef.max ?? 100}</span>
                </div>
              </>
            )}

            {paramDef.type === 'enum' && (
              <select
                value={String(currentValue)}
                onChange={(e) => onParameterChange?.(paramDef.id, e.target.value)}
                disabled={disabled}
                className="w-full px-2 py-2 bg-bg-elevated text-text-primary border border-border-default rounded text-sm"
              >
                {(paramDef.options ?? []).map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            )}

            {paramDef.type === 'bool' && (
              <button
                onClick={() => onParameterChange?.(paramDef.id, !currentValue)}
                disabled={disabled}
                className={`w-full px-3 py-2 rounded border transition-colors text-sm font-medium ${
                  currentValue
                    ? 'bg-accent-primary text-bg-app border-accent-primary'
                    : 'bg-bg-elevated text-text-secondary border-border-default hover:border-accent-primary'
                }`}
              >
                {currentValue ? '✓ Enabled' : '✕ Disabled'}
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default AnimationParametersPanel;
