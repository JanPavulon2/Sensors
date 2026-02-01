import { io } from 'socket.io-client';
import { setOutputFrame } from './frames.store';

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL ?? 'http://localhost:8000';

export const framesSocket = io(`${SOCKET_URL}/frames`, {
  transports: ['websocket'],
  autoConnect: false,  // Manual control
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 500,
});

framesSocket.on('connect', () => {
  console.log('[framesSocket] connected', framesSocket.id);
});

framesSocket.on('disconnect', (reason) => {
  console.warn('[framesSocket] disconnected', reason);
});

framesSocket.on('connect_error', (err) => {
  console.error('[framesSocket] connect_error', err);
});

framesSocket.on('output_frame', (data) => {
  setOutputFrame(data);
});

export function connectFrameStream() {
  console.log('[framesSocket] Connecting to /frames namespace...');
  if (!framesSocket.connected) framesSocket.connect();
}

export function disconnectFrameStream() {
  console.log('[framesSocket] Disconnecting from /frames namespace...');
  if (framesSocket.connected) framesSocket.disconnect();
}