/**
 * Zone Store
 * Global state management for zones using Zustand
 */

import { create } from 'zustand';
import type { Zone, ZoneState } from '@/types/zone';

interface ZoneStore {
  zones: Zone[];
  selectedZoneId: string | null;
  loading: boolean;
  error: string | null;

  // Actions
  setZones: (zones: Zone[]) => void;
  addZone: (zone: Zone) => void;
  updateZone: (id: string, updates: Partial<Zone>) => void;
  deleteZone: (id: string) => void;
  setSelectedZone: (id: string | null) => void;
  updateZoneState: (id: string, state: ZoneState) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useZoneStore = create<ZoneStore>((set) => ({
  zones: [],
  selectedZoneId: null,
  loading: false,
  error: null,

  setZones: (zones: Zone[]) => set({ zones }),

  addZone: (zone: Zone) =>
    set((state) => ({
      zones: [...state.zones, zone],
    })),

  updateZone: (id: string, updates: Partial<Zone>) =>
    set((state) => ({
      zones: state.zones.map((zone) =>
        zone.id === id ? { ...zone, ...updates } : zone
      ),
    })),

  deleteZone: (id: string) =>
    set((state) => ({
      zones: state.zones.filter((zone) => zone.id !== id),
    })),

  setSelectedZone: (id: string | null) => set({ selectedZoneId: id }),

  updateZoneState: (id: string, state: ZoneState) =>
    set((prevState) => ({
      zones: prevState.zones.map((zone) =>
        zone.id === id ? { ...zone, state } : zone
      ),
    })),

  setLoading: (loading: boolean) => set({ loading }),

  setError: (error: string | null) => set({ error }),
}));

export default useZoneStore;
