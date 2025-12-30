/**
 * Zone Card Preview
 * LED strip visualization for zone
 */

import type { ZoneSnapshot } from '@/shared/types/domain/zone';
import { CompactLEDPreview } from '../preview';

interface ZoneCardPreviewProps {
  zone: ZoneSnapshot;
}

export function ZoneCardPreview({ zone }: ZoneCardPreviewProps) {
  const rgb =
    zone.color?.rgb ?? [0, 0, 0];

  const pixels = Array.from({ length: zone.pixel_count }, () => rgb);


  // Mock pixel data - in real app this would come from zone state
  // const mockPixels = Array(zone.pixel_count)
  //   .fill(null)
  //   .map(() => {
  //     const [r, g, b] = zone.color.rgb || [0, 0, 0];
  //     return [r, g, b] as [number, number, number];
  //   });

  return (
    <div className="py-3">
      <CompactLEDPreview
        pixels={pixels}
        pixelCount={zone.pixel_count}
        brightness={zone.brightness}
        animationMode={zone.render_mode}
      />
    </div>
  );
}
