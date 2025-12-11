/**
 * Preset Color Grid - Quick-select color presets
 *
 * Features:
 * - Grid of 20 curated color presets
 * - Organized by color category
 * - Visual preview with glow effect
 * - Click to select
 * - Category labels
 */

import React from 'react';
import { getDefaultPresets } from '../../utils/colors';
import styles from './ColorControlPanel.module.css';

interface PresetColorGridProps {
  currentPreset?: string;
  onSelect: (presetName: string) => void;
}

/**
 * PresetColorGrid Component
 * Grid layout of 20 preset colors organized by category
 */
export const PresetColorGrid: React.FC<PresetColorGridProps> = ({ currentPreset, onSelect }) => {
  const presets = getDefaultPresets();

  // Group presets by category
  const categories = Array.from(new Set(presets.map((p) => p.category)));

  return (
    <div className={styles.presetGrid}>
      {categories.map((category) => {
        const categoryPresets = presets.filter((p) => p.category === category);
        return (
          <div key={category} className={styles.presetCategory}>
            <h5 className={styles.categoryLabel}>{category}</h5>
            <div className={styles.presetRow}>
              {categoryPresets.map((preset) => (
                <button
                  key={preset.name}
                  className={`${styles.presetButton} ${
                    currentPreset === preset.name ? styles.selected : ''
                  }`}
                  style={{
                    backgroundColor: preset.hex,
                    boxShadow:
                      currentPreset === preset.name
                        ? `0 0 0 3px rgba(0, 255, 0, 0.6), 0 0 12px ${preset.hex}`
                        : `0 0 8px ${preset.hex}40`,
                  }}
                  onClick={() => onSelect(preset.name)}
                  title={`${preset.name} - RGB(${preset.rgb[0]}, ${preset.rgb[1]}, ${preset.rgb[2]})`}
                  aria-label={`Select ${preset.name} color`}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default PresetColorGrid;
