/**
 * Zone Render Mode Indicator
 * Displays zone animation/static status with icon and text
 */

import { Circle, Play } from 'lucide-react';

interface ZoneRenderModeIndicatorProps {
  renderMode: 'static' | 'animation';
  animationName?: string | null;
  compact?: boolean;
}

export function ZoneRenderModeIndicator({
  renderMode,
  animationName,
  compact = false,
}: ZoneRenderModeIndicatorProps) {
  const isStatic = renderMode === 'static';

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        {isStatic ? (
          <Circle className="w-3 h-3 text-text-tertiary" />
        ) : (
          <Play className="w-3 h-3 text-accent-primary fill-accent-primary" />
        )}
        <span className={`text-sm ${isStatic ? 'text-text-tertiary' : 'text-accent-primary'}`}>
          {isStatic ? 'No animation' : animationName || 'Animation'}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {isStatic ? (
        <Circle className="w-4 h-4 text-text-tertiary" />
      ) : (
        <Play className="w-4 h-4 text-accent-primary fill-accent-primary" />
      )}
      <span className={`text-sm ${isStatic ? 'text-text-tertiary' : 'text-accent-primary'}`}>
        {isStatic ? 'No animation' : `Animation: ${animationName || 'Unknown'}`}
      </span>
    </div>
  );
}
