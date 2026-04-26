import { useSyncExternalStore } from 'react';
import type { OutputFrame, FrameMetrics } from '../types/output-frame';

let currentFrame: OutputFrame | null = null;
let metrics: FrameMetrics = { fps: 0, latency: 0, frameCount: 0, lastFrameTime: 0 };
let cachedMetrics: FrameMetrics = { fps: 0, latency: 0, frameCount: 0, lastFrameTime: 0 };
let frameTimes: number[] = [];
const listeners = new Set<() => void>();

export function setOutputFrame(frame: OutputFrame): void {
  const now = performance.now();
  currentFrame = frame;

  // Calculate FPS
  frameTimes.push(now);
  if (frameTimes.length > 30) frameTimes.shift();

  if (frameTimes.length >= 2) {
    const delta = frameTimes[frameTimes.length - 1] - frameTimes[0];
    metrics.fps = Math.round((frameTimes.length - 1) / (delta / 1000));
  }

  metrics.frameCount++;
  metrics.lastFrameTime = now;

  // Update cached metrics (for stable reference in useSyncExternalStore)
  cachedMetrics = { ...metrics };

  // Debug logging (first 5 frames only)
  if (metrics.frameCount <= 5) {
    console.log('[frames] Frame received:', {
      t: frame.t,
      zoneCount: Object.keys(frame.zones).length,
      zones: Object.keys(frame.zones),
      fps: metrics.fps
    });
  }

  listeners.forEach(l => l());
}

export function useOutputFrame(): OutputFrame | null {
  return useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => listeners.delete(cb); },
    () => currentFrame,
    () => null
  );
}

export function useFrameMetrics(): FrameMetrics {
  return useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => listeners.delete(cb); },
    () => cachedMetrics,
    () => ({ fps: 0, latency: 0, frameCount: 0, lastFrameTime: 0 })
  );
}
