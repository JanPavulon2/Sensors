/**
 * Zone Edit Panel
 * Modal dialog for editing zone settings
 * Composed of: Header, Preview, ColorSection, AnimationSection, Footer
 */

import { useState } from 'react';
import { Dialog, DialogContent } from '@/shared/ui/dialog';
import type { Zone } from '@/shared/types/domain/zone';
import { ZoneEditPanelHeader } from './ZoneEditPanelHeader';
import { ZoneEditPanelPreview } from './ZoneEditPanelPreview';
import { ZoneColorSection } from './ZoneColorSection';
import { ZoneAnimationSection } from './ZoneAnimationSection';
import { ZoneEditPanelFooter } from './ZoneEditPanelFooter';

interface ZoneEditPanelProps {
  zone: Zone;
  currentIndex: number;
  totalZones: number;
  onClose: () => void;
  onPrevZone: () => void;
  onNextZone: () => void;
}

export function ZoneEditPanel({
  zone,
  currentIndex,
  totalZones,
  onClose,
  onPrevZone,
  onNextZone,
}: ZoneEditPanelProps) {
  const [colorExpanded, setColorExpanded] = useState(true);
  const [animationExpanded, setAnimationExpanded] = useState(false);

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="max-w-lg w-full max-h-[90vh] flex flex-col gap-0 p-0 overflow-hidden"
        onEscapeKeyDown={() => onClose()}
      >
        {/* Sticky Header */}
        <ZoneEditPanelHeader zone={zone} onClose={onClose} />

        {/* Sticky Preview */}
        <ZoneEditPanelPreview zone={zone} />

        {/* Scrollable Sections */}
        <div className="flex-1 overflow-y-auto">
          <ZoneColorSection
            zone={zone}
            expanded={colorExpanded}
            onToggle={setColorExpanded}
          />

          <ZoneAnimationSection
            zone={zone}
            expanded={animationExpanded}
            onToggle={setAnimationExpanded}
          />
        </div>

        {/* Sticky Footer */}
        <ZoneEditPanelFooter
          currentIndex={currentIndex}
          totalZones={totalZones}
          onPrevious={onPrevZone}
          onNext={onNextZone}
        />
      </DialogContent>
    </Dialog>
  );
}

export default ZoneEditPanel;
