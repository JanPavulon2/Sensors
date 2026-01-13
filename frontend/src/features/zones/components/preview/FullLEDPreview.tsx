/**
 * Full LED Preview - Zone-aware LED visualization
 *
 * Renders complete zone visualization with shape support
 * - Strip: Horizontal or vertical line
 * - Circle: Radial arrangement
 * - Matrix: Grid layout
 *
 * Used in Zone Detail Panel for full preview
 */

import React from 'react';
import { usePreviewSettingsStore } from '@/features/zones/stores/previewSettingsStore';

export type RGB = [number, number, number];
export type ZoneShape = 'strip' | 'circle' | 'matrix';

export interface ShapeConfig {
  shape: ZoneShape;
  orientation?: 'horizontal' | 'vertical';
  rows?: number;
  columns?: number;
}

interface FullLEDPreviewProps {
  pixels: RGB[];
  pixelCount: number;
  shape?: ShapeConfig;
  brightness?: number; // 0-255
  animationMode?: string;
  containerHeight?: number; // px, defaults to responsive
  className?: string;
  useSettings?: boolean; // Use stored preview settings if true
}

/**
 * FullLEDPreview Component
 * Renders zone pixels in proper shape format
 */
export const FullLEDPreview: React.FC<FullLEDPreviewProps> = ({
  pixels,
  pixelCount,
  shape = { shape: 'strip', orientation: 'horizontal' },
  brightness = 100,
  containerHeight,
  className = '',
  useSettings = false,
}) => {
  const previewSettings = usePreviewSettingsStore((state) => state.settings);

  // Ensure we have the right number of pixels
  const displayPixels = pixels.slice(0, pixelCount);
  while (displayPixels.length < pixelCount) {
    displayPixels.push([0, 0, 0]);
  }

  const shapeType = shape.shape || 'strip';

  return (
    <div className={`w-full bg-bg-app rounded-lg p-4 ${className}`}>
      {/* Shape-specific rendering */}
      {shapeType === 'strip' && (
        <StripPreview
          pixels={displayPixels}
          orientation={shape.orientation || 'horizontal'}
          brightness={brightness}
          height={containerHeight}
          previewSettings={previewSettings}
        />
      )}

      {shapeType === 'circle' && (
        <CirclePreview
          pixels={displayPixels}
          brightness={brightness}
          diameter={containerHeight}
          previewSettings={previewSettings}
        />
      )}

      {shapeType === 'matrix' && (
        <MatrixPreview
          pixels={displayPixels}
          pixelCount={pixelCount}
          rows={shape.rows || 8}
          columns={shape.columns || 8}
          brightness={brightness}
          previewSettings={previewSettings}
        />
      )}
    </div>
  );
};

/**
 * Strip Preview - Horizontal or vertical line of LEDs
 */
const StripPreview: React.FC<{
  pixels: RGB[];
  orientation: 'horizontal' | 'vertical';
  brightness: number;
  height?: number;
  useSettings?: boolean;
  previewSettings?: any;
}> = ({ pixels, orientation, brightness, height, previewSettings }) => {
  const isHorizontal = orientation === 'horizontal';
  const defaultLedSize = Math.max(6, Math.min(20, Math.floor((isHorizontal ? 400 : 200) / pixels.length)));
  const ledSize = previewSettings?.size ?? defaultLedSize;
  const gap = previewSettings?.spacing ?? 2;
  const glowIntensity = ((previewSettings?.glowIntensity ?? 80) / 100);
  const showGlow = previewSettings?.showGlow !== false; // Always true by default
  const shape = previewSettings?.shape ?? 'square';

  const getShapeClass = (shape: string) => {
    switch (shape) {
      case 'circle':
        return 'rounded-full';
      case 'pill':
        return 'rounded-full';
      default:
        return 'rounded-sm';
    }
  };

  return (
    <div
      className={`flex items-start justify-center ${isHorizontal ? 'flex-row' : 'flex-col'}`}
      style={{
        gap: `${gap}px`,
        overflow: 'visible',
        ...(height ? { height: `${height}px` } : {}),
      }}
    >
      {pixels.map((rgb, index) => {
        const [r, g, b] = rgb;
        const hasColor = r > 0 || g > 0 || b > 0;

        // Multi-layer glow effect
        const outerGlowRadius = ledSize * 1.5;
        const midGlowRadius = ledSize * 0.75;
        const innerGlowRadius = ledSize * 0.3;

        const boxShadowLayers = hasColor
          ? showGlow
            ? [
                `0 0 ${outerGlowRadius}px rgba(${r}, ${g}, ${b}, ${0.8 * glowIntensity})`,
                `0 0 ${midGlowRadius}px rgba(${r}, ${g}, ${b}, ${glowIntensity})`,
                `inset 0 0 ${innerGlowRadius}px rgba(255, 255, 255, 0.4)`,
              ].join(', ')
            : `inset 0 0 ${ledSize / 2}px rgba(255, 255, 255, 0.2)`
          : 'inset 0 0 2px rgba(0, 0, 0, 0.5)';

        return (
          <div
            key={index}
            className={`${getShapeClass(shape)} transition-all duration-150 flex-shrink-0`}
            style={{
              width: `${ledSize}px`,
              height: `${ledSize}px`,
              backgroundColor: hasColor ? `rgb(${r}, ${g}, ${b})` : 'rgba(128, 128, 128, 0.15)',
              boxShadow: boxShadowLayers,
              opacity: brightness / 100,
            }}
            title={`LED ${index}: RGB(${r}, ${g}, ${b})`}
          />
        );
      })}
    </div>
  );
};

/**
 * Circle Preview - Radial arrangement of LEDs
 */
const CirclePreview: React.FC<{
  pixels: RGB[];
  brightness: number;
  diameter?: number;
  useSettings?: boolean;
  previewSettings?: any;
}> = ({ pixels, brightness, diameter = 200, previewSettings }) => {
  const radius = diameter / 2;
  const defaultLedSize = Math.max(8, Math.min(16, diameter / pixels.length));
  const ledSize = previewSettings?.size ?? defaultLedSize;
  const glowIntensity = ((previewSettings?.glowIntensity ?? 80) / 100);
  const showGlow = previewSettings?.showGlow !== false; // Always true by default
  const shape = previewSettings?.shape ?? 'square';

  const getShapeClass = (shape: string) => {
    switch (shape) {
      case 'circle':
        return 'rounded-full';
      case 'pill':
        return 'rounded-full';
      default:
        return 'rounded-sm';
    }
  };

  return (
    <div
      className="relative mx-auto"
      style={{
        width: `${diameter}px`,
        height: `${diameter}px`,
      }}
    >
      {pixels.map((rgb, index) => {
        const angle = (index / pixels.length) * Math.PI * 2 - Math.PI / 2;
        const x = Math.cos(angle) * (radius - ledSize / 2);
        const y = Math.sin(angle) * (radius - ledSize / 2);
        const [r, g, b] = rgb;
        const hasColor = r > 0 || g > 0 || b > 0;

        // Multi-layer glow effect
        const outerGlowRadius = ledSize * 1.5;
        const midGlowRadius = ledSize * 0.75;
        const innerGlowRadius = ledSize * 0.3;

        const boxShadowLayers = hasColor
          ? showGlow
            ? [
                `0 0 ${outerGlowRadius}px rgba(${r}, ${g}, ${b}, ${0.8 * glowIntensity})`,
                `0 0 ${midGlowRadius}px rgba(${r}, ${g}, ${b}, ${glowIntensity})`,
                `inset 0 0 ${innerGlowRadius}px rgba(255, 255, 255, 0.4)`,
              ].join(', ')
            : `inset 0 0 ${ledSize / 2}px rgba(255, 255, 255, 0.2)`
          : 'inset 0 0 2px rgba(0, 0, 0, 0.5)';

        return (
          <div
            key={index}
            className={`absolute ${getShapeClass(shape)} transition-all duration-150`}
            style={{
              width: `${ledSize}px`,
              height: `${ledSize}px`,
              left: `${radius + x - ledSize / 2}px`,
              top: `${radius + y - ledSize / 2}px`,
              backgroundColor: hasColor ? `rgb(${r}, ${g}, ${b})` : 'rgba(128, 128, 128, 0.15)',
              boxShadow: boxShadowLayers,
              opacity: brightness / 100,
            }}
            title={`LED ${index}: RGB(${r}, ${g}, ${b})`}
          />
        );
      })}
    </div>
  );
};

/**
 * Matrix Preview - Grid arrangement of LEDs
 */
const MatrixPreview: React.FC<{
  pixels: RGB[];
  pixelCount: number;
  rows: number;
  columns: number;
  brightness: number;
  useSettings?: boolean;
  previewSettings?: any;
}> = ({ pixels, pixelCount, rows, columns, brightness, previewSettings }) => {
  const defaultLedSize = Math.max(8, Math.min(16, Math.floor(350 / Math.max(rows, columns))));
  const ledSize = previewSettings?.size ?? defaultLedSize;
  const gap = previewSettings?.spacing ?? Math.max(1, Math.floor(defaultLedSize / 3));
  const glowIntensity = ((previewSettings?.glowIntensity ?? 80) / 100);
  const showGlow = previewSettings?.showGlow !== false; // Always true by default
  const shape = previewSettings?.shape ?? 'square';

  const getShapeClass = (shape: string) => {
    switch (shape) {
      case 'circle':
        return 'rounded-full';
      case 'pill':
        return 'rounded-full';
      default:
        return 'rounded-sm';
    }
  };

  return (
    <div
      className="flex items-center justify-center mx-auto"
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${columns}, 1fr)`,
        gap: `${gap}px`,
        width: 'fit-content',
      }}
    >
      {pixels.map((rgb, index) => {
        if (index >= pixelCount) return null;

        const [r, g, b] = rgb;
        const hasColor = r > 0 || g > 0 || b > 0;

        // Multi-layer glow effect
        const outerGlowRadius = ledSize * 1.5;
        const midGlowRadius = ledSize * 0.75;
        const innerGlowRadius = ledSize * 0.3;

        const boxShadowLayers = hasColor
          ? showGlow
            ? [
                `0 0 ${outerGlowRadius}px rgba(${r}, ${g}, ${b}, ${0.8 * glowIntensity})`,
                `0 0 ${midGlowRadius}px rgba(${r}, ${g}, ${b}, ${glowIntensity})`,
                `inset 0 0 ${innerGlowRadius}px rgba(255, 255, 255, 0.4)`,
              ].join(', ')
            : `inset 0 0 ${ledSize / 2}px rgba(255, 255, 255, 0.2)`
          : 'inset 0 0 2px rgba(0, 0, 0, 0.5)';

        return (
          <div
            key={index}
            className={`${getShapeClass(shape)} transition-all duration-150`}
            style={{
              width: `${ledSize}px`,
              height: `${ledSize}px`,
              backgroundColor: hasColor ? `rgb(${r}, ${g}, ${b})` : 'rgba(128, 128, 128, 0.15)',
              boxShadow: boxShadowLayers,
              opacity: brightness / 100,
            }}
            title={`LED ${index}: RGB(${r}, ${g}, ${b})`}
          />
        );
      })}
    </div>
  );
};

export default FullLEDPreview;
