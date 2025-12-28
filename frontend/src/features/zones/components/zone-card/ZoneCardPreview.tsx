/**
 * Zone Card Preview
 * LED strip visualization for zone
 */

import type { Zone } from '@/shared/types/domain/zone';
import { CompactLEDPreview } from '../preview';

interface ZoneCardPreviewProps {
  zone: Zone;
}

export function ZoneCardPreview({ zone }: ZoneCardPreviewProps) {
  // Mock pixel data - in real app this would come from zone state
  const mockPixels = Array(zone.pixel_count)
    .fill(null)
    .map(() => {
      const [r, g, b] = zone.state.color.rgb || [0, 0, 0];
      return [r, g, b] as [number, number, number];
    });

  return (
    <div className="py-3">
      <CompactLEDPreview
        pixels={mockPixels}
        pixelCount={zone.pixel_count}
        brightness={zone.state.brightness || 100}
        animationMode={zone.state.render_mode}
      />
    </div>
  );
}
