/**
 * LED Shape Renderer - Renders zones in different shapes
 * Supports: strip (horizontal/vertical), circle, matrix
 */

import React, { useMemo } from 'react';
import type { ShapeConfig } from '../../types/index';
import type { RGBColor } from '../ZonesDashboard/ZoneDetailCard';
import { calculateCirclePositions } from './shapeUtils';

interface LEDShapeRendererProps {
  pixelCount: number;
  ledColors: RGBColor[];
  shapeConfig?: ShapeConfig;
  width?: number;
  height?: number;
  isCompact?: boolean; // for thumbnail view
}

/**
 * Universal LED shape renderer - renders zones in different shapes
 */
export const LEDShapeRenderer: React.FC<LEDShapeRendererProps> = ({
  pixelCount,
  ledColors,
  shapeConfig,
  width = 560,
  height = 80,
  isCompact = false,
}) => {
  // Default to horizontal strip if no shape config provided
  const effectiveShape = shapeConfig?.shape || 'strip';

  // Render different shapes
  if (effectiveShape === 'strip') {
    const orientation =
      shapeConfig && shapeConfig.shape === 'strip' && 'orientation' in shapeConfig
        ? shapeConfig.orientation
        : 'horizontal';

    return (
      <LEDStripRenderer
        pixelCount={pixelCount}
        ledColors={ledColors}
        width={width}
        height={height}
        orientation={orientation}
        isCompact={isCompact}
      />
    );
  } else if (effectiveShape === 'circle') {
    return (
      <LEDCircleRenderer
        pixelCount={pixelCount}
        ledColors={ledColors}
        width={width}
        height={height}
        isCompact={isCompact}
      />
    );
  } else if (effectiveShape === 'matrix') {
    const rows =
      shapeConfig && shapeConfig.shape === 'matrix' && 'rows' in shapeConfig
        ? shapeConfig.rows
        : 2;
    const columns =
      shapeConfig && shapeConfig.shape === 'matrix' && 'columns' in shapeConfig
        ? shapeConfig.columns
        : Math.ceil(pixelCount / rows);

    return (
      <LEDMatrixRenderer
        pixelCount={pixelCount}
        ledColors={ledColors}
        rows={rows}
        columns={columns}
        width={width}
        height={height}
        isCompact={isCompact}
      />
    );
  }

  return null;
};

// ============ Strip Renderer ============

interface LEDStripRendererProps {
  pixelCount: number;
  ledColors: RGBColor[];
  width?: number;
  height?: number;
  orientation: 'horizontal' | 'vertical';
  isCompact?: boolean;
}

export const LEDStripRenderer: React.FC<LEDStripRendererProps> = ({
  ledColors,
  width = 560,
  height = 80,
  orientation = 'horizontal',
  isCompact = false,
}) => {
  const ledDiameter = isCompact ? 8 : 16;
  const gap = isCompact ? 4 : 6;

  const containerStyle: React.CSSProperties =
    orientation === 'horizontal'
      ? {
          width,
          height,
          display: 'flex',
          gap: `${gap}px`,
          padding: `${gap}px`,
          background: 'rgba(10, 14, 20, 0.9)',
          border: '1px solid rgba(0, 255, 0, 0.2)',
          borderRadius: '0.375rem',
          alignItems: 'center',
          justifyContent: isCompact ? 'center' : 'flex-start',
          overflow: isCompact ? 'hidden' : 'auto',
        }
      : {
          width,
          height,
          display: 'flex',
          flexDirection: 'column',
          gap: `${gap}px`,
          padding: `${gap}px`,
          background: 'rgba(10, 14, 20, 0.9)',
          border: '1px solid rgba(0, 255, 0, 0.2)',
          borderRadius: '0.375rem',
          alignItems: 'center',
          justifyContent: isCompact ? 'center' : 'flex-start',
          overflow: isCompact ? 'hidden' : 'auto',
        };

  return (
    <div style={containerStyle}>
      {ledColors.map((color, idx) => (
        <div
          key={idx}
          style={{
            width: `${ledDiameter}px`,
            height: `${ledDiameter}px`,
            borderRadius: '50%',
            backgroundColor: `rgb(${color[0]}, ${color[1]}, ${color[2]})`,
            boxShadow: `0 0 ${isCompact ? 3 : 6}px rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.8), inset 0 0 2px rgba(0, 0, 0, 0.5)`,
            transition: 'background-color 100ms ease-out, box-shadow 100ms ease-out',
            flexShrink: 0,
          }}
        />
      ))}
    </div>
  );
};

// ============ Circle Renderer ============

interface LEDCircleRendererProps {
  pixelCount: number;
  ledColors: RGBColor[];
  width?: number;
  height?: number;
  isCompact?: boolean;
}

export const LEDCircleRenderer: React.FC<LEDCircleRendererProps> = ({
  pixelCount,
  ledColors,
  width = 240,
  height = 240,
  isCompact = false,
}) => {
  // Smaller LEDs for circles to prevent overlap
  const ledDiameter = isCompact ? 6 : 12;
  // Increased padding for large circles with many pixels
  const padding = Math.max(isCompact ? 12 : 24, ledDiameter * 1.5);

  const positions = useMemo(
    () => calculateCirclePositions(pixelCount, width, height, padding),
    [pixelCount, width, height, padding]
  );

  // Fallback color when ledColors is empty (initial render)
  const getColor = (index: number): [number, number, number] => {
    return ledColors[index] || [30, 30, 30]; // Dark gray fallback
  };

  return (
    <div
      style={{
        position: 'relative',
        width,
        height,
        background: 'rgba(10, 14, 20, 0.9)',
        border: '1px solid rgba(0, 255, 0, 0.2)',
        borderRadius: '0.375rem',
      }}
    >
      {positions.map((pos) => {
        const color = getColor(pos.index);
        const glowSize = isCompact ? 3 : 6;
        return (
          <div
            key={pos.index}
            style={{
              position: 'absolute',
              left: `${pos.x}px`,
              top: `${pos.y}px`,
              width: `${ledDiameter}px`,
              height: `${ledDiameter}px`,
              borderRadius: '50%',
              transform: 'translate(-50%, -50%)',
              backgroundColor: `rgb(${color[0]}, ${color[1]}, ${color[2]})`,
              boxShadow: `0 0 ${glowSize}px rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.8), inset 0 0 1px rgba(0, 0, 0, 0.5)`,
              transition: 'background-color 100ms ease-out, box-shadow 100ms ease-out',
            }}
          />
        );
      })}
    </div>
  );
};

// ============ Matrix Renderer ============

interface LEDMatrixRendererProps {
  pixelCount: number;
  ledColors: RGBColor[];
  rows: number;
  columns: number;
  width?: number;
  height?: number;
  isCompact?: boolean;
}

export const LEDMatrixRenderer: React.FC<LEDMatrixRendererProps> = ({
  ledColors,
  rows,
  columns,
  width = 240,
  height = 160,
  isCompact = false,
}) => {
  const gap = isCompact ? 2 : 4;
  const ledDiameter = isCompact ? 6 : 10;

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${columns}, 1fr)`,
        gridTemplateRows: `repeat(${rows}, 1fr)`,
        width,
        height,
        gap: `${gap}px`,
        padding: `${gap}px`,
        background: 'rgba(10, 14, 20, 0.9)',
        border: '1px solid rgba(0, 255, 0, 0.2)',
        borderRadius: '0.375rem',
        placeItems: 'center',
      }}
    >
      {ledColors.map((color, idx) => (
        <div
          key={idx}
          style={{
            width: `${ledDiameter}px`,
            height: `${ledDiameter}px`,
            borderRadius: '50%',
            backgroundColor: `rgb(${color[0]}, ${color[1]}, ${color[2]})`,
            boxShadow: `0 0 ${isCompact ? 3 : 6}px rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.8), inset 0 0 2px rgba(0, 0, 0, 0.5)`,
            transition: 'background-color 100ms ease-out, box-shadow 100ms ease-out',
          }}
        />
      ))}
    </div>
  );
};

export default LEDShapeRenderer;
