/**
 * Color Control Panel - Multi-method color selection
 *
 * Provides two color input methods:
 * 1. HueColorPicker - Hue-only picker (0-360°)
 * 2. PresetColorGrid - Quick-select preset colors
 *
 * Features:
 * - Mode switching (HUE ↔ PRESET)
 * - Brightness slider
 * - Live color preview
 */

import React, { useState, useMemo } from 'react';
import { Slider } from '@/shared/ui/slider';
import { Button } from '@/shared/ui/button';
import { PresetColorGrid } from './PresetColorGrid';
import { hueToRGB, rgbToHue, getPresetByName } from '@/shared/utils/colorConversions';

export type ColorMode = 'HUE' | 'PRESET';

export interface ColorValue {
  mode: ColorMode;
  hue?: number; // 0-360 for HUE mode
  preset?: string; // preset name for PRESET mode
}

interface ColorControlPanelProps {
  color: ColorValue;
  brightness?: number;
  onColorChange: (color: ColorValue) => void;
  onBrightnessChange?: (brightness: number) => void;
  disabled?: boolean;
}

/**
 * ColorControlPanel Component
 * Complete color selection interface with HUE and PRESET input methods
 */
export const ColorControlPanel: React.FC<ColorControlPanelProps> = ({
  color,
  brightness = 100,
  onColorChange,
  onBrightnessChange,
  disabled = false,
}) => {
  const [activeMode, setActiveMode] = useState<ColorMode>(color.mode || 'HUE');

  // Derive current RGB from color mode
  const currentRGB = useMemo(() => {
    if (activeMode === 'HUE' && color.hue !== undefined) {
      return hueToRGB(color.hue);
    } else if (activeMode === 'PRESET' && color.preset) {
      const preset = getPresetByName(color.preset);
      return preset?.rgb || [255, 255, 255];
    }
    return [255, 255, 255];
  }, [activeMode, color, color.hue, color.preset]);

  // Derive hue from RGB for display
  const currentHue = useMemo(() => {
    return rgbToHue(currentRGB[0], currentRGB[1], currentRGB[2]);
  }, [currentRGB]);

  // Handle hue change
  const handleHueChange = (hue: number) => {
    setActiveMode('HUE');
    onColorChange({ mode: 'HUE', hue });
  };

  // Handle preset selection
  const handlePresetSelect = (presetName: string) => {
    setActiveMode('PRESET');
    onColorChange({ mode: 'PRESET', preset: presetName });
  };

  // Handle brightness change
  const handleBrightnessChange = (value: number[]) => {
    onBrightnessChange?.(value[0]);
  };

  return (
    <div className="space-y-4">
      {/* Color Mode Selector */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-text-primary">Color Mode</h3>
        <div className="flex gap-2">
          <Button
            variant={activeMode === 'HUE' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveMode('HUE')}
            disabled={disabled}
            className="flex-1 text-xs"
            title="Hue picker (0-360°)"
          >
            🎨 Hue
          </Button>
          <Button
            variant={activeMode === 'PRESET' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveMode('PRESET')}
            disabled={disabled}
            className="flex-1 text-xs"
            title="Preset colors"
          >
            ⭐ Preset
          </Button>
        </div>
      </div>

      {/* Color Picker Section */}
      <div className="space-y-3 p-3 bg-bg-panel rounded-md border border-border-default">
        {activeMode === 'HUE' && (
          <div className="space-y-2">
            <Slider
              value={[currentHue]}
              onValueChange={(value) => handleHueChange(value[0])}
              min={0}
              max={360}
              step={1}
              disabled={disabled}
              className="w-full"
            />
            <p className="text-xs text-text-tertiary text-center font-mono">
              Hue: {Math.round(currentHue)}°
            </p>
            <div
              className="h-10 rounded border border-border-default"
              style={{
                background: `hsl(${currentHue}, 100%, 50%)`,
              }}
            />
          </div>
        )}

        {activeMode === 'PRESET' && (
          <PresetColorGrid
            currentPreset={color.preset}
            onSelect={handlePresetSelect}
            disabled={disabled}
          />
        )}
      </div>

      {/* Brightness Control */}
      {onBrightnessChange && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-text-primary">Brightness</label>
            <span className="text-sm font-mono text-accent-primary">
              {Math.round((brightness / 255) * 100)}%
            </span>
          </div>
          <Slider
            value={[brightness]}
            onValueChange={handleBrightnessChange}
            max={255}
            step={1}
            disabled={disabled}
            className="w-full"
          />
          {/* Brightness preview bar */}
          <div
            className="h-6 rounded-sm border border-border-default"
            style={{
              backgroundColor: `rgb(${currentRGB[0]}, ${currentRGB[1]}, ${currentRGB[2]})`,
              opacity: brightness / 255,
              boxShadow:
                brightness > 50
                  ? `inset 0 0 8px rgba(0, 0, 0, 0.3), 0 0 12px rgba(${currentRGB[0]}, ${currentRGB[1]}, ${currentRGB[2]}, 0.5)`
                  : 'inset 0 0 8px rgba(0, 0, 0, 0.3)',
            }}
          />
        </div>
      )}

      {/* Current Color Display */}
      <div className="p-3 bg-bg-elevated rounded-md text-xs space-y-1">
        <p className="text-text-secondary">
          <span className="font-medium">RGB:</span>{' '}
          <span className="font-mono text-text-primary">
            ({currentRGB[0]}, {currentRGB[1]}, {currentRGB[2]})
          </span>
        </p>
        <p className="text-text-secondary">
          <span className="font-medium">Hue:</span>{' '}
          <span className="font-mono text-text-primary">{Math.round(currentHue)}°</span>
        </p>
      </div>
    </div>
  );
};

export default ColorControlPanel;
