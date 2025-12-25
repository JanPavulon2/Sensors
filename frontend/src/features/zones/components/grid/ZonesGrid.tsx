/**
 * Zones Grid Component
 * Displays a grid of zone cards with loading and error states
 */

import { useZonesQuery } from '@/features/zones/api';
import { ZoneCard } from '../zone-card';
import { Card, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';

interface ZonesGridProps {
  onSelectZone?: (zoneId: string) => void;
}

export function ZonesGrid({ onSelectZone }: ZonesGridProps): JSX.Element {
  const { data, isLoading, error, refetch } = useZonesQuery();

  const zones = data?.zones || [];

  if (isLoading) {
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

  if (error) {
    return (
      <Card className="border-error bg-error/10">
        <CardContent className="pt-6">
          <p className="text-sm text-error mb-3">
            Failed to load zones: {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <Button size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (zones.length === 0) {
    return (
      <Card className="border-border-subtle bg-bg-elevated">
        <CardContent className="pt-6 text-center">
          <p className="text-text-secondary mb-3">No zones loaded</p>
          <p className="text-xs text-text-tertiary mb-4">
            Check your backend connection in Settings
          </p>
          <Button size="sm" onClick={() => refetch()}>
            Refresh
          </Button>
        </CardContent>
      </Card>
    );
  }

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
