import { useOutputFrame } from '../realtime/frames.store';
import { useZones } from '@/features/zones/hooks';
import { ZoneFrameView } from './ZoneFrameView';

export function AllZonesView() {
  const frame = useOutputFrame();
  const zones = useZones();

  if (!frame) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-accent-primary border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-text-secondary">Waiting for frame stream...</p>
        </div>
      </div>
    );
  }

  const zoneMap = Object.fromEntries(zones.map(z => [z.id, z.display_name]));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Object.entries(frame.zones).map(([zoneId, pixels]) => (
        <ZoneFrameView
          key={zoneId}
          zoneId={zoneId}
          pixels={pixels}
          displayName={zoneMap[zoneId]}
        />
      ))}
    </div>
  );
}
