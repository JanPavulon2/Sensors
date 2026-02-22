/**
 * Zone Edit Panel Preview
 * Sticky large LED preview with dropdown settings menu
 */

import { Settings } from 'lucide-react';
import type { ZoneSnapshot } from '@/shared/types/domain/zone';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
} from '@/shared/ui/dropdown-menu';
import { Button } from '@/shared/ui/button';
import { FullLEDPreview } from '../preview';
import { LEDPreviewSettings } from '@/features/zones/components/preview/LEDPreviewSettings';
import { colorToRGB } from '@/shared/utils/colorConvert';
import { useOutputFrame } from '@/features/frames/realtime/frames.store';

interface ZoneEditPanelPreviewProps {
  zone: ZoneSnapshot;
  useSettings?: boolean;
}

export function ZoneEditPanelPreview({ zone, useSettings = false }: ZoneEditPanelPreviewProps) {
  const frame = useOutputFrame();
  const livePixels = frame?.zones[zone.id];

  // Live from output_frame stream; fallback to static single-color fill
  const zoneRGB = colorToRGB(zone.color);
  const pixels = livePixels
    ?? Array(zone.pixel_count).fill(zoneRGB as [number, number, number]);

  // OLD: static only
  // const mockPixels = Array(zone.pixel_count).fill(null).map(() => zoneRGB as [number, number, number]);

  return (
    <div className="sticky top-[88px] z-10 p-4">
      <div className="flex items-center justify-between">
        <p className="text-base font-semibold text-text-primary">Preview</p>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="hover:bg-bg-elevated"
              title="Preview settings"
            >
              <Settings className="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <div className="p-2">
              <LEDPreviewSettings />
            </div>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <FullLEDPreview
        pixels={pixels}
        pixelCount={zone.pixel_count}
        brightness={livePixels ? 100 : (zone.brightness || 100)}
        animationMode={zone.render_mode}
        useSettings={useSettings}
      />
    </div>
  );
}
