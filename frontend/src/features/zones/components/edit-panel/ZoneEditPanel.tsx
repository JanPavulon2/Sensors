/**
 * Zone Edit Panel
 * Modal dialog for editing zone settings
 * Composed of: Header, Preview, ColorSection, AnimationSection, Footer
 */

import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/shared/ui/dialog';
import type { ZoneSnapshot } from '@/shared/types/domain/zone';
import { ZoneEditPanelHeader } from './ZoneEditPanelHeader';
import { ZoneEditPanelPreview } from './ZoneEditPanelPreview';
import { ZoneColorSection } from './ZoneColorSection';
import { ZoneAnimationSection } from './ZoneAnimationSection';
import { ZoneEditPanelFooter } from './ZoneEditPanelFooter';

interface ZoneEditPanelProps {
  zone: ZoneSnapshot;
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
  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className={`max-w-lg w-full max-h-[90vh] flex flex-col gap-0 p-0 md:max-w-4xl lg:max-w-5xl transition-opacity ${
          !zone.is_on ? 'opacity-50' : ''
        }`}
        onEscapeKeyDown={() => onClose()}
      >
        {/* Accessible title for screen readers */}
        <DialogTitle className="sr-only">Edit {zone.display_name}</DialogTitle>
        <DialogDescription className="sr-only">
          Configure zone {zone.display_name} settings including brightness, color, and animations
        </DialogDescription>

        {/* Sticky Header */}
        <ZoneEditPanelHeader zone={zone} onClose={onClose} />

        {/* Sticky Preview */}
        <div className="border-b border-border-default">
          <ZoneEditPanelPreview zone={zone} useSettings />
        </div>

        {/* Scrollable Sections - Side-by-side layout on desktop */}
        <div className={`flex-1 overflow-y-auto ${!zone.is_on ? 'pointer-events-none' : ''}`}>
          {/* Main Content Grid - side by side layout */}
          <div className="grid grid-cols-2 gap-0 w-full">
            {/* Appearance Section - left column */}
            <div className="w-full border-r border-border-default overflow-y-auto">
              <ZoneColorSection zone={zone} />
            </div>

            {/* Animation Section - right column */}
            <div className="w-full">
              <ZoneAnimationSection zone={zone} />
            </div>
          </div>
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
