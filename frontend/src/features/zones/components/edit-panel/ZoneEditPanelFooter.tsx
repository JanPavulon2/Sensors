/**
 * Zone Edit Panel Footer
 * Sticky footer with zone navigation
 */

import { CollectionNavigator } from '@/shared/components/CollectionNavigator';

interface ZoneEditPanelFooterProps {
  currentIndex: number;
  totalZones: number;
  onPrevious: () => void;
  onNext: () => void;
}

export function ZoneEditPanelFooter({
  currentIndex,
  totalZones,
  onPrevious,
  onNext,
}: ZoneEditPanelFooterProps) {
  return (
    <div className="sticky bottom-0 z-10 bg-bg-panel border-t border-border-default p-4">
      <CollectionNavigator
        currentIndex={currentIndex}
        totalItems={totalZones}
        itemLabel="Zone"
        onPrevious={onPrevious}
        onNext={onNext}
      />
    </div>
  );
}
