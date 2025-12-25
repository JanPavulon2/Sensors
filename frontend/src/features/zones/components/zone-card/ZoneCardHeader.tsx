/**
 * Zone Card Header
 * Displays zone name, power toggle, pixel count, and render mode indicator
 */

import type { Zone } from '@/shared/types/domain/zone';
import { PowerSwitch } from '@/shared/ui/power-switch';
import { ZoneRenderModeIndicator } from '../common';
import { ZoneRenderMode } from '@/shared/types/domain/zone';
import { useToggleZonePowerMutation } from '@/features/zones/api';

interface ZoneCardHeaderProps {
  zone: Zone;
}

export function ZoneCardHeader({ zone }: ZoneCardHeaderProps) {
  const isOn = zone.state.is_on;
  const powerMutation = useToggleZonePowerMutation(zone.id);

  const handleToggle = (checked: boolean) => {
    powerMutation.mutate({ is_on: checked });
  };

  const isAnimationMode = zone.state.render_mode === ZoneRenderMode.ANIMATION;

  return (
    <div className="space-y-1">
      {/* Name + Power Switch */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-text-primary">{zone.name}</h3>
        <PowerSwitch
          checked={isOn}
          onCheckedChange={handleToggle}
          disabled={powerMutation.isPending}
          label={`Toggle ${zone.name} on/off`}
        />
      </div>

      {/* Pixel Count + Render Mode Indicator */}
      <div className="flex items-center gap-2">
        <p className="text-sm text-text-secondary">{zone.pixel_count} pixels</p>
        <span className="w-1 h-1 rounded-full bg-border-default" />
        <div className="scale-90 origin-left">
          <ZoneRenderModeIndicator
            renderMode={isAnimationMode ? 'animation' : 'static'}
            animationName={zone.state.animation_id}
            compact={true}
          />
        </div>
      </div>
    </div>
  );
}
