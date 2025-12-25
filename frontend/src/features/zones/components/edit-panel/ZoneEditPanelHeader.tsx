/**
 * Zone Edit Panel Header
 * Sticky header with zone info, power switch, and close button
 */

import { X } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { PowerSwitch } from '@/shared/ui/power-switch';
import type { Zone } from '@/shared/types/domain/zone';
import { ZoneRenderModeIndicator } from '../common';
import { useToggleZonePowerMutation } from '@/features/zones/api';

interface ZoneEditPanelHeaderProps {
  zone: Zone;
  onClose: () => void;
}

export function ZoneEditPanelHeader({ zone, onClose }: ZoneEditPanelHeaderProps) {
  const togglePowerMutation = useToggleZonePowerMutation(zone.id);

  const handleTogglePower = () => {
    togglePowerMutation.mutate({ is_on: !zone.state.is_on });
  };

  return (
    <div className="sticky top-0 z-10 bg-bg-panel border-b border-border-default p-6 space-y-3">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-text-primary">{zone.name}</h2>
          <div className="flex items-center gap-2 mt-1">
            <p className="text-sm text-text-secondary">{zone.pixel_count} pixels</p>
            <span className="w-1 h-1 rounded-full bg-border-default" />
            <div className="scale-90 origin-left">
              <ZoneRenderModeIndicator
                renderMode={zone.state.render_mode}
                animationName={zone.state.animation_id}
                compact={true}
              />
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <PowerSwitch
            checked={zone.state.is_on}
            onCheckedChange={handleTogglePower}
            disabled={togglePowerMutation.isPending}
            label="Zone Power"
          />
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="hover:bg-bg-elevated"
            aria-label="Close panel"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
