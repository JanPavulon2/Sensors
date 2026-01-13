import { io, Socket } from 'socket.io-client';

const SOCKET_URL =
  import.meta.env.VITE_SOCKET_URL ?? 'http://localhost:8000';

export const socket: Socket = io(SOCKET_URL, {
  transports: ['websocket'],
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 500,
});


socket.on('connect', () => {
  console.info('[socket] connected', socket.id);
});

socket.on('disconnect', (reason) => {
  console.warn('[socket] disconnected', reason);
});

socket.on('connect_error', (err) => {
  console.error('[socket] connect_error', err);
});