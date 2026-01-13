/**
 * RGB Slider Group - Individual R/G/B value sliders
 *
 * Features:
 * - Three independent sliders (0-255 each)
 * - Live color preview
 * - Numeric input support
 * - Accessibility optimized
 */

import React, { useState } from 'react';
import styles from './ColorControlPanel.module.css';

interface RGBSliderGroupProps {
  rgb: [number, number, number];
  onChange: (r: number, g: number, b: number) => void;
}

/**
 * RGBSliderGroup Component
 * Three sliders for precise RGB color control
 */
export const RGBSliderGroup: React.FC<RGBSliderGroupProps> = ({ rgb, onChange }) => {
  const [inputMode, setInputMode] = useState<'R' | 'G' | 'B' | null>(null);

  const handleSliderChange = (channel: 'R' | 'G' | 'B', value: number) => {
    const newRGB: [number, number, number] = [...rgb];
    const channelIndex = channel === 'R' ? 0 : channel === 'G' ? 1 : 2;
    newRGB[channelIndex] = Math.max(0, Math.min(255, value));
    onChange(newRGB[0], newRGB[1], newRGB[2]);
  };

  const handleInputChange = (channel: 'R' | 'G' | 'B', value: string) => {
    const num = parseInt(value, 10);
    if (!isNaN(num)) {
      handleSliderChange(channel, num);
    }
  };

  const handleInputBlur = () => {
    setInputMode(null);
  };

  const renderSlider = (
    channel: 'R' | 'G' | 'B',
    value: number,
    color: string,
    label: string
  ) => (
    <div key={channel} className={styles.rgbSlider}>
      <div className={styles.rgbHeader}>
        <label>{label}</label>
        {inputMode === channel ? (
          <input
            type="number"
            min="0"
            max="255"
            value={value}
            onChange={(e) => handleInputChange(channel, e.target.value)}
            onBlur={handleInputBlur}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleInputBlur();
            }}
            autoFocus
            className={styles.numericInput}
          />
        ) : (
          <span
            className={styles.rgbValue}
            onClick={() => setInputMode(channel)}
            title="Click to edit"
          >
            {value}
          </span>
        )}
      </div>
      <input
        type="range"
        min="0"
        max="255"
        value={value}
        onChange={(e) => handleSliderChange(channel, parseInt(e.target.value, 10))}
        className={styles.slider}
        style={
          {
            '--slider-color': color,
          } as React.CSSProperties
        }
      />
    </div>
  );

  return (
    <div className={styles.rgbGroup}>
      {renderSlider('R', rgb[0], 'rgba(255, 0, 0, 0.6)', '🔴 Red')}
      {renderSlider('G', rgb[1], 'rgba(0, 255, 0, 0.6)', '🟢 Green')}
      {renderSlider('B', rgb[2], 'rgba(0, 100, 255, 0.6)', '🔵 Blue')}

      {/* Hex value display */}
      <div className={styles.rgbHex}>
        <label>Hex:</label>
        <code>
          #{rgb[0].toString(16).padStart(2, '0').toUpperCase()}
          {rgb[1].toString(16).padStart(2, '0').toUpperCase()}
          {rgb[2].toString(16).padStart(2, '0').toUpperCase()}
        </code>
      </div>
    </div>
  );
};

export default RGBSliderGroup;
