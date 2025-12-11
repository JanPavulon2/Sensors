/**
 * Zone Thumbnail - Mini animated preview of a zone
 *
 * Displays:
 * - Live animation preview matching zone animation mode
 * - Zone name and pixel count
 * - On/off status
 * - Quick brightness indicator
 * - Click to open detail view
 */

import React, { useRef, useEffect, useState } from 'react';
import type { ZoneCombined } from '../../types/index';
import { hueToRGB, getDefaultPresets } from '../../utils/colors';
import styles from './ZonesDashboard.module.css';

type RGBColor = [number, number, number];

interface ZoneThumbnailProps {
  zone: ZoneCombined;
  isSelected?: boolean;
  onClick?: () => void;
}

/**
 * ZoneThumbnail Component
 * Compact animated preview of a zone with live animation effects
 */
export const ZoneThumbnail: React.FC<ZoneThumbnailProps> = ({
  zone,
  isSelected = false,
  onClick,
}) => {
  const timeRef = useRef<number>(0);
  const [ledColors, setLedColors] = useState<RGBColor[]>([]);

  // Get zone color RGB
  const getColorRGB = (): RGBColor => {
    const presets = getDefaultPresets();

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

  // Calculate LED color for current frame
  const calculateLedColor = (time: number): RGBColor => {
    const rgb = getColorRGB();
    let brightness = zone.brightness || 100;

    // Apply animation effects
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

      const color = calculateLedColor(timeRef.current);
      setLedColors(Array.from({ length: zone.pixelCount }, () => color));

      animationId = requestAnimationFrame(animate);
    };

    animationId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationId);
  }, [zone]);

  return (
    <div className={`${styles.thumbnail} ${isSelected ? styles.selected : ''}`} onClick={onClick}>
      <div className={styles.thumbnailLedStrip}>
        {ledColors.map((color, idx) => (
          <div
            key={idx}
            className={styles.thumbnailLedPixel}
            style={{
              backgroundColor: `rgb(${color[0]}, ${color[1]}, ${color[2]})`,
              boxShadow: `0 0 4px rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.6)`,
            }}
          />
        ))}
      </div>
      <div className={styles.info}>
        <h4 className={styles.name}>{zone.displayName}</h4>
        <p className={styles.meta}>
          {zone.pixelCount}px • {zone.mode}
          {zone.enabled === false && ' • OFF'}
        </p>
      </div>
    </div>
  );
};

export default ZoneThumbnail;
