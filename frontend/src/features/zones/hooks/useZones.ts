import { useZones as useZonesStore } from '../realtime/zones.store';
import type { ZoneSnapshot } from '@/shared/types/domain/zone';

export function useZones(): ZoneSnapshot[] {
  return useZonesStore();
}