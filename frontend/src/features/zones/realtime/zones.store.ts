import { useSyncExternalStore, useCallback } from 'react';
import type { ZoneSnapshot } from '@/shared/types/domain/zone';

type ZoneMap = Record<string, ZoneSnapshot>;

let zones: ZoneMap = {};
let cachedZonesArray: ZoneSnapshot[] = [];
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

export function setZonesSnapshot(snapshot: ZoneSnapshot[]): void {
  zones = Object.fromEntries(snapshot.map(z => [z.id, z]));
  cachedZonesArray = snapshot; // Cache the array to avoid recreating it
  notify();
}

export function updateZoneSnapshot(zone: ZoneSnapshot): void {
  zones = { ...zones, [zone.id]: zone };
  // Rebuild cached array with updated zone
  cachedZonesArray = Object.values(zones);
  notify();
}

// Subscription function - always the same reference
function subscribe(callback: () => void): () => void {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

// Snapshot function - returns cached array to avoid recreation
function getZonesSnapshot(): ZoneSnapshot[] {
  return cachedZonesArray;
}

function getServerSnapshot(): ZoneSnapshot[] {
  return [];
}

export function useZones(): ZoneSnapshot[] {
  return useSyncExternalStore(
    subscribe,
    getZonesSnapshot,
    getServerSnapshot
  );
}

export function useZone(id: string): ZoneSnapshot | undefined {
  // Cache zone by ID
  const getSnapshot = useCallback(() => zones[id], [id]);
  const getServerSnapshot = useCallback(() => undefined, []);

  return useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot
  );
}
