import { useZone as useZoneStore } from '../realtime/zones.store';
import type { ZoneSnapshot } from '@/shared/types/domain/zone';

export function useZone(zoneId: string): ZoneSnapshot | undefined {
  return useZoneStore(zoneId);
}