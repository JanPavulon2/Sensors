/**
 * Zone Animation Section
 * Carousel-style animation selection with parameters below
 */

import type { Zone } from '@/shared/types/domain/zone';
import { ZoneRenderMode } from '@/shared/types/domain/zone';
import { AnimationCarousel, AnimationParametersPanel } from '@/features/zones/components/animations';
import type { AnimationID } from '@/features/zones/components/animations';
import { useUpdateZoneAnimationMutation, useUpdateZoneAnimationParametersMutation } from '@/features/zones/api';

interface ZoneAnimationSectionProps {
  zone: Zone;
}

export function ZoneAnimationSection({
  zone,
}: ZoneAnimationSectionProps) {
  const animationMutation = useUpdateZoneAnimationMutation(zone.id);
  const parametersMutation = useUpdateZoneAnimationParametersMutation(zone.id);

  // Determine selected animation based on render mode (not animation_id)
  const isStatic = zone.state.render_mode === ZoneRenderMode.STATIC;
  const selectedAnimation: AnimationID = isStatic ? 'STATIC' : ((zone.state.animation_id as AnimationID) || 'STATIC');

  return (
    <div>
      {/* Section Header */}
      <h3 className="text-base font-semibold text-text-primary px-4 pt-4">Animation</h3>

      {/* Section Content */}
      <div className="px-4 pb-4 space-y-6 bg-bg-app">
        {/* Animation Carousel */}
        <AnimationCarousel
          selectedAnimation={selectedAnimation}
          onSelect={(animationId: AnimationID) => {
            animationMutation.mutate({
              animation_id: animationId === 'STATIC' ? null : animationId,
            });
          }}
          disabled={animationMutation.isPending}
        />

        {/* Animation Parameters Section - Reserved height to prevent flicker */}
        <div className="border-t border-border-default pt-4 space-y-3 min-h-[120px]">
          {!isStatic && zone.state.animation_id ? (
            <>
              <h4 className="text-sm font-medium text-text-primary">Parameters</h4>
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
            </>
          ) : (
            <p className="text-sm text-text-tertiary italic">No parameters for this animation</p>
          )}
        </div>
      </div>
    </div>
  );
}
