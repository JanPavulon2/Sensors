/**
 * Logger WebSocket Hook
 * Manages real-time WebSocket connection for log streaming
 *
 * IMPORTANT IMPLEMENTATION NOTES:
 * This hook uses refs and useCallback to prevent infinite reconnection loops caused by stale closures.
 *
 * THE PROBLEM:
 * - WebSocket event handlers (onopen, onclose, etc.) capture variables when created
 * - If store methods are in the dependency array, the effect re-runs when they change
 * - This causes: state change → effect re-runs → new connection → state change → LOOP
 *
 * THE SOLUTION:
 * 1. Use handleMessage callback with useLoggerStore.getState() to get fresh store state
 *    - Avoids adding store methods to dependency arrays
 *    - Store methods from useLoggerStore() might not be stable references
 *    - Using getState() ensures we always get the current store instance
 *
 * 2. Keep effect dependencies minimal and stable
 *    - Only depend on: enabled, url, handleMessage
 *    - Do NOT depend on state that changes during operation (addLog, etc.)
 *
 * 3. Use refs for reconnection timeout tracking
 *    - Prevents multiple simultaneous connection attempts
 *    - Refs maintain current values without triggering re-renders
 */

import { useEffect, useRef, useCallback } from 'react';
import { useLoggerStore } from '@/stores/loggerStore';
import { config } from '@/config/constants';
import type { LogEntry } from '@/types/logger';

interface UseLoggerWebSocketOptions {
  enabled?: boolean;
  url?: string;
}

/**
 * Connect to WebSocket for real-time log streaming
 * Assumes backend sends logs as JSON messages with structure:
 * { timestamp, level, category, message }
 */
export const useLoggerWebSocket = ({
  enabled = true,
  url = `${config.websocket.url}/ws/logs`,
}: UseLoggerWebSocketOptions = {}) => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Define handleMessage callback that accesses fresh store state
  // This prevents stale closures by always calling getState() instead of capturing addLog
  const handleMessage = useCallback((log: LogEntry) => {
    const store = useLoggerStore.getState();
    store.addLog(log);
  }, []); // No dependencies - we get fresh store state each time

  useEffect(() => {
    if (!enabled) return;

    const connect = () => {
      try {
        wsRef.current = new WebSocket(url);

        wsRef.current.onopen = () => {
          console.log('✓ Logger WebSocket connected');
          // Clear reconnect timeout on successful connection
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
        };

        wsRef.current.onmessage = (event) => {
          try {
            const logData = JSON.parse(event.data);
            const log: LogEntry = {
              id: `${Date.now()}-${Math.random()}`,
              timestamp: logData.timestamp || new Date().toISOString(),
              level: logData.level || 'INFO',
              category: logData.category || 'UNKNOWN',
              message: logData.message || '',
            };
            // Use handleMessage callback instead of directly calling addLog
            // This ensures we always get the latest store instance
            handleMessage(log);
          } catch (error) {
            console.error('Failed to parse log message:', error);
          }
        };

        wsRef.current.onerror = (error) => {
          console.error('Logger WebSocket error:', error);
        };

        wsRef.current.onclose = () => {
          console.log('Logger WebSocket disconnected, attempting reconnect...');
          // Attempt reconnect after 3 seconds
          reconnectTimeoutRef.current = setTimeout(connect, 3000);
        };
      } catch (error) {
        console.error('Failed to connect to logger WebSocket:', error);
        // Attempt reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [enabled, url, handleMessage]); // Only stable dependencies - no store methods

  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    ws: wsRef.current,
  };
};
