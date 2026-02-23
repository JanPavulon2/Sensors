/**
 * Animation Parameters Panel - Dynamic parameter controls
 *
 * Shows controls for animation-specific parameters
 * Supports: Range sliders, Enum dropdowns, Boolean toggles
 */

import React from 'react';
import { Slider } from '@/shared/ui/slider';
import { Label } from '@/shared/ui/label';
import { ANIMATION_PARAMETERS, type AnimationID } from './animations.config';

/**
 * Convert backend value to display value
 * Handles special cases like intensity (0.0-1.0 → 0-100%)
 */
function toDisplayValue(parameterId: string, value: number | string | boolean): number | string | boolean {
  if (typeof value !== 'number') return value;
  if (parameterId === 'intensity') return value * 100;
  return value;
}

/**
 * Convert display value back to backend value
 * Handles special cases like intensity (0-100% → 0.0-1.0)
 */
function toBackendValue(parameterId: string, value: number | string | boolean): number | string | boolean {
  if (typeof value !== 'number') return value;
  if (parameterId === 'intensity') return value / 100;
  return value;
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
        const rawValue = parameters[paramDef.id] ?? paramDef.default ?? 0;
        const displayValue = toDisplayValue(paramDef.id, rawValue);

        return (
          <div key={paramDef.id} className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium text-text-primary">{paramDef.label}</Label>
              <span className="text-sm font-mono text-accent-primary">
                {typeof displayValue === 'number' ? Math.round(displayValue * 100) / 100 : displayValue}
                {paramDef.unit ? ` ${paramDef.unit}` : ''}
              </span>
            </div>

            {paramDef.type === 'range' && (
              <>
                <Slider
                  value={[typeof displayValue === 'number' ? displayValue : 0]}
                  onValueChange={(value) => {
                    const backendValue = toBackendValue(paramDef.id, value[0]);
                    onParameterChange?.(paramDef.id, backendValue);
                  }}
                  min={paramDef.min ?? 0}
                  max={paramDef.max ?? 100}
                  step={paramDef.step ?? 1}
                  disabled={disabled}
                  className="w-full"
                />
                <div className="text-xs text-text-tertiary flex justify-between">
                  <span>{paramDef.min ?? 0}</span>
                  <span>{paramDef.max ?? 100}</span>
                </div>
              </>
            )}

            {paramDef.type === 'enum' && (
              <select
                value={String(rawValue)}
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
                onClick={() => onParameterChange?.(paramDef.id, !rawValue)}
                disabled={disabled}
                className={`w-full px-3 py-2 rounded border transition-colors text-sm font-medium ${
                  rawValue
                    ? 'bg-accent-primary text-bg-app border-accent-primary'
                    : 'bg-bg-elevated text-text-secondary border-border-default hover:border-accent-primary'
                }`}
              >
                {rawValue ? '✓ Enabled' : '✕ Disabled'}
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default AnimationParametersPanel;
