/**
 * Animation Carousel
 * Carousel-style animation selector with centered highlight
 * Shows one animation centered/larger with < > navigation
 * Click any card to select or navigate with arrows
 */

import React, { useMemo } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import type { AnimationID } from './AnimationSelector';

interface Animation {
  id: AnimationID;
  name: string;
  icon: string;
  description: string;
  category: 'basic' | 'color' | 'advanced';
}

const ANIMATIONS: Animation[] = [
  {
    id: 'STATIC',
    name: 'Static',
    icon: '📍',
    description: 'Solid color, no animation',
    category: 'basic',
  },
  {
    id: 'BREATHE',
    icon: '💨',
    name: 'Breathe',
    description: 'Smooth brightness pulsing',
    category: 'basic',
  },
  {
    id: 'COLOR_FADE',
    icon: '🌅',
    name: 'Fade',
    description: 'Smooth hue fade in/out',
    category: 'color',
  },
  {
    id: 'SNAKE',
    icon: '🐍',
    name: 'Snake',
    description: 'Pixels chase pattern',
    category: 'advanced',
  },
  {
    id: 'COLOR_SNAKE',
    icon: '🌈',
    name: 'Color Snake',
    description: 'Rainbow chase pattern',
    category: 'advanced',
  },
];

interface AnimationCarouselProps {
  selectedAnimation?: AnimationID;
  onSelect: (animationId: AnimationID) => void;
  disabled?: boolean;
}

export const AnimationCarousel: React.FC<AnimationCarouselProps> = ({
  selectedAnimation = 'STATIC',
  onSelect,
  disabled = false,
}) => {
  // Find current index
  const currentIndex = useMemo(
    () => ANIMATIONS.findIndex((a) => a.id === selectedAnimation),
    [selectedAnimation]
  );

  // Visible cards (show 7 at a time with infinite loop)
  const visibleCount = 7;
  const centerOffset = Math.floor(visibleCount / 2);

  // Get visible animations with wrapping for infinite loop
  const visibleAnimations = Array.from({ length: visibleCount }, (_, i) => {
    const index = (currentIndex - centerOffset + i + ANIMATIONS.length * 100) % ANIMATIONS.length;
    return ANIMATIONS[index];
  });

  const handlePrevious = () => {
    const newIndex = (currentIndex - 1 + ANIMATIONS.length) % ANIMATIONS.length;
    onSelect(ANIMATIONS[newIndex].id);
  };

  const handleNext = () => {
    const newIndex = (currentIndex + 1) % ANIMATIONS.length;
    onSelect(ANIMATIONS[newIndex].id);
  };

  return (
    <div className="space-y-6">
      {/* Carousel Navigation */}
      <div className="flex items-center justify-between gap-4">
        {/* Previous Button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handlePrevious}
          disabled={disabled}
          className="shrink-0"
          aria-label="Previous animation"
        >
          <ChevronLeft className="w-5 h-5" />
        </Button>

        {/* Carousel Cards */}
        <div className="flex-1 flex gap-3 justify-center items-center overflow-hidden">
          {visibleAnimations.map((animation, idx) => {
            const isCenter = idx === centerOffset;
            const isEdge = idx === 0 || idx === visibleCount - 1;
            const isNearEdge = idx === 1 || idx === visibleCount - 2;
            const isSelected = animation.id === selectedAnimation;

            return (
              <button
                key={`${animation.id}-${idx}`}
                onClick={() => !disabled && onSelect(animation.id)}
                disabled={disabled}
                className={`
                  transition-all duration-200 rounded-lg border-2
                  flex flex-col items-center justify-center shrink-0
                  ${
                    isCenter && isSelected
                      ? 'border-accent-primary bg-accent-primary/10 shadow-lg shadow-accent-primary/50 p-6 h-56 w-44'
                      : 'border-border-default hover:border-accent-primary p-2 h-20 w-16'
                  }
                  ${isEdge || isNearEdge ? 'opacity-40' : 'opacity-100'}
                  ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}
                `}
                title={animation.description}
                aria-pressed={isSelected}
                aria-label={`Select ${animation.name} animation`}
              >
                {isCenter && isSelected ? (
                  <>
                    <div className="text-7xl mb-4">{animation.icon}</div>
                    <h3 className="text-xl font-semibold text-text-primary mb-2">{animation.name}</h3>
                    <p className="text-sm text-text-secondary mb-3 line-clamp-2">{animation.description}</p>
                    <span className="text-xs text-accent-primary font-medium uppercase tracking-wide">
                      {animation.category === 'basic' && 'Basic'}
                      {animation.category === 'color' && 'Color'}
                      {animation.category === 'advanced' && 'Advanced'}
                    </span>
                  </>
                ) : (
                  <>
                    <div className="text-3xl">{animation.icon}</div>
                    <p className="text-xs text-text-primary text-center mt-1">{animation.name}</p>
                  </>
                )}
              </button>
            );
          })}
        </div>

        {/* Next Button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleNext}
          disabled={disabled}
          className="shrink-0"
          aria-label="Next animation"
        >
          <ChevronRight className="w-5 h-5" />
        </Button>
      </div>
    </div>
  );
};

export default AnimationCarousel;
