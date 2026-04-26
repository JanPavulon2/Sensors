import type { ShapeConfig } from '@/features/zones/components/preview/FullLEDPreview';

export const ZONE_SHAPES: Record<string, ShapeConfig> = {
  FLOOR: { shape: 'strip', orientation: 'horizontal' },
  CIRCLE: { shape: 'circle' },
  MATRIX: { shape: 'matrix', rows: 8, columns: 6 },
  PIXEL: { shape: 'strip', orientation: 'horizontal' },
  PIXEL2: { shape: 'strip', orientation: 'horizontal' },
  LAMP: { shape: 'strip', orientation: 'vertical' },
  GATE: { shape: 'strip', orientation: 'horizontal' },
};

export function getZoneShape(zoneId: string): ShapeConfig {
  return ZONE_SHAPES[zoneId] ?? { shape: 'strip', orientation: 'horizontal' };
}
