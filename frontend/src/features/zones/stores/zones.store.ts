import { create } from 'zustand';
import type { ZoneSnapshot } from '@/shared/types/domain/zone';

import { devtools } from 'zustand/middleware';

interface ZonesState {
  zones: Record<string, ZoneSnapshot>;

  setZonesSnapshot: (zones: ZoneSnapshot[]) => void;
  upsertZoneSnapshot: (zone: ZoneSnapshot) => void;

  getZone: (zoneId: string) => ZoneSnapshot | undefined;
}


/**
 * Zones Store
 *
 * Rules:
 * - updated ONLY by Socket.IO events
 * - no REST
 * - no optimistic updates
 * - backend is arbiter of truth
 */
export const useZonesStore = create<ZonesState>()(
  devtools(
    (set, get) => ({
      zones: {},

      setZonesSnapshot: (zones) =>
        set(
          {
            zones: Object.fromEntries(
              zones.map((zone) => [zone.id, zone])
            ),
          },
          false,
          'zones/setZonesSnapshot'
        ),

      upsertZoneSnapshot: (zone) =>
        set(
          (state) => ({
            zones: {
              ...state.zones,
              [zone.id]: zone,
            },
          }),
          false,
          'zones/upsertZoneSnapshot'
        ),

      getZone: (zoneId) => get().zones[zoneId],
    }),
    {
      name: 'zones-store',
    }
  )
);

/**
 * Selectors (optional but recommended)
 */

export const useZonesList = () =>
  useZonesStore((state) => Object.values(state.zones));

export const useZoneById = (zoneId: string) =>
  useZonesStore((state) => state.zones[zoneId] ?? null);