/**
 * Zone Edit Panel Preview
 * Sticky large LED preview
 */

import type { Zone } from '@/shared/types/domain/zone';
import { FullLEDPreview } from '../preview';

interface ZoneEditPanelPreviewProps {
  zone: Zone;
}

export function ZoneEditPanelPreview({ zone }: ZoneEditPanelPreviewProps) {
  // Mock pixel data
  const mockPixels = Array(zone.pixel_count)
    .fill(null)
    .map(() => {
      const [r, g, b] = zone.state.color.rgb || [0, 0, 0];
      return [r, g, b] as [number, number, number];
    });

  return (
    <div className="sticky top-[88px] z-10 bg-bg-panel p-4">
      <p className="text-base font-semibold text-text-primary mb-3">Preview</p>
      <FullLEDPreview
        pixels={mockPixels}
        pixelCount={zone.pixel_count}
        brightness={zone.state.brightness || 255}
        animationMode={zone.state.render_mode}
      />
    </div>
  );
}
