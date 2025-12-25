/**
 * CollectionNavigator Component
 * Generic prev/next navigation for collections with item counter
 */

import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/shared/ui/button';

interface CollectionNavigatorProps {
  /** Current item index (0-based) */
  currentIndex: number;
  /** Total number of items */
  totalItems: number;
  /** Label for the item (e.g., "Zone", "Animation") - optional */
  itemLabel?: string;
  /** Callback when previous button is clicked */
  onPrevious: () => void;
  /** Callback when next button is clicked */
  onNext: () => void;
  /** Disable previous button */
  disablePrevious?: boolean;
  /** Disable next button */
  disableNext?: boolean;
}

export function CollectionNavigator({
  currentIndex,
  totalItems,
  itemLabel = 'Item',
  onPrevious,
  onNext,
  disablePrevious,
  disableNext,
}: CollectionNavigatorProps): JSX.Element {
  const displayIndex = currentIndex + 1; // Convert to 1-based for display

  return (
    <div className="flex items-center justify-between gap-4">
      {/* Previous Button */}
      <Button
        variant="outline"
        size="sm"
        onClick={onPrevious}
        disabled={disablePrevious ?? currentIndex === 0}
        className="hover:bg-bg-elevated"
        aria-label={`Go to previous ${itemLabel.toLowerCase()}`}
      >
        <ChevronLeft className="w-4 h-4" />
        <span className="ml-1">Previous</span>
      </Button>

      {/* Counter */}
      <div className="flex flex-col items-center gap-1">
        <span className="text-sm text-text-secondary">
          {displayIndex} / {totalItems}
        </span>
        {itemLabel && (
          <span className="text-xs text-text-tertiary">{itemLabel}</span>
        )}
      </div>

      {/* Next Button */}
      <Button
        variant="outline"
        size="sm"
        onClick={onNext}
        disabled={disableNext ?? currentIndex === totalItems - 1}
        className="hover:bg-bg-elevated"
        aria-label={`Go to next ${itemLabel.toLowerCase()}`}
      >
        <span className="mr-1">Next</span>
        <ChevronRight className="w-4 h-4" />
      </Button>
    </div>
  );
}
