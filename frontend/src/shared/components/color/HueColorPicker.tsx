/**
 * Hue Color Picker
 * Canvas-based fancy hue wheel for color selection
 */

import { HueWheelPicker } from './HueWheelPicker';
import { hueToRGB } from '@/shared/utils/colorConversions';
import { useMemo } from 'react';

interface HueColorPickerProps {
  /** Current hue value (0-360) */
  value: number;
  /** Callback when hue changes */
  onChange: (hue: number) => void;
  /** Disable the picker */
  disabled?: boolean;
}

/**
 * HueColorPicker Component
 * Canvas-based hue wheel with live preview
 */
export function HueColorPicker({
  value,
  onChange,
  disabled = false,
}: HueColorPickerProps) {
  // Convert hue to RGB for preview display
  const currentRGB = useMemo(() => {
    return hueToRGB(value);
  }, [value]);

  return (
    <div className="space-y-4">
      <HueWheelPicker hue={value} onChange={onChange} compact={false} />

      {/* Color Preview */}
      <div className="flex items-center gap-3">
        <div
          className="w-12 h-12 rounded border border-border-default transition-colors"
          style={{ backgroundColor: `rgb(${currentRGB[0]}, ${currentRGB[1]}, ${currentRGB[2]})` }}
        />
        <div>
          <div className="text-sm font-medium text-text-primary">{Math.round(value)}°</div>
          <div className="text-xs text-text-secondary">
            RGB({currentRGB[0]}, {currentRGB[1]}, {currentRGB[2]})
          </div>
        </div>
      </div>
    </div>
  );
}
