/**
 * Zone Animation Section
 * Carousel-style animation selection with parameters below
 */

import { useCallback } from 'react';
import type { ZoneSnapshot } from '@/shared/types/domain/zone';
import { AnimationCarousel, AnimationParametersPanel } from '@/features/zones/components/animations';
import type { AnimationID } from '@/features/zones/components/animations';
import { api } from '@/shared/api/client';

interface ZoneAnimationSectionProps {
  zone: ZoneSnapshot;
}

export function ZoneAnimationSection({
  zone,
}: ZoneAnimationSectionProps) {
  // Determine selected animation based on render mode (not animation_id)
  const isStatic = zone.render_mode === 'STATIC';
  const selectedAnimation: AnimationID = isStatic ? 'STATIC' : ((zone.animation?.id as AnimationID) || 'STATIC');

  const handleAnimationSelect = useCallback((animationId: AnimationID) => {
    if (animationId === 'STATIC') {
      // Stop animation and return to static mode
      api.post(`/v1/zones/${zone.id}/animation/stop`).catch((error) => {
        console.error('Failed to stop animation:', error);
      });
    } else {
      // Start animation
      api.put(`/v1/zones/${zone.id}/animation`, {
        animation_id: animationId,
      }).catch((error) => {
        console.error('Failed to set animation:', error);
      });
    }
  }, [zone.id]);

  const handleParameterChange = useCallback((key: string, value: string | number | boolean) => {
    api.put(`/v1/zones/${zone.id}/animation/parameters`, {
      parameters: {
        [key]: value,
      },
    }).catch((error) => {
      console.error('Failed to update animation parameter:', error);
    });
  }, [zone.id]);

  return (
    <div>
      {/* Section Header */}
      <h3 className="text-base font-semibold text-text-primary px-4 pt-4">Animation</h3>

      {/* Section Content */}
      <div className="px-4 pb-4 space-y-6 bg-bg-app">
        {/* Animation Carousel */}
        <AnimationCarousel
          selectedAnimation={selectedAnimation}
          onSelect={handleAnimationSelect}
        />

        {/* Animation Parameters Section - Reserved height to prevent flicker */}
        <div className="border-t border-border-default pt-4 space-y-3 min-h-[120px]">
          {!isStatic && zone.animation?.id ? (
            <>
              <h4 className="text-sm font-medium text-text-primary">Parameters</h4>
              <AnimationParametersPanel
                animationId={zone.animation?.id as any}
                parameters={zone.animation?.parameters || {}}
                onParameterChange={handleParameterChange}
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
