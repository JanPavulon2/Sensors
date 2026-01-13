/**
 * Compact LED Preview - Horizontal LED strip visualization
 *
 * Shows all zone pixels in a compact horizontal strip format
 * Used in Zone Card header for quick visual feedback
 * Updates in real-time to show animation state
 */

import React from 'react';

export type RGB = [number, number, number];

interface CompactLEDPreviewProps {
  pixels: RGB[];
  pixelCount: number;
  animationMode?: string;
  brightness?: number; // 0-255
  className?: string;
}

/**
 * CompactLEDPreview Component
 * Renders a horizontal strip of LEDs with real-time animation
 */
export const CompactLEDPreview: React.FC<CompactLEDPreviewProps> = ({
  pixels,
  pixelCount,
  animationMode = 'STATIC',
  brightness = 100,
  className = '',
}) => {
  // Ensure we have the right number of pixels
  const displayPixels = pixels.slice(0, pixelCount);
  while (displayPixels.length < pixelCount) {
    displayPixels.push([0, 0, 0]);
  }

  // Calculate LED size based on pixel count
  // For small counts, show larger LEDs; for large counts, show smaller LEDs
  const ledSize = Math.max(4, Math.min(12, Math.floor(200 / pixelCount)));
  const gap = Math.max(1, Math.floor(ledSize / 4));

  return (
    <div className={`flex items-center justify-center gap-${gap} p-2 bg-bg-app rounded-md ${className}`}>
      {/* Strip container */}
      <div
        className="flex gap-1 items-center justify-center flex-nowrap"
        style={{
          gap: `${gap}px`,
        }}
      >
        {displayPixels.map((rgb, index) => {
          const [r, g, b] = rgb;
          const hasColor = r > 0 || g > 0 || b > 0;

          return (
            <div
              key={index}
              className="rounded-sm transition-all duration-150"
              style={{
                width: `${ledSize}px`,
                height: `${ledSize}px`,
                backgroundColor: hasColor ? `rgb(${r}, ${g}, ${b})` : 'rgba(128, 128, 128, 0.2)',
                boxShadow: hasColor
                  ? `0 0 ${Math.max(2, ledSize / 2)}px rgba(${r}, ${g}, ${b}, 0.6), inset 0 0 ${ledSize / 2}px rgba(255, 255, 255, 0.2)`
                  : 'inset 0 0 2px rgba(0, 0, 0, 0.5)',
                opacity: brightness / 255,
              }}
              title={`Pixel ${index}: RGB(${r}, ${g}, ${b})`}
            />
          );
        })}
      </div>

      {/* Animation mode label */}
      {animationMode && animationMode !== 'STATIC' && (
        <span className="text-xs font-medium text-accent-primary whitespace-nowrap ml-2">
          {animationMode}
        </span>
      )}
    </div>
  );
};

export default CompactLEDPreview;
