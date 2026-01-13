/**
 * Color Preset Selector - Quick-select color presets
 *
 * Features:
 * - Grid of curated color presets
 * - Organized by color category
 * - Small square color blocks (28x28px)
 * - Hover effects with scale and glow
 * - Visual selection indicator with border
 * - Keyboard accessible
 */

import React from 'react';
import { Check } from 'lucide-react';
import { getDefaultPresets } from '@/shared/utils/colorConversions';

interface ColorPresetSelectorProps {
  currentPreset?: string;
  onSelect: (presetName: string) => void;
  disabled?: boolean;
}

/**
 * ColorPresetSelector Component
 * Grid layout of preset colors organized by category
 * Each color is a small square block (28x28px) matching future-design styling
 */
export const ColorPresetSelector: React.FC<ColorPresetSelectorProps> = ({
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
    <div className="space-y-3">
      {categories.map((category) => {
        const categoryPresets = presets.filter((p) => p.category === category);
        return (
          <div key={category} className="space-y-2">
            {/* Category Label */}
            <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wider">
              {category}
            </h4>

            {/* Preset Grid - larger blocks with more spacing */}
            <div className="flex flex-wrap gap-3">
              {categoryPresets.map((preset) => {
                const isSelected = currentPreset ? currentPreset.toUpperCase() === preset.name.toUpperCase() : false;
                return (
                  <button
                    key={preset.name}
                    className={`relative rounded-md transition-all duration-200 border-2 flex items-center justify-center hover:scale-110 ${
                      isSelected
                        ? 'border-white/70 opacity-100 scale-110'
                        : 'border-transparent opacity-75 hover:opacity-100'
                    } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
                    style={{
                      backgroundColor: preset.hex,
                      boxShadow: isSelected
                        ? `0 0 0 2px rgba(255, 255, 255, 0.5), 0 0 12px ${preset.hex}, inset 0 0 8px rgba(255, 255, 255, 0.3)`
                        : `0 0 6px ${preset.hex}60`,
                      width: '40px',
                      height: '40px',
                      flexShrink: 0,
                    }}
                    onClick={() => !disabled && onSelect(preset.name)}
                    onKeyDown={(e) => {
                      if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
                        e.preventDefault();
                        onSelect(preset.name);
                      }
                    }}
                    title={`${preset.name}`}
                    aria-label={`Select ${preset.name} color`}
                    aria-pressed={isSelected}
                    disabled={disabled}
                  >
                    {/* Selection Indicator - Checkmark */}
                    {isSelected && (
                      <Check className="absolute w-5 h-5 text-white drop-shadow-lg" strokeWidth={3} />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ColorPresetSelector;
