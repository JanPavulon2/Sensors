/**
 * Logger WebSocket Hook
 * Manages real-time WebSocket connection for log streaming
 */

import { useEffect, useRef } from 'react';
import { useLoggerStore } from '@/stores/loggerStore';
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
  url = `${import.meta.env.VITE_API_URL?.replace('http', 'ws') || 'ws://localhost:8000'}/ws/logs`,
}: UseLoggerWebSocketOptions = {}) => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const addLog = useLoggerStore((state) => state.addLog);

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
            addLog(log);
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
  }, [enabled, url, addLog]);

  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    ws: wsRef.current,
  };
};
