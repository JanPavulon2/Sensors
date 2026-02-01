import { FullLEDPreview } from '@/features/zones/components/preview/FullLEDPreview';
import { getZoneShape } from '../constants/zone-shapes';
import type { RGB } from '../types/output-frame';

interface Props {
  zoneId: string;
  pixels: RGB[];
  displayName?: string;
}

export function ZoneFrameView({ zoneId, pixels, displayName }: Props) {
  const shape = getZoneShape(zoneId);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between px-2">
        <h3 className="text-sm font-medium">{displayName ?? zoneId}</h3>
        <span className="text-xs text-text-tertiary font-mono">{pixels.length} px</span>
      </div>
      <FullLEDPreview
        pixels={pixels}
        pixelCount={pixels.length}
        shape={shape}
        brightness={100}
        useSettings={true}
      />
    </div>
  );
}
