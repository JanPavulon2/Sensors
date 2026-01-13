/**
 * Animation Control Panel - Animation mode and parameter selection
 *
 * Supports 6 animation types:
 * 1. STATIC - No animation, solid color
 * 2. BREATHE - Smooth brightness pulsing
 * 3. COLOR_FADE - Smooth hue rotation
 * 4. COLOR_CYCLE - Fast hue rotation loop
 * 5. SNAKE - Pixels chase along strip
 * 6. MATRIX - Falling characters (Matrix rain)
 *
 * Features:
 * - Animation type selector
 * - Dynamic parameter sliders per mode
 * - Real-time preview
 * - Enable/disable toggle
 */

import React, { useMemo } from 'react';
import type { AnimationID, AnimationParameters } from '../../types/index';
import styles from './AnimationControlPanel.module.css';

interface AnimationControlPanelProps {
  animationMode: AnimationID;
  parameters: AnimationParameters;
  enabled?: boolean;
  onAnimationChange: (mode: AnimationID) => void;
  onParameterChange: (key: keyof AnimationParameters, value: number | string) => void;
  onEnabledChange?: (enabled: boolean) => void;
}

const ANIMATION_TYPES: { id: AnimationID; label: string; icon: string; description: string }[] = [
  { id: 'STATIC', label: 'Static', icon: '📍', description: 'Solid color, no animation' },
  { id: 'BREATHE', label: 'Breathe', icon: '💨', description: 'Smooth brightness pulsing' },
  { id: 'COLOR_FADE', label: 'Fade', icon: '🌅', description: 'Smooth color transition' },
  { id: 'SNAKE', label: 'Snake', icon: '🐍', description: 'Pixels chase pattern' },
  { id: 'COLOR_SNAKE', label: 'Color Snake', icon: '🐍', description: 'Colored pixels chase pattern' },
];

// Parameter specifications for each animation type
const PARAMETER_SPECS: Record<AnimationID, Array<{ key: keyof AnimationParameters; label: string; min: number; max: number; step: number; unit: string }>> = {
  STATIC: [],
  BREATHE: [
    { key: 'speed', label: 'Speed', min: 1, max: 100, step: 5, unit: 'ms' },
    { key: 'intensity', label: 'Intensity', min: 10, max: 100, step: 5, unit: '%' },
  ],
  COLOR_FADE: [
    { key: 'speed', label: 'Speed', min: 1, max: 100, step: 5, unit: 'ms' },
    { key: 'length', label: 'Length', min: 1, max: 360, step: 10, unit: '°' },
  ],
  COLOR_CYCLE: [
    { key: 'speed', label: 'Speed', min: 1, max: 100, step: 5, unit: 'ms' },
    { key: 'hue_offset', label: 'Hue Offset', min: 0, max: 360, step: 10, unit: '°' },
  ],
  SNAKE: [
    { key: 'speed', label: 'Speed', min: 1, max: 100, step: 5, unit: 'ms' },
    { key: 'length', label: 'Length', min: 1, max: 20, step: 1, unit: 'px' },
    { key: 'intensity', label: 'Tail Fade', min: 0, max: 100, step: 5, unit: '%' },
  ],
  COLOR_SNAKE: [
    { key: 'speed', label: 'Speed', min: 1, max: 100, step: 5, unit: 'ms' },
    { key: 'length', label: 'Length', min: 1, max: 20, step: 1, unit: 'px' },
    { key: 'hue_offset', label: 'Color Offset', min: 0, max: 360, step: 10, unit: '°' },
  ],
  MATRIX: [
    { key: 'speed', label: 'Speed', min: 1, max: 100, step: 5, unit: 'ms' },
    { key: 'intensity', label: 'Density', min: 10, max: 100, step: 5, unit: '%' },
  ],
};

/**
 * AnimationControlPanel Component
 * Complete animation control interface with mode selection and parameters
 */
export const AnimationControlPanel: React.FC<AnimationControlPanelProps> = ({
  animationMode,
  parameters,
  enabled = true,
  onAnimationChange,
  onParameterChange,
  onEnabledChange,
}) => {
  const currentAnimation = ANIMATION_TYPES.find((a) => a.id === animationMode);
  const paramSpecs = PARAMETER_SPECS[animationMode] || [];

  // Group animations by category
  const animationsByCategory = useMemo(() => {
    const basic = ANIMATION_TYPES.filter((a) => ['STATIC', 'BREATHE'].includes(a.id));
    const color = ANIMATION_TYPES.filter((a) => ['COLOR_FADE', 'COLOR_CYCLE'].includes(a.id));
    const advanced = ANIMATION_TYPES.filter((a) => ['SNAKE', 'MATRIX'].includes(a.id));
    return { basic, color, advanced };
  }, []);

  return (
    <div className={styles.container}>
      {/* Header with enable/disable toggle */}
      <div className={styles.header}>
        <h3>Animation</h3>
        {onEnabledChange && (
          <button
            className={`${styles.toggleButton} ${enabled ? styles.enabled : styles.disabled}`}
            onClick={() => onEnabledChange(!enabled)}
            title={enabled ? 'Click to disable' : 'Click to enable'}
          >
            {enabled ? '▶' : '⏸'}
          </button>
        )}
      </div>

      {/* Animation Type Selector */}
      <div className={styles.section}>
        <label className={styles.sectionLabel}>Animation Type</label>

        {/* Basic Animations */}
        <div className={styles.animationGroup}>
          <h5 className={styles.categoryLabel}>Basic</h5>
          <div className={styles.animationButtons}>
            {animationsByCategory.basic.map((anim) => (
              <button
                key={anim.id}
                className={`${styles.animationButton} ${
                  animationMode === anim.id ? styles.active : ''
                }`}
                onClick={() => onAnimationChange(anim.id)}
                title={anim.description}
                disabled={!enabled}
              >
                <span className={styles.animIcon}>{anim.icon}</span>
                <span className={styles.animLabel}>{anim.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Color Animations */}
        <div className={styles.animationGroup}>
          <h5 className={styles.categoryLabel}>Color</h5>
          <div className={styles.animationButtons}>
            {animationsByCategory.color.map((anim) => (
              <button
                key={anim.id}
                className={`${styles.animationButton} ${
                  animationMode === anim.id ? styles.active : ''
                }`}
                onClick={() => onAnimationChange(anim.id)}
                title={anim.description}
                disabled={!enabled}
              >
                <span className={styles.animIcon}>{anim.icon}</span>
                <span className={styles.animLabel}>{anim.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Advanced Animations */}
        <div className={styles.animationGroup}>
          <h5 className={styles.categoryLabel}>Advanced</h5>
          <div className={styles.animationButtons}>
            {animationsByCategory.advanced.map((anim) => (
              <button
                key={anim.id}
                className={`${styles.animationButton} ${
                  animationMode === anim.id ? styles.active : ''
                }`}
                onClick={() => onAnimationChange(anim.id)}
                title={anim.description}
                disabled={!enabled}
              >
                <span className={styles.animIcon}>{anim.icon}</span>
                <span className={styles.animLabel}>{anim.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Animation Description */}
      {currentAnimation && (
        <div className={styles.description}>
          <p>{currentAnimation.description}</p>
        </div>
      )}

      {/* Dynamic Parameters */}
      {paramSpecs.length > 0 && (
        <div className={styles.section}>
          <label className={styles.sectionLabel}>Parameters</label>
          <div className={styles.parameterGroup}>
            {paramSpecs.map((spec) => (
              <div key={spec.key} className={styles.parameter}>
                <div className={styles.parameterHeader}>
                  <label>{spec.label}</label>
                  <span className={styles.parameterValue}>
                    {parameters[spec.key]} {spec.unit}
                  </span>
                </div>
                <input
                  type="range"
                  min={spec.min}
                  max={spec.max}
                  step={spec.step}
                  value={parameters[spec.key] || spec.min}
                  onChange={(e) =>
                    onParameterChange(spec.key, parseInt(e.target.value, 10))
                  }
                  className={styles.slider}
                  disabled={!enabled}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className={styles.infoBox}>
        <p className={styles.infoLabel}>Current Mode:</p>
        <p className={styles.infoValue}>
          {currentAnimation?.icon} {currentAnimation?.label}
        </p>
        {paramSpecs.length > 0 && (
          <>
            <p className={styles.infoLabel}>Parameters:</p>
            <p className={styles.infoValue}>
              {paramSpecs.map((s) => `${s.label}: ${parameters[s.key]}${s.unit}`).join(' • ')}
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default AnimationControlPanel;
