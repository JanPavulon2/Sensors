/**
 * Example Zone Generator
 * Creates demo zones with various shapes and configurations
 * Useful for testing and showcasing shape functionality
 */

import type { ZoneCombined, ShapeConfig } from '../types/index';

export const EXAMPLE_ZONES: ZoneCombined[] = [
  // Horizontal Strip (classic linear layout)
  {
    id: 'demo-strip-h',
    displayName: '📏 Horizontal Strip',
    pixelCount: 60,
    enabled: true,
    reversed: false,
    order: 1,
    startIndex: 0,
    endIndex: 59,
    gpio: 17,
    shapeConfig: {
      shape: 'strip',
      orientation: 'horizontal',
    } as ShapeConfig,
    color: {
      mode: 'HUE',
      hue: 120, // Green
    },
    brightness: 200,
    mode: 'BREATHE',
  },

  // Vertical Strip
  {
    id: 'demo-strip-v',
    displayName: '📐 Vertical Strip',
    pixelCount: 30,
    enabled: true,
    reversed: false,
    order: 2,
    startIndex: 0,
    endIndex: 29,
    gpio: 27,
    shapeConfig: {
      shape: 'strip',
      orientation: 'vertical',
    } as ShapeConfig,
    color: {
      mode: 'HUE',
      hue: 280, // Purple
    },
    brightness: 200,
    mode: 'COLOR_CYCLE',
  },

  // Circle Layout (ring/halo)
  {
    id: 'demo-circle-ring',
    displayName: '⭕ Ring Layout',
    pixelCount: 60,
    enabled: true,
    reversed: false,
    order: 3,
    startIndex: 0,
    endIndex: 59,
    gpio: 22,
    shapeConfig: {
      shape: 'circle',
    } as ShapeConfig,
    color: {
      mode: 'HUE',
      hue: 0, // Red
    },
    brightness: 220,
    mode: 'COLOR_FADE',
  },

  // Small Circle
  {
    id: 'demo-circle-small',
    displayName: '🔴 Small Ring',
    pixelCount: 24,
    enabled: true,
    reversed: false,
    order: 4,
    startIndex: 0,
    endIndex: 23,
    gpio: 23,
    shapeConfig: {
      shape: 'circle',
    } as ShapeConfig,
    color: {
      mode: 'HUE',
      hue: 60, // Yellow
    },
    brightness: 200,
    mode: 'SNAKE',
  },

  // 8x8 Matrix (64 pixels)
  {
    id: 'demo-matrix-8x8',
    displayName: '🎮 8×8 Matrix',
    pixelCount: 64,
    enabled: true,
    reversed: false,
    order: 5,
    startIndex: 0,
    endIndex: 63,
    gpio: 24,
    shapeConfig: {
      shape: 'matrix',
      rows: 8,
      columns: 8,
    } as ShapeConfig,
    color: {
      mode: 'HUE',
      hue: 180, // Cyan
    },
    brightness: 210,
    mode: 'MATRIX',
  },

  // 16x8 Matrix (128 pixels - wide display)
  {
    id: 'demo-matrix-16x8',
    displayName: '📺 16×8 Display',
    pixelCount: 128,
    enabled: true,
    reversed: false,
    order: 6,
    startIndex: 0,
    endIndex: 127,
    gpio: 25,
    shapeConfig: {
      shape: 'matrix',
      rows: 8,
      columns: 16,
    } as ShapeConfig,
    color: {
      mode: 'HUE',
      hue: 320, // Magenta
    },
    brightness: 200,
    mode: 'COLOR_CYCLE',
  },

  // 4x4 Matrix (compact)
  {
    id: 'demo-matrix-4x4',
    displayName: '⬛ 4×4 Grid',
    pixelCount: 16,
    enabled: true,
    reversed: false,
    order: 7,
    startIndex: 0,
    endIndex: 15,
    gpio: 26,
    shapeConfig: {
      shape: 'matrix',
      rows: 4,
      columns: 4,
    } as ShapeConfig,
    color: {
      mode: 'HUE',
      hue: 240, // Blue
    },
    brightness: 220,
    mode: 'BREATHE',
  },

  // 12x12 Matrix (large)
  {
    id: 'demo-matrix-12x12',
    displayName: '🔲 12×12 Panel',
    pixelCount: 144,
    enabled: true,
    reversed: false,
    order: 8,
    startIndex: 0,
    endIndex: 143,
    gpio: 21,
    shapeConfig: {
      shape: 'matrix',
      rows: 12,
      columns: 12,
    } as ShapeConfig,
    color: {
      mode: 'HUE',
      hue: 40, // Orange
    },
    brightness: 200,
    mode: 'COLOR_FADE',
  },

  // 5x5 Matrix (square)
  {
    id: 'demo-matrix-5x5',
    displayName: '⏹️ 5×5 Square',
    pixelCount: 25,
    enabled: true,
    reversed: false,
    order: 9,
    startIndex: 0,
    endIndex: 24,
    gpio: 20,
    shapeConfig: {
      shape: 'matrix',
      rows: 5,
      columns: 5,
    } as ShapeConfig,
    color: {
      mode: 'HUE',
      hue: 150, // Teal
    },
    brightness: 210,
    mode: 'SNAKE',
  },

  // Long Horizontal Strip
  {
    id: 'demo-strip-long',
    displayName: '📊 Long Strip',
    pixelCount: 120,
    enabled: true,
    reversed: false,
    order: 10,
    startIndex: 0,
    endIndex: 119,
    gpio: 19,
    shapeConfig: {
      shape: 'strip',
      orientation: 'horizontal',
    } as ShapeConfig,
    color: {
      mode: 'PRESET',
      preset: 'sunset', // Will use a preset color if available
    },
    brightness: 190,
    mode: 'COLOR_CYCLE',
  },
];

/**
 * Get example zones - useful for demos and testing
 * @param filterShape - optionally filter by shape ('strip', 'circle', 'matrix')
 * @returns array of example zones
 */
export function getExampleZones(filterShape?: string): ZoneCombined[] {
  if (!filterShape) {
    return EXAMPLE_ZONES;
  }

  return EXAMPLE_ZONES.filter((zone) => zone.shapeConfig?.shape === filterShape);
}

/**
 * Get a single example zone by ID
 */
export function getExampleZoneById(id: string): ZoneCombined | undefined {
  return EXAMPLE_ZONES.find((zone) => zone.id === id);
}

/**
 * Get example zones grouped by shape
 */
export function getExampleZonesGrouped(): Record<string, ZoneCombined[]> {
  return {
    strip: getExampleZones('strip'),
    circle: getExampleZones('circle'),
    matrix: getExampleZones('matrix'),
  };
}

/**
 * Statistics about example zones
 */
export function getExampleZonesStats() {
  const grouped = getExampleZonesGrouped();
  return {
    total: EXAMPLE_ZONES.length,
    strip: grouped.strip.length,
    circle: grouped.circle.length,
    matrix: grouped.matrix.length,
    totalPixels: EXAMPLE_ZONES.reduce((sum, z) => sum + z.pixelCount, 0),
  };
}
