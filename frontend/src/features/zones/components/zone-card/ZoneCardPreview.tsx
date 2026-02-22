/**
 * Zone Card Preview
 * LED strip visualization for zone
 */

import type { ZoneSnapshot } from '@/shared/types/domain/zone';
import { CompactLEDPreview } from '../preview';
import { useOutputFrame } from '@/features/frames/realtime/frames.store';
import { colorToRGB } from '@/shared/utils/colorConvert';

interface ZoneCardPreviewProps {
  zone: ZoneSnapshot;
}

export function ZoneCardPreview({ zone }: ZoneCardPreviewProps) {
  const frame = useOutputFrame();
  const livePixels = frame?.zones[zone.id];

  // Live from output_frame stream; fallback to static single-color fill
  const pixels = livePixels
    ?? Array.from({ length: zone.pixel_count }, () => colorToRGB(zone.color) as [number, number, number]);

  // OLD: static only
  // const rgb = zone.color?.rgb ?? [0, 0, 0];
  // const pixels = Array.from({ length: zone.pixel_count }, () => rgb);

  return (
    <div className="py-3">
      <CompactLEDPreview
        pixels={pixels}
        pixelCount={zone.pixel_count}
        brightness={livePixels ? 100 : zone.brightness}
        animationMode={zone.render_mode}
      />
    </div>
  );
}
