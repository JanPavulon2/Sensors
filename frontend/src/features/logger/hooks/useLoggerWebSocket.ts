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

import { useEffect, useState } from 'react';
import { socket } from '@/realtime/socket';
import { useLoggerStreamStore } from '@/features/logger/stores/loggerStreamStore';
import type { LogEntry, LogLevel } from '@/shared/types/domain/logger';

interface UseLoggerWebSocketOptions {
  enabled?: boolean;
}

// Register log:entry listener ONCE at module level to avoid duplicates
// This listener stays active permanently to capture logs even when tab is inactive
let logEntryListenerRegistered = false;

const registerLogEntryListener = () => {
  if (logEntryListenerRegistered) return;

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

      // Add to store using getState() to always get fresh store instance
      const store = useLoggerStreamStore.getState();
      store.addLog(log);
    } catch (error) {
      console.error('Failed to process log entry:', error);
    }
  });

  logEntryListenerRegistered = true;
};

/**
 * Connect to Socket.IO for real-time log streaming
 * Listens to 'log:entry' events from the backend
 */
export const useLoggerWebSocket = ({
  enabled = true,
}: UseLoggerWebSocketOptions = {}) => {
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!enabled) return;

    // Register the permanent log:entry listener once
    registerLogEntryListener();

    // Connection established
    const handleConnect = () => {
      console.log('✓ Logger Socket.IO connected');
      setIsConnected(true);
      // Request log history on first connect
      socket.emit('logs_request_history', { limit: 500 });
    };

    // Listen to log history response
    const handleLogHistory = (data: unknown) => {
      try {
        const historyData = data as { logs: any[] };
        if (!Array.isArray(historyData.logs)) {
          console.warn('Invalid log history format:', data);
          return;
        }

        const store = useLoggerStreamStore.getState();

        // Add historical logs in order (oldest to newest)
        historyData.logs.forEach((logData: any) => {
          const level = (['DEBUG', 'INFO', 'WARN', 'ERROR'].includes(logData.level as string)
            ? logData.level
            : 'INFO') as LogLevel;

          const log: LogEntry = {
            id: `history-${logData.timestamp}-${Math.random()}`,
            timestamp: (logData.timestamp as string) || new Date().toISOString(),
            level,
            category: (logData.category as string) || 'UNKNOWN',
            message: (logData.message as string) || '',
          };
          store.addLog(log);
        });

        console.log(`✓ Loaded ${historyData.logs.length} historical logs`);
      } catch (error) {
        console.error('Failed to process log history:', error);
      }
    };

    // Connection lost
    const handleDisconnect = (reason: string) => {
      console.log(`Logger Socket.IO disconnected: ${reason}`);
      setIsConnected(false);
    };

    // Connection error
    const handleConnectError = (error: unknown) => {
      console.error('Logger Socket.IO connection error:', error);
    };

    // Register listeners on shared socket
    socket.on('connect', handleConnect);
    socket.on('logs:history', handleLogHistory);
    socket.on('disconnect', handleDisconnect);
    socket.on('connect_error', handleConnectError);

    // Set initial connection state
    setIsConnected(socket.connected);

    return () => {
      // Cleanup: Only unregister connect/disconnect handlers
      // log:entry listener stays active permanently
      socket.off('connect', handleConnect);
      socket.off('logs:history', handleLogHistory);
      socket.off('disconnect', handleDisconnect);
      socket.off('connect_error', handleConnectError);
    };
  }, [enabled]);

  return {
    isConnected,
    socket,
  };
};
