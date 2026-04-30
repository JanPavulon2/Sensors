/**
 * Render Metrics Socket.IO Client
 *
 * Connects to the /metrics namespace. autoConnect: false — only connects
 * when the Render tab is active (called from component useEffect).
 *
 * Streaming only — mutations (reset, interval, fps) go through REST API.
 */

import { io } from 'socket.io-client';
import { setMetricsSnapshot, setMetricsConnected } from './metrics.store';
import type { RenderMetricsSnapshot } from '../types/metrics';

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL ?? 'http://localhost:8000';

export const metricsSocket = io(`${SOCKET_URL}/metrics`, {
  transports: ['websocket'],
  autoConnect: false,
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 500,
});

metricsSocket.on('connect', () => {
  console.log('[metricsSocket] connected', metricsSocket.id);
  setMetricsConnected(true);
});

metricsSocket.on('disconnect', (reason) => {
  console.warn('[metricsSocket] disconnected', reason);
  setMetricsConnected(false);
});

metricsSocket.on('connect_error', (err) => {
  console.error('[metricsSocket] connect_error', err);
});

metricsSocket.on('metrics:snapshot', (data: RenderMetricsSnapshot) => {
  setMetricsSnapshot(data);
});

export function connectMetricsStream() {
  if (!metricsSocket.connected) {
    console.log('[metricsSocket] Connecting to /metrics namespace...');
    metricsSocket.connect();
  }
}

export function disconnectMetricsStream() {
  if (metricsSocket.connected) {
    console.log('[metricsSocket] Disconnecting from /metrics namespace...');
    metricsSocket.disconnect();
  }
}
