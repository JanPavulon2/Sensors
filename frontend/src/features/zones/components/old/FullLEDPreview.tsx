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
  animationMode,
  containerHeight = 120,
  className = '',
}) => {
  // Ensure we have the right number of pixels
  const displayPixels = pixels.slice(0, pixelCount);
  while (displayPixels.length < pixelCount) {
    displayPixels.push([0, 0, 0]);
  }

  const shapeType = shape.shape || 'strip';

  return (
    <div className={`w-full bg-bg-app rounded-lg p-4 border border-border-default ${className}`}>
      {/* Shape-specific rendering */}
      {shapeType === 'strip' && (
        <StripPreview
          pixels={displayPixels}
          orientation={shape.orientation || 'horizontal'}
          brightness={brightness}
          height={containerHeight}
        />
      )}

      {shapeType === 'circle' && (
        <CirclePreview pixels={displayPixels} brightness={brightness} diameter={containerHeight} />
      )}

      {shapeType === 'matrix' && (
        <MatrixPreview
          pixels={displayPixels}
          pixelCount={pixelCount}
          rows={shape.rows || 8}
          columns={shape.columns || 8}
          brightness={brightness}
        />
      )}

      {/* Animation mode badge */}
      {animationMode && animationMode !== 'STATIC' && (
        <div className="mt-3 text-center">
          <span className="inline-block px-2 py-1 text-xs font-medium bg-accent-glow text-accent-primary rounded">
            {animationMode}
          </span>
        </div>
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
  height: number;
}> = ({ pixels, orientation, brightness, height }) => {
  const isHorizontal = orientation === 'horizontal';
  const ledSize = Math.max(6, Math.min(20, Math.floor((isHorizontal ? 400 : 200) / pixels.length)));

  return (
    <div
      className={`flex gap-1 items-center justify-center ${isHorizontal ? 'flex-row' : 'flex-col'}`}
      style={{ minHeight: `${height}px` }}
    >
      {pixels.map((rgb, index) => {
        const [r, g, b] = rgb;
        const hasColor = r > 0 || g > 0 || b > 0;

        return (
          <div
            key={index}
            className="rounded-sm transition-all duration-150 flex-shrink-0"
            style={{
              width: `${ledSize}px`,
              height: `${ledSize}px`,
              backgroundColor: hasColor ? `rgb(${r}, ${g}, ${b})` : 'rgba(128, 128, 128, 0.15)',
              boxShadow: hasColor
                ? `0 0 ${Math.max(4, ledSize / 1.5)}px rgba(${r}, ${g}, ${b}, 0.7), inset 0 0 ${ledSize / 2}px rgba(255, 255, 255, 0.2)`
                : 'inset 0 0 2px rgba(0, 0, 0, 0.5)',
              opacity: brightness / 255,
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
const CirclePreview: React.FC<{ pixels: RGB[]; brightness: number; diameter: number }> = ({
  pixels,
  brightness,
  diameter,
}) => {
  const radius = diameter / 2;
  const ledSize = Math.max(8, Math.min(16, diameter / pixels.length));

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

        return (
          <div
            key={index}
            className="absolute rounded-sm transition-all duration-150"
            style={{
              width: `${ledSize}px`,
              height: `${ledSize}px`,
              left: `${radius + x - ledSize / 2}px`,
              top: `${radius + y - ledSize / 2}px`,
              backgroundColor: hasColor ? `rgb(${r}, ${g}, ${b})` : 'rgba(128, 128, 128, 0.15)',
              boxShadow: hasColor
                ? `0 0 ${Math.max(4, ledSize / 1.5)}px rgba(${r}, ${g}, ${b}, 0.7), inset 0 0 ${ledSize / 2}px rgba(255, 255, 255, 0.2)`
                : 'inset 0 0 2px rgba(0, 0, 0, 0.5)',
              opacity: brightness / 255,
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
}> = ({ pixels, pixelCount, rows, columns, brightness }) => {
  const ledSize = Math.max(8, Math.min(16, Math.floor(350 / Math.max(rows, columns))));
  const gap = Math.max(1, Math.floor(ledSize / 3));

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

        return (
          <div
            key={index}
            className="rounded-sm transition-all duration-150"
            style={{
              width: `${ledSize}px`,
              height: `${ledSize}px`,
              backgroundColor: hasColor ? `rgb(${r}, ${g}, ${b})` : 'rgba(128, 128, 128, 0.15)',
              boxShadow: hasColor
                ? `0 0 ${Math.max(4, ledSize / 1.5)}px rgba(${r}, ${g}, ${b}, 0.7), inset 0 0 ${ledSize / 2}px rgba(255, 255, 255, 0.2)`
                : 'inset 0 0 2px rgba(0, 0, 0, 0.5)',
              opacity: brightness / 255,
            }}
            title={`LED ${index}: RGB(${r}, ${g}, ${b})`}
          />
        );
      })}
    </div>
  );
};

export default FullLEDPreview;
