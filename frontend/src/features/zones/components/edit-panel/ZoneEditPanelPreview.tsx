/**
 * Zone Edit Panel Preview
 * Sticky large LED preview with dropdown settings menu
 */

import { Settings } from 'lucide-react';
import type { Zone } from '@/shared/types/domain/zone';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
} from '@/shared/ui/dropdown-menu';
import { Button } from '@/shared/ui/button';
import { FullLEDPreview } from '../preview';
import { LEDPreviewSettings } from '@/features/zones/components/preview/LEDPreviewSettings';

interface ZoneEditPanelPreviewProps {
  zone: Zone;
  useSettings?: boolean;
}

export function ZoneEditPanelPreview({ zone, useSettings = false }: ZoneEditPanelPreviewProps) {
  // Mock pixel data
  const mockPixels = Array(zone.pixel_count)
    .fill(null)
    .map(() => {
      const [r, g, b] = zone.state.color.rgb || [0, 0, 0];
      return [r, g, b] as [number, number, number];
    });

  return (
    <div className="sticky top-[88px] z-10 bg-bg-panel p-4">
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
        pixels={mockPixels}
        pixelCount={zone.pixel_count}
        brightness={zone.state.brightness || 255}
        animationMode={zone.state.render_mode}
        useSettings={useSettings}
      />
    </div>
  );
}
