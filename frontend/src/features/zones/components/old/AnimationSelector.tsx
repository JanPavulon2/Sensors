/**
 * Animation Selector - Grid of available animations
 *
 * Shows all 7 animation types in a grid layout
 * Organized by category (Basic, Color, Advanced)
 * Click to select animation
 */

import React from 'react';

export type AnimationID = 'STATIC' | 'BREATHE' | 'COLOR_FADE' | 'COLOR_CYCLE' | 'SNAKE' | 'COLOR_SNAKE' | 'MATRIX';

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
    id: 'COLOR_CYCLE',
    name: 'Cycle',
    icon: '🔄',
    description: 'Fast hue rotation loop',
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
  {
    id: 'MATRIX',
    icon: '🟩',
    name: 'Matrix',
    description: 'Matrix rain effect',
    category: 'advanced',
  },
];

interface AnimationSelectorProps {
  selectedAnimation?: AnimationID;
  onSelect: (animationId: AnimationID) => void;
  disabled?: boolean;
}

/**
 * AnimationSelector Component
 * Grid of animation tiles with categories
 */
export const AnimationSelector: React.FC<AnimationSelectorProps> = ({
  selectedAnimation,
  onSelect,
  disabled = false,
}) => {
  // Group animations by category
  const categories = Array.from(new Set(ANIMATIONS.map((a) => a.category)));

  return (
    <div className="space-y-6">
      {categories.map((category) => {
        const categoryAnimations = ANIMATIONS.filter((a) => a.category === category);
        const categoryLabel = {
          basic: 'Basic',
          color: 'Color',
          advanced: 'Advanced',
        }[category];

        return (
          <div key={category} className="space-y-3">
            {/* Category Label */}
            <h4 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
              {categoryLabel}
            </h4>

            {/* Animation Grid */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {categoryAnimations.map((animation) => (
                <button
                  key={animation.id}
                  onClick={() => !disabled && onSelect(animation.id)}
                  onKeyDown={(e) => {
                    if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault();
                      onSelect(animation.id);
                    }
                  }}
                  disabled={disabled}
                  className={`p-3 rounded-md border-2 transition-all duration-200 text-center space-y-1 ${
                    selectedAnimation === animation.id
                      ? 'border-accent-primary bg-accent-primary/10 shadow-lg shadow-accent-primary/50'
                      : 'border-border-default hover:border-accent-primary hover:bg-bg-elevated'
                  } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  title={animation.description}
                  aria-pressed={selectedAnimation === animation.id}
                  aria-label={`Select ${animation.name} animation`}
                >
                  {/* Icon */}
                  <div className="text-2xl">{animation.icon}</div>

                  {/* Name */}
                  <p className="text-sm font-medium text-text-primary">{animation.name}</p>

                  {/* Description */}
                  <p className="text-xs text-text-tertiary hidden sm:block line-clamp-2">
                    {animation.description}
                  </p>
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default AnimationSelector;
