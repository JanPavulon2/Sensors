/**
 * WebSocket Service
 * Handles real-time bidirectional communication with the backend
 */

import { io, Socket } from 'socket.io-client';
import { config } from '@/config/constants';

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = config.websocket.reconnectAttempts;

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.socket?.connected) {
      console.log('[WebSocket] Already connected');
      return;
    }

    this.socket = io(config.websocket.url, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: config.websocket.reconnectDelay,
      reconnectionAttempts: this.maxReconnectAttempts,
    });

    this.setupListeners();
  }

  /**
   * Setup default listeners for connection events
   */
  private setupListeners(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('[WebSocket] Connected');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason: string) => {
      console.log('[WebSocket] Disconnected:', reason);
    });

    this.socket.on('error', (error: Error) => {
      console.error('[WebSocket] Error:', error);
    });

    this.socket.on('reconnect_attempt', () => {
      this.reconnectAttempts += 1;
      console.log(`[WebSocket] Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
    });
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  /**
   * Subscribe to zone state changes
   */
  onZoneStateChanged(callback: (data: unknown) => void): void {
    this.socket?.on('zone:state_changed', callback);
  }

  /**
   * Subscribe to animation events
   */
  onAnimationStarted(callback: (data: unknown) => void): void {
    this.socket?.on('animation:started', callback);
  }

  onAnimationStopped(callback: (data: unknown) => void): void {
    this.socket?.on('animation:stopped', callback);
  }

  /**
   * Subscribe to frame updates (60 FPS)
   */
  onFrameUpdate(callback: (data: unknown) => void): void {
    this.socket?.on('frame:update', callback);
  }

  /**
   * Send zone color command
   */
  setZoneColor(zoneId: string, color: unknown): void {
    this.socket?.emit('zone:set_color', { zone_id: zoneId, color });
  }

  /**
   * Send zone brightness command
   */
  setZoneBrightness(zoneId: string, brightness: number): void {
    this.socket?.emit('zone:set_brightness', { zone_id: zoneId, brightness });
  }

  /**
   * Start animation
   */
  startAnimation(animationId: string, params?: Record<string, unknown>): void {
    this.socket?.emit('animation:start', { animation_id: animationId, params });
  }

  /**
   * Stop animation
   */
  stopAnimation(animationId: string): void {
    this.socket?.emit('animation:stop', { animation_id: animationId });
  }

  /**
   * Disconnect WebSocket
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      console.log('[WebSocket] Disconnected');
    }
  }
}

export const websocketService = new WebSocketService();
export default websocketService;
