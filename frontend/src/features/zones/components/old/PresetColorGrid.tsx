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
import { getDefaultPresets } from '@/shared/utils/colorConversions';

interface PresetColorGridProps {
  currentPreset?: string;
  onSelect: (presetName: string) => void;
  disabled?: boolean;
}

/**
 * PresetColorGrid Component
 * Grid layout of 20 preset colors organized by category
 */
export const PresetColorGrid: React.FC<PresetColorGridProps> = ({
  currentPreset,
  onSelect,
  disabled = false,
}) => {
  const presets = getDefaultPresets();

  // Group presets by category, maintaining order
  const categoryOrder: Array<'basic' | 'warm' | 'cool' | 'natural' | 'white'> = [
    'basic',
    'warm',
    'cool',
    'natural',
    'white',
  ];
  const categories = categoryOrder.filter((cat) => presets.some((p) => p.category === cat));

  return (
    <div className="space-y-6">
      {categories.map((category) => {
        const categoryPresets = presets.filter((p) => p.category === category);
        return (
          <div key={category} className="space-y-2">
            {/* Category Label */}
            <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wider">
              {category}
            </h4>

            {/* Preset Row */}
            <div className="grid grid-cols-[repeat(auto-fit,minmax(28px,1fr))] gap-1">
              {categoryPresets.map((preset) => (
                <button
                  key={preset.name}
                  className={`aspect-square w-full h-7 rounded-sm border transition-all duration-200 ${
                    currentPreset === preset.name
                      ? 'border-white/50 scale-110 opacity-100'
                      : 'border-transparent opacity-70 hover:opacity-100 hover:scale-110'
                  } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
                  style={{
                    backgroundColor: preset.hex,
                    boxShadow:
                      currentPreset === preset.name
                        ? `0 0 0 3px rgba(0, 255, 0, 0.6), 0 0 12px ${preset.hex}`
                        : `0 0 8px ${preset.hex}40`,
                  }}
                  onClick={() => !disabled && onSelect(preset.name)}
                  onKeyDown={(e) => {
                    if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault();
                      onSelect(preset.name);
                    }
                  }}
                  title={`${preset.name} - RGB(${preset.rgb[0]}, ${preset.rgb[1]}, ${preset.rgb[2]})`}
                  aria-label={`Select ${preset.name} color`}
                  aria-pressed={currentPreset === preset.name}
                  disabled={disabled}
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
