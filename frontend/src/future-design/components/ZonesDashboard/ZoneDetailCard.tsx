/**
 * Zone Detail Card - Comprehensive zone editor with full controls
 *
 * Displays:
 * - Large animated preview with circular LEDs
 * - On/off toggle (fixed)
 * - Brightness slider with percentage and progressbar
 * - Collapsible sections (Animation, Color, Status)
 * - Navigation arrows
 */

import React, { useRef, useEffect, useState } from 'react';
import type { ZoneCombined, AnimationID } from '../../types/index';
import { hueToRGB, getDefaultPresets } from '../../utils/colors';
import { ColorControlPanel } from '../ColorControl/ColorControlPanel';
import { AnimationControlPanel } from '../AnimationControl/AnimationControlPanel';
import { LEDShapeRenderer } from '../LEDRenderers/LEDShapeRenderer';
import styles from './ZonesDashboard.module.css';

export type RGBColor = [number, number, number];

interface ZoneDetailCardProps {
  zone: ZoneCombined;
  currentIndex: number;
  totalZones: number;
  onUpdate: (zone: ZoneCombined) => void;
  onClose: () => void;
  onPrevZone: () => void;
  onNextZone: () => void;
}

const ANIMATION_NAMES: Record<AnimationID, string> = {
  STATIC: '📍 Static',
  BREATHE: '💨 Breathe',
  COLOR_FADE: '🌅 Fade',
  COLOR_CYCLE: '🔄 Cycle',
  SNAKE: '🐍 Snake',
  COLOR_SNAKE: '🐍 Color Snake',
  MATRIX: '🟩 Matrix',
};

/**
 * ZoneDetailCard Component
 * Full-featured zone editor with live preview and collapsible sections
 */
export const ZoneDetailCard: React.FC<ZoneDetailCardProps> = ({
  zone,
  currentIndex,
  totalZones,
  onUpdate,
  onClose,
  onPrevZone,
  onNextZone,
}) => {
  const timeRef = useRef<number>(0);
  const [ledColors, setLedColors] = useState<RGBColor[]>([]);

  // Collapsible section states
  const [expandedSections, setExpandedSections] = useState({
    animation: false,
    color: true,
    status: false,
  });

  // Toggle section
  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // Calculate LED colors for current animation frame
  const calculateLedColors = (time: number): RGBColor => {
    const presets = getDefaultPresets();
    let rgb: RGBColor;

    if (zone.color.mode === 'HUE' && zone.color.hue !== undefined) {
      rgb = hueToRGB(zone.color.hue);
    } else if (zone.color.mode === 'RGB' && zone.color.rgb) {
      rgb = zone.color.rgb;
    } else if (zone.color.mode === 'PRESET' && zone.color.preset) {
      const preset = presets.find((p) => p.name === zone.color.preset);
      rgb = preset?.rgb || [255, 255, 255];
    } else {
      rgb = [255, 255, 255];
    }

    // Apply animation
    let brightness = zone.brightness || 100;

    if (zone.mode === 'BREATHE') {
      const pulse = Math.sin(time / 300) * 0.5 + 0.5;
      brightness = brightness * (0.3 + pulse * 0.7);
    } else if (zone.mode === 'COLOR_CYCLE') {
      const pulse = Math.sin(time / 500) * 0.3 + 0.7;
      brightness = brightness * pulse;
    } else if (zone.mode === 'SNAKE') {
      const pulse = (Math.sin(time / 250) + 1) * 0.5;
      brightness = brightness * (0.5 + pulse * 0.5);
    } else if (zone.mode === 'COLOR_FADE') {
      const pulse = Math.abs(Math.sin(time / 400));
      brightness = brightness * (0.4 + pulse * 0.6);
    } else if (zone.mode === 'MATRIX') {
      const pulse = Math.random() * 0.5 + 0.5;
      brightness = brightness * pulse;
    }

    const brightnessFactor = brightness / 255;
    return [
      Math.round(rgb[0] * brightnessFactor),
      Math.round(rgb[1] * brightnessFactor),
      Math.round(rgb[2] * brightnessFactor),
    ];
  };

  // Animation loop
  useEffect(() => {
    let animationId: number;
    let lastTime = Date.now();

    const animate = () => {
      const now = Date.now();
      timeRef.current += now - lastTime;
      lastTime = now;

      const color = calculateLedColors(timeRef.current);
      setLedColors(Array.from({ length: zone.pixelCount }, () => color));

      animationId = requestAnimationFrame(animate);
    };

    animationId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationId);
  }, [zone]);

  const handleColorChange = (color: any) => {
    onUpdate({ ...zone, color });
  };

  const handleBrightnessChange = (brightness: number) => {
    onUpdate({ ...zone, brightness });
  };

  const handleAnimationChange = (mode: AnimationID) => {
    onUpdate({ ...zone, mode });
  };

  const handleToggle = () => {
    const newZone = { ...zone, enabled: zone.enabled === false ? true : false };
    onUpdate(newZone);
  };

  const brightnessPercent = Math.round((zone.brightness || 100) / 255 * 100);

  return (
    <div className={styles.detailCard}>
      {/* Header */}
      <div className={styles.cardHeader}>
        <div className={styles.cardTitle}>
          <h2 className={styles.cardName}>{zone.displayName}</h2>
          <p className={styles.cardMeta}>
            {zone.pixelCount} pixels • {ANIMATION_NAMES[zone.mode]}
          </p>
        </div>
        <button className={styles.closeButton} onClick={onClose}>
          ✕
        </button>
      </div>

      {/* Body */}
      <div className={styles.cardBody}>
        {/* Preview */}
        <div className={styles.previewSection}>
          <h4 className={styles.sectionLabel}>Live Preview</h4>
          {(() => {
            // Calculate dimensions based on shape
            const shape = zone.shapeConfig?.shape || 'strip';
            const orientation = zone.shapeConfig?.shape === 'strip' && 'orientation' in zone.shapeConfig
              ? zone.shapeConfig.orientation
              : 'horizontal';
            let width = 560, height = 80;

            if (shape === 'strip' && orientation === 'vertical') {
              // Vertical strips need more height, less width
              width = 100;
              height = 300;
            } else if (shape === 'circle') {
              // Circles need square space
              width = 300;
              height = 300;
            } else if (shape === 'matrix') {
              // Matrices need more space
              width = 320;
              height = 240;
            }
            // Default horizontal strip: 560x80

            return (
              <LEDShapeRenderer
                pixelCount={zone.pixelCount}
                ledColors={ledColors}
                shapeConfig={zone.shapeConfig}
                width={width}
                height={height}
              />
            );
          })()}
        </div>

        {/* Status Section (Collapsible) */}
        <div className={styles.collapsibleSection}>
          <button
            className={styles.sectionHeader}
            onClick={() => toggleSection('status')}
          >
            <span>{expandedSections.status ? '▼' : '▶'} Status</span>
          </button>
          {expandedSections.status && (
            <div className={styles.sectionContent}>
              <div className={styles.controlRow}>
                <label className={styles.controlLabel}>Enable/Disable</label>
                <button
                  className={`${styles.toggleButton} ${
                    zone.enabled !== false ? styles.enabled : ''
                  }`}
                  onClick={handleToggle}
                >
                  {zone.enabled !== false ? '✓ On' : '✕ Off'}
                </button>
              </div>

              <div className={styles.brightnessControl}>
                <label className={styles.controlLabel}>Brightness</label>
                <div className={styles.sliderContainer}>
                  <input
                    type="range"
                    min="0"
                    max="255"
                    value={zone.brightness || 100}
                    onChange={(e) => handleBrightnessChange(parseInt(e.target.value, 10))}
                    className={styles.slider}
                  />
                  <span className={styles.brightnessValue}>{brightnessPercent}%</span>
                </div>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{ width: `${brightnessPercent}%` }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Color Section (Collapsible) */}
        <div className={styles.collapsibleSection}>
          <button
            className={styles.sectionHeader}
            onClick={() => toggleSection('color')}
          >
            <span>{expandedSections.color ? '▼' : '▶'} Color</span>
          </button>
          {expandedSections.color && (
            <div className={styles.sectionContent}>
              <ColorControlPanel
                color={zone.color}
                brightness={zone.brightness || 100}
                onColorChange={handleColorChange}
                onBrightnessChange={handleBrightnessChange}
                compact
              />
            </div>
          )}
        </div>

        {/* Animation Section (Collapsible) */}
        <div className={styles.collapsibleSection}>
          <button
            className={styles.sectionHeader}
            onClick={() => toggleSection('animation')}
          >
            <span>{expandedSections.animation ? '▼' : '▶'} Animation</span>
          </button>
          {expandedSections.animation && (
            <div className={styles.sectionContent}>
              <AnimationControlPanel
                animationMode={zone.mode}
                parameters={{
                  speed: 50,
                  intensity: 50,
                  length: 10,
                  hue_offset: 0,
                }}
                enabled={zone.enabled !== false}
                onAnimationChange={handleAnimationChange}
                onParameterChange={() => {}}
              />
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className={styles.navigation}>
        <button
          className={styles.navButton}
          onClick={onPrevZone}
          disabled={currentIndex === 0}
          title="Previous zone"
        >
          ← Previous
        </button>
        <span className={styles.navCounter}>
          {currentIndex + 1} / {totalZones}
        </span>
        <button
          className={styles.navButton}
          onClick={onNextZone}
          disabled={currentIndex === totalZones - 1}
          title="Next zone"
        >
          Next →
        </button>
      </div>
    </div>
  );
};

export default ZoneDetailCard;
