/**
 * Compact LED Preview - Horizontal LED strip visualization
 *
 * Shows all zone pixels in a compact horizontal strip format
 * Used in Zone Card header for quick visual feedback
 * Updates in real-time to show animation state
 */

import React from 'react';
import { usePreviewSettingsStore } from '@/features/zones/stores/previewSettingsStore';

export type RGB = [number, number, number];

interface CompactLEDPreviewProps {
  pixels: RGB[];
  pixelCount: number;
  animationMode?: string;
  brightness?: number; // 0-255
  className?: string;
  useSettings?: boolean; // Use stored preview settings if true
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
  useSettings = false,
}) => {
  const previewSettings = usePreviewSettingsStore((state) => state.settings);

  // Ensure we have the right number of pixels
  const displayPixels = pixels.slice(0, pixelCount);
  while (displayPixels.length < pixelCount) {
    displayPixels.push([0, 0, 0]);
  }

  // Use stored settings or calculate defaults
  const ledSize = useSettings ? previewSettings.size : Math.max(4, Math.min(12, Math.floor(200 / pixelCount)));
  const gap = useSettings ? previewSettings.spacing : Math.max(1, Math.floor(ledSize / 4));
  const glowIntensity = useSettings ? previewSettings.glowIntensity / 100 : 1;
  const showGlow = useSettings ? previewSettings.showGlow : true;
  const shape = useSettings ? previewSettings.shape : 'square';

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
                backgroundColor: hasColor ? `rgb(${r}, ${g}, ${b})` : 'rgba(128, 128, 128, 0.2)',
                boxShadow: boxShadowLayers,
                opacity: brightness / 255,
              }}
              title={`Pixel ${index}: RGB(${r}, ${g}, ${b})`}
            />
          );
        })}
      </div>
    </div>
  );
};

export default CompactLEDPreview;
