/**
 * Color Control Panel - Multi-method color selection
 *
 * Provides three color input methods:
 * 1. HueWheelPicker - Canvas-based 360° hue wheel
 * 2. RGBSliderGroup - Individual R/G/B value sliders
 * 3. PresetColorGrid - Quick-select preset colors
 *
 * Features:
 * - Real-time color preview with live LED feedback
 * - Seamless mode switching (HUE ↔ RGB ↔ PRESET)
 * - Color format conversion
 * - Accessibility support (keyboard input for sliders)
 */

import React, { useState, useMemo } from 'react';
import type { Color } from '../../types/index';
import { hueToRGB, rgbToHue, getDefaultPresets } from '../../utils/colors';
import { HueWheelPicker } from './HueWheelPicker';
import { RGBSliderGroup } from './RGBSliderGroup';
import { PresetColorGrid } from './PresetColorGrid';
import styles from './ColorControlPanel.module.css';

interface ColorControlPanelProps {
  color: Color;
  brightness?: number;
  onColorChange: (color: Color) => void;
  onBrightnessChange?: (brightness: number) => void;
  compact?: boolean;
}

type ColorMode = 'HUE' | 'RGB' | 'PRESET';

/**
 * ColorControlPanel Component
 * Complete color selection interface with multiple input methods
 */
export const ColorControlPanel: React.FC<ColorControlPanelProps> = ({
  color,
  brightness = 100,
  onColorChange,
  onBrightnessChange,
  compact = false,
}) => {
  const [activeMode, setActiveMode] = useState<ColorMode>(color.mode as ColorMode);
  const presets = getDefaultPresets();

  // Derive RGB from current color
  const currentRGB = useMemo((): [number, number, number] => {
    if (color.mode === 'HUE' && color.hue !== undefined) {
      return hueToRGB(color.hue);
    } else if (color.mode === 'RGB' && color.rgb) {
      return color.rgb;
    } else if (color.mode === 'PRESET' && color.preset) {
      const preset = presets.find((p) => p.name === color.preset);
      return preset?.rgb || [255, 255, 255];
    }
    return [255, 255, 255];
  }, [color, presets]);

  // Derive hue from RGB
  const currentHue = useMemo(() => {
    return rgbToHue(currentRGB[0], currentRGB[1], currentRGB[2]);
  }, [currentRGB]);

  // Handle hue wheel change
  const handleHueChange = (hue: number) => {
    setActiveMode('HUE');
    onColorChange({ mode: 'HUE', hue });
  };

  // Handle RGB slider change
  const handleRGBChange = (r: number, g: number, b: number) => {
    setActiveMode('RGB');
    onColorChange({ mode: 'RGB', rgb: [r, g, b] });
  };

  // Handle preset selection
  const handlePresetSelect = (presetName: string) => {
    setActiveMode('PRESET');
    onColorChange({ mode: 'PRESET', preset: presetName });
  };

  // Handle brightness change
  const handleBrightnessChange = (value: number) => {
    onBrightnessChange?.(value);
  };

  if (compact) {
    // Compact mode: Just sliders and presets (for small panels)
    return (
      <div className={styles.container}>
        <div className={styles.section}>
          <h4>Color Mode</h4>
          <div className={styles.modeButtons}>
            <button
              className={`${styles.modeButton} ${activeMode === 'HUE' ? styles.active : ''}`}
              onClick={() => setActiveMode('HUE')}
              title="Hue wheel picker (0-360°)"
            >
              🎨 Hue
            </button>
            <button
              className={`${styles.modeButton} ${activeMode === 'RGB' ? styles.active : ''}`}
              onClick={() => setActiveMode('RGB')}
              title="RGB sliders (0-255 each)"
            >
              ⚙️ RGB
            </button>
            <button
              className={`${styles.modeButton} ${activeMode === 'PRESET' ? styles.active : ''}`}
              onClick={() => setActiveMode('PRESET')}
              title="Preset color grid"
            >
              ⭐ Preset
            </button>
          </div>
        </div>

        {activeMode === 'HUE' && (
          <HueWheelPicker hue={currentHue} onChange={handleHueChange} compact />
        )}

        {activeMode === 'RGB' && (
          <RGBSliderGroup rgb={currentRGB} onChange={handleRGBChange} />
        )}

        {activeMode === 'PRESET' && (
          <PresetColorGrid currentPreset={color.preset} onSelect={handlePresetSelect} />
        )}

        {onBrightnessChange && (
          <div className={styles.section}>
            <h4>Brightness</h4>
            <div className={styles.brightnessControl}>
              <input
                type="range"
                min="0"
                max="255"
                value={brightness}
                onChange={(e) => handleBrightnessChange(parseInt(e.target.value, 10))}
                className={styles.slider}
              />
              <span className={styles.value}>{Math.round((brightness / 255) * 100)}%</span>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Full mode: All three pickers with color preview
  return (
    <div className={styles.container}>
      {/* Color Mode Selector */}
      <div className={styles.section}>
        <h3>Color Selection</h3>
        <div className={styles.modeButtons}>
          <button
            className={`${styles.modeButton} ${activeMode === 'HUE' ? styles.active : ''}`}
            onClick={() => setActiveMode('HUE')}
            title="Hue wheel picker (0-360°)"
          >
            🎨 Hue Wheel
          </button>
          <button
            className={`${styles.modeButton} ${activeMode === 'RGB' ? styles.active : ''}`}
            onClick={() => setActiveMode('RGB')}
            title="RGB sliders (0-255 each)"
          >
            ⚙️ RGB Values
          </button>
          <button
            className={`${styles.modeButton} ${activeMode === 'PRESET' ? styles.active : ''}`}
            onClick={() => setActiveMode('PRESET')}
            title="Preset color grid"
          >
            ⭐ Presets
          </button>
        </div>
      </div>

      {/* Color Picker Section */}
      <div className={styles.pickerSection}>
        {activeMode === 'HUE' && (
          <HueWheelPicker hue={currentHue} onChange={handleHueChange} />
        )}

        {activeMode === 'RGB' && (
          <RGBSliderGroup rgb={currentRGB} onChange={handleRGBChange} />
        )}

        {activeMode === 'PRESET' && (
          <PresetColorGrid currentPreset={color.preset} onSelect={handlePresetSelect} />
        )}
      </div>

      {/* Color Preview */}
      <div className={styles.section}>
        <h4>Current Color</h4>
        <div className={styles.previewContainer}>
          <div
            className={styles.colorPreview}
            style={{
              backgroundColor: `rgb(${currentRGB[0]}, ${currentRGB[1]}, ${currentRGB[2]})`,
            }}
          />
          <div className={styles.colorInfo}>
            <p>
              <strong>Hue:</strong> {currentHue.toFixed(0)}°
            </p>
            <p>
              <strong>RGB:</strong> ({currentRGB[0]}, {currentRGB[1]}, {currentRGB[2]})
            </p>
            <p>
              <strong>Mode:</strong> {color.mode}
            </p>
          </div>
        </div>
      </div>

      {/* Brightness Control */}
      {onBrightnessChange && (
        <div className={styles.section}>
          <h4>Brightness</h4>
          <div className={styles.brightnessControl}>
            <input
              type="range"
              min="0"
              max="255"
              value={brightness}
              onChange={(e) => handleBrightnessChange(parseInt(e.target.value, 10))}
              className={styles.slider}
            />
            <span className={styles.value}>{Math.round((brightness / 255) * 100)}%</span>
          </div>
          <div
            className={styles.brightnessPreview}
            style={{
              backgroundColor: `rgba(${currentRGB[0]}, ${currentRGB[1]}, ${currentRGB[2]}, ${brightness / 255})`,
            }}
          />
        </div>
      )}
    </div>
  );
};

export default ColorControlPanel;
