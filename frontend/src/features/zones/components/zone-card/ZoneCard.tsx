/**
 * Zone Card Component
 * Displays zone information with power control and edit action
 * Composed of: ZoneCardHeader, ZoneCardPreview, ZoneCardFooter
 */

import { Card, CardContent, CardHeader } from '@/shared/ui/card';
import type { ZoneSnapshot } from '@/shared/types/domain/zone';
import { ZoneCardHeader } from './ZoneCardHeader';
import { ZoneCardPreview } from './ZoneCardPreview';
import { ZoneCardFooter } from './ZoneCardFooter';

interface ZoneCardProps {
  zone: ZoneSnapshot;
  onSelect?: (zoneId: string) => void;
}

export function ZoneCard({ zone, onSelect }: ZoneCardProps): JSX.Element {
  const handleEdit = () => {
    onSelect?.(zone.id);
  };

  return (
    <Card className="hover:border-accent-primary transition-colors overflow-hidden flex flex-col h-full">
      {/* Header: Name, Power Switch, Pixels, Render Mode */}
      <CardHeader className="pb-3">
        <ZoneCardHeader zone={zone} />
      </CardHeader>

      {/* Preview: LED Strip Visualization */}
      <CardContent className="flex-1 p-3 pb-0">
        <ZoneCardPreview zone={zone} />
      </CardContent>

      {/* Footer: Edit Button */}
      <CardContent className="pt-2 pb-3 px-3">
        <ZoneCardFooter onEdit={handleEdit} />
      </CardContent>
    </Card>
  );
}

export default ZoneCard;
