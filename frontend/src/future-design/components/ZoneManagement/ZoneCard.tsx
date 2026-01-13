/**
 * Zone Card - Individual zone display and quick control
 *
 * Displays:
 * - Zone name and pixel count
 * - Color preview and mode
 * - Animation mode
 * - Brightness indicator
 * - Enable/disable toggle
 *
 * Interactions:
 * - Click to select zone
 * - Quick enable/disable toggle
 */

import React from 'react';
import type { ZoneCombined } from '../../types/index';
import { hueToRGB, getDefaultPresets } from '../../utils/colors';
import styles from './ZoneManagement.module.css';

interface ZoneCardProps {
  zone: ZoneCombined;
  isSelected: boolean;
  onSelect: (zoneId: string) => void;
  onToggleEnabled?: (zoneId: string, enabled: boolean) => void;
}

const ANIMATION_EMOJIS: Record<string, string> = {
  STATIC: '📍',
  BREATHE: '💨',
  COLOR_FADE: '🌅',
  COLOR_CYCLE: '🔄',
  SNAKE: '🐍',
  MATRIX: '🟩',
};

/**
 * ZoneCard Component
 * Compact card displaying zone configuration
 */
export const ZoneCard: React.FC<ZoneCardProps> = ({
  zone,
  isSelected,
  onSelect,
  onToggleEnabled,
}) => {
  const presets = getDefaultPresets();

  // Get color for preview
  const getColorRGB = (): [number, number, number] => {
    if (zone.color.mode === 'HUE' && zone.color.hue !== undefined) {
      return hueToRGB(zone.color.hue);
    } else if (zone.color.mode === 'RGB' && zone.color.rgb) {
      return zone.color.rgb;
    } else if (zone.color.mode === 'PRESET' && zone.color.preset) {
      const preset = presets.find((p) => p.name === zone.color.preset);
      return preset?.rgb || [255, 255, 255];
    }
    return [255, 255, 255];
  };

  const colorRGB = getColorRGB();
  const brightness = zone.brightness || 100;
  const brightnessFactor = brightness / 255;

  return (
    <div
      className={`${styles.zoneCard} ${isSelected ? styles.selected : ''}`}
      onClick={() => onSelect(zone.id)}
    >
      {/* Header */}
      <div className={styles.cardHeader}>
        <div className={styles.headerInfo}>
          <h4 className={styles.zoneName}>{zone.displayName}</h4>
          <p className={styles.pixelCount}>{zone.pixelCount} pixels</p>
        </div>

        {/* Enable/Disable Toggle */}
        <button
          className={`${styles.enableToggle} ${zone.enabled !== false ? styles.enabled : styles.disabled}`}
          onClick={(e) => {
            e.stopPropagation();
            onToggleEnabled?.(zone.id, zone.enabled === false);
          }}
          title={zone.enabled !== false ? 'Click to disable' : 'Click to enable'}
        >
          {zone.enabled !== false ? '✓' : '✕'}
        </button>
      </div>

      {/* Color Preview */}
      <div className={styles.colorPreview}>
        <div
          className={styles.colorSwatch}
          style={{
            backgroundColor: `rgb(${Math.round(colorRGB[0] * brightnessFactor)}, ${Math.round(
              colorRGB[1] * brightnessFactor
            )}, ${Math.round(colorRGB[2] * brightnessFactor)})`,
            boxShadow:
              brightness > 0
                ? `0 0 12px rgb(${Math.round(colorRGB[0] * brightnessFactor)}, ${Math.round(
                    colorRGB[1] * brightnessFactor
                  )}, ${Math.round(colorRGB[2] * brightnessFactor)})`
                : 'inset 0 0 4px rgba(0, 0, 0, 0.5)',
          }}
        />
        <div className={styles.colorInfo}>
          <p className={styles.colorMode}>
            {zone.color.mode === 'HUE' && `${zone.color.hue}°`}
            {zone.color.mode === 'RGB' && 'RGB'}
            {zone.color.mode === 'PRESET' && zone.color.preset}
          </p>
          <p className={styles.brightness}>{Math.round((brightness / 255) * 100)}% bright</p>
        </div>
      </div>

      {/* Animation Info */}
      <div className={styles.animationInfo}>
        <span className={styles.animIcon}>{ANIMATION_EMOJIS[zone.mode] || '❓'}</span>
        <span className={styles.animMode}>{zone.mode}</span>
      </div>

      {/* Status Badge */}
      <div className={styles.statusBadge}>
        {zone.enabled === false && <span className={styles.disabledBadge}>Disabled</span>}
        {zone.reversed && <span className={styles.reversedBadge}>Reversed</span>}
      </div>
    </div>
  );
};

export default ZoneCard;
