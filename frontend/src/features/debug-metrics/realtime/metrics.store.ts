/**
 * Render Metrics Store
 *
 * Module-level state with useSyncExternalStore for efficient subscriptions.
 * Follows the same pattern as frames.store.ts for high-frequency updates.
 */

import { useSyncExternalStore } from 'react';
import type { RenderMetricsSnapshot } from '../types/metrics';

const HISTORY_SIZE = 60; // 1 minute at 1 Hz

let currentSnapshot: RenderMetricsSnapshot | null = null;
let snapshotHistory: RenderMetricsSnapshot[] = [];
let isConnected = false;

// Cached references to prevent unnecessary re-renders
let cachedSnapshot: RenderMetricsSnapshot | null = null;
let cachedHistory: RenderMetricsSnapshot[] = [];
let cachedIsConnected = false;

const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

function subscribe(callback: () => void): () => void {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

// --- Mutators (called from socket module) ---

export function setMetricsSnapshot(snapshot: RenderMetricsSnapshot): void {
  currentSnapshot = snapshot;
  cachedSnapshot = snapshot;

  snapshotHistory = [...snapshotHistory, snapshot];
  if (snapshotHistory.length > HISTORY_SIZE) {
    snapshotHistory = snapshotHistory.slice(-HISTORY_SIZE);
  }
  cachedHistory = snapshotHistory;

  notify();
}

export function setMetricsConnected(connected: boolean): void {
  isConnected = connected;
  cachedIsConnected = connected;
  notify();
}

export function clearMetricsHistory(): void {
  currentSnapshot = null;
  cachedSnapshot = null;
  snapshotHistory = [];
  cachedHistory = [];
  notify();
}

// --- Hooks ---

export function useMetricsSnapshot(): RenderMetricsSnapshot | null {
  return useSyncExternalStore(
    subscribe,
    () => cachedSnapshot,
    () => null,
  );
}

export function useMetricsHistory(): RenderMetricsSnapshot[] {
  return useSyncExternalStore(
    subscribe,
    () => cachedHistory,
    () => [],
  );
}

export function useMetricsConnected(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => cachedIsConnected,
    () => false,
  );
}
