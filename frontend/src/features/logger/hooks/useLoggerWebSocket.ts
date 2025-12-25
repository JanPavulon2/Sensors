/**
 * Logger Stream Hook
 * Manages Socket.IO connection for real-time log streaming
 *
 * IMPORTANT IMPLEMENTATION NOTES:
 * This hook uses refs and useCallback to prevent infinite reconnection loops caused by stale closures.
 *
 * THE PROBLEM:
 * - Socket.IO event handlers capture variables when registered
 * - If store methods are in dependencies, re-registering causes reconnection loops
 * - This causes: state change → effect re-runs → new handlers → reconnect → LOOP
 *
 * THE SOLUTION:
 * 1. Use handleMessage callback with useLoggerStreamStore.getState() to get fresh store state
 *    - Avoids adding store methods to dependency arrays
 *    - Using getState() ensures we always get the current store instance
 *
 * 2. Keep effect dependencies minimal and stable
 *    - Only depend on: enabled
 *    - Do NOT depend on state that changes during operation (addLog, etc.)
 *
 * 3. Use refs for Socket.IO instance to ensure single connection
 *    - Prevents multiple simultaneous Socket.IO connections
 *    - Refs maintain current values without triggering re-renders
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { useLoggerStreamStore } from '@/features/logger/stores/loggerStreamStore';
import { config } from '@/config/constants';
import type { LogEntry, LogLevel } from '@/shared/types/domain/logger';

interface UseLoggerWebSocketOptions {
  enabled?: boolean;
}

/**
 * Connect to Socket.IO for real-time log streaming
 * Listens to 'log:entry' events from the backend
 */
export const useLoggerWebSocket = ({
  enabled = true,
}: UseLoggerWebSocketOptions = {}) => {
  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // Define handleMessage callback that accesses fresh store state
  // This prevents stale closures by always calling getState() instead of capturing addLog
  const handleLogEntry = useCallback((logData: LogEntry) => {
    const store = useLoggerStreamStore.getState();
    store.addLog(logData);
  }, []); // No dependencies - we get fresh store state each time

  useEffect(() => {
    if (!enabled) return;

    // Prevent duplicate connections
    if (socketRef.current?.connected) {
      return;
    }

    try {
      // Connect to Socket.IO server (same host/port as HTTP frontend)
      // Note: Try polling first as fallback if WebSocket has issues
      const socket = io(config.websocket.url, {
        reconnection: true,
        reconnectionDelay: 3000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: Infinity,
        transports: ['polling', 'websocket'], // HTTP polling first, WebSocket fallback
      });

      // Connection established
      socket.on('connect', () => {
        console.log('✓ Logger Socket.IO connected');
        setIsConnected(true);
      });

      // Listen to log entries from backend
      socket.on('log:entry', (logData: unknown) => {
        try {
          // Handle both direct log data and wrapped format
          let data = logData as Record<string, unknown>;
          if (!data || typeof data !== 'object') {
            console.warn('Invalid log entry data:', logData);
            return;
          }

          // Check if data is wrapped in a log property
          if (!('level' in data) && 'log' in data) {
            const wrapped = data.log as Record<string, unknown>;
            if (wrapped && typeof wrapped === 'object') {
              data = wrapped;
            }
          }

          const level = (['DEBUG', 'INFO', 'WARN', 'ERROR'].includes(data.level as string)
            ? data.level
            : 'INFO') as LogLevel;

          const log: LogEntry = {
            id: `${Date.now()}-${Math.random()}`,
            timestamp: (data.timestamp as string) || new Date().toISOString(),
            level,
            category: (data.category as string) || 'UNKNOWN',
            message: (data.message as string) || '',
          };
          // Use handleLogEntry callback to get fresh store instance
          handleLogEntry(log);
        } catch (error) {
          console.error('Failed to process log entry:', error);
        }
      });

      // Connection lost
      socket.on('disconnect', (reason) => {
        console.log(`Logger Socket.IO disconnected: ${reason}`);
        setIsConnected(false);
      });

      // Connection error
      socket.on('connect_error', (error) => {
        console.error('Logger Socket.IO connection error:', error);
      });

      socketRef.current = socket;
    } catch (error) {
      console.error('Failed to create Logger Socket.IO connection:', error);
    }

    return () => {
      // Disconnect on cleanup
      if (socketRef.current) {
        socketRef.current.off('log:entry', handleLogEntry);
        socketRef.current.disconnect();
        socketRef.current = null;
        setIsConnected(false);
      }
    };
  }, [enabled, handleLogEntry]); // Only stable dependencies

  return {
    isConnected,
    socket: socketRef.current,
  };
};
