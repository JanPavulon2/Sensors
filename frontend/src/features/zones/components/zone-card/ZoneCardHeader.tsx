/**
 * Zone Card Header
 * Displays zone name, power toggle, pixel count, and render mode indicator
 */

import type { ZoneSnapshot } from '@/shared/types/domain/zone';
import { PowerSwitch } from '@/shared/ui/power-switch';
import { ZoneRenderModeIndicator } from '../common';
import { useZonePowerCommand } from '@/features/zones/hooks/useZonePowerCommand';

interface ZoneCardHeaderProps {
  zone: ZoneSnapshot;
}

export function ZoneCardHeader({ zone }: ZoneCardHeaderProps) {
  const powerCommand = useZonePowerCommand(zone.id);

  const isOn = zone.is_on;
  // const powerMutation = useToggleZonePowerMutation(zone.id);

  const handleToggle = (checked: boolean) => {
    powerCommand.setPower(checked);
    // powerMutation.mutate({ is_on: checked });
  };

  const isAnimationMode = zone.render_mode === "ANIMATION";

  return (
    <div className="space-y-1">
      {/* Name + Power Switch */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-text-primary">{zone.display_name}</h3>
        <PowerSwitch
          checked={zone.is_on}
          onCheckedChange={handleToggle}
          disabled={powerCommand.isSending}
          label={`Toggle ${zone.display_name} on/off`}
        />
      </div>

      {/* Pixel Count + Render Mode Indicator */}
      <div className="flex items-center gap-2">
        <p className="text-sm text-text-secondary">{zone.pixel_count} pixels</p>
        <span className="w-1 h-1 rounded-full bg-border-default" />
        <div className="scale-90 origin-left">
          <ZoneRenderModeIndicator
            renderMode={isAnimationMode ? 'animation' : 'static'}
            animationName={zone.animation?.id}
            compact={true}
          />
        </div>
      </div>
    </div>
  );
}
