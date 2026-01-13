/**
 * Zones Grid Component
 * Displays a grid of zone cards with real-time updates via Socket.IO
 */

import { useZones } from '@/features/zones/realtime/zones.store';
import { ZoneCard } from '../zone-card';
import { Card, CardContent } from '@/shared/ui/card';

interface ZonesGridProps {
  onSelectZone?: (zoneId: string) => void;
}

export function ZonesGrid({ onSelectZone }: ZonesGridProps): JSX.Element {
  // Real-time updates from Socket.IO store
  const zones = useZones();

  // Loading state - show skeleton cards while waiting for initial data
  if (zones.length === 0) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="h-48 pt-6 bg-bg-elevated" />
          </Card>
        ))}
      </div>
    );
  }

  // Render zone cards
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {zones.map((zone) => (
        <ZoneCard
          key={zone.id}
          zone={zone}
          onSelect={onSelectZone}
        />
      ))}
    </div>
  );
}

export default ZonesGrid;
