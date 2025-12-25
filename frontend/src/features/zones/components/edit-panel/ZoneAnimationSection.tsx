/**
 * Zone Animation Section
 * Collapsible section for animation selection and parameters
 */

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { Zone } from '@/shared/types/domain/zone';
import { ZoneRenderMode } from '@/shared/types/domain/zone';
import { AnimationSelector, AnimationParametersPanel } from '@/features/zones/components/animations';
import type { AnimationID } from '@/features/zones/components/animations';
import { useUpdateZoneAnimationMutation, useUpdateZoneAnimationParametersMutation } from '@/features/zones/api';

interface ZoneAnimationSectionProps {
  zone: Zone;
  expanded?: boolean;
  onToggle?: (expanded: boolean) => void;
}

export function ZoneAnimationSection({
  zone,
  expanded = false,
  onToggle,
}: ZoneAnimationSectionProps) {
  const [isExpanded, setIsExpanded] = useState(expanded);
  const animationMutation = useUpdateZoneAnimationMutation(zone.id);
  const parametersMutation = useUpdateZoneAnimationParametersMutation(zone.id);

  const handleToggle = () => {
    const newState = !isExpanded;
    setIsExpanded(newState);
    onToggle?.(newState);
  };

  // Determine selected animation based on render mode (not animation_id)
  const isStatic = zone.state.render_mode === ZoneRenderMode.STATIC;
  const selectedAnimation: AnimationID = isStatic ? 'STATIC' : ((zone.state.animation_id as AnimationID) || 'STATIC');

  return (
    <div className="border-t border-border-default">
      {/* Section Header */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between p-4 hover:bg-bg-elevated transition-colors"
      >
        <h3 className="text-base font-semibold text-text-primary">Animation</h3>
        <ChevronDown
          className={`w-4 h-4 text-text-secondary transition-transform ${
            isExpanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Section Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 bg-bg-app">
          {/* Animation Selector */}
          <AnimationSelector
            selectedAnimation={selectedAnimation}
            onSelect={(animationId) => {
              animationMutation.mutate({
                animation_id: animationId === 'STATIC' ? null : animationId,
              });
            }}
            disabled={animationMutation.isPending}
          />

          {/* Animation Parameters (if not static) */}
          {!isStatic && zone.state.animation_id && (
            <div className="border-t border-border-default pt-4">
              <h4 className="text-sm font-medium text-text-primary mb-3">Parameters</h4>
              <AnimationParametersPanel
                animationId={zone.state.animation_id as any}
                parameters={{}}
                onParameterChange={(key, value) => {
                  parametersMutation.mutate({
                    animation_parameters: {
                      [key]: value,
                    },
                  });
                }}
                disabled={parametersMutation.isPending}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
