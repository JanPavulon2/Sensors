/**
 * Custom React hook for managing WebSocket connection to task monitoring endpoint
 *
 * Handles:
 * - Connection lifecycle (connect, disconnect, reconnect)
 * - Message parsing and validation
 * - Store updates via Zustand
 * - Automatic reconnection with exponential backoff
 * - Memory cleanup on unmount
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { useTaskStore } from "@/stores/taskStore";
import { config } from "@/config/constants";
import type { TaskWebSocketMessage } from "@/types/task";

interface UseTaskWebSocketOptions {
  enabled?: boolean;
  url?: string;
  autoReconnect?: boolean;
  reconnectDelay?: number;
  maxReconnectAttempts?: number;
}

interface UseTaskWebSocketReturn {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  retryCount: number;
  sendCommand: (command: Record<string, any>) => void;
}

// Build WebSocket URL for tasks from base WebSocket URL
const getTasksWebSocketUrl = (): string => {
  // Get base WebSocket URL from config (handles env vars + auto-detection)
  const baseUrl = config.websocket.url; // e.g., "ws://localhost:8000"

  // Append /ws/tasks path
  return `${baseUrl}/ws/tasks`;
};

const DEFAULT_URL = getTasksWebSocketUrl();
const DEFAULT_RECONNECT_DELAY = config.websocket.reconnectDelay;
const DEFAULT_MAX_RECONNECT = config.websocket.reconnectAttempts;

export function useTaskWebSocket(
  options: UseTaskWebSocketOptions = {}
): UseTaskWebSocketReturn {
  const {
    enabled = true,
    url = DEFAULT_URL,
    autoReconnect = true,
    reconnectDelay = DEFAULT_RECONNECT_DELAY,
    maxReconnectAttempts = DEFAULT_MAX_RECONNECT,
  } = options;

  const websocketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const store = useTaskStore();

  const connect = useCallback(() => {
    if (!enabled || isConnected || isConnecting) return;

    setIsConnecting(true);
    setError(null);

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log("[TaskMonitor] WebSocket connected");
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
        setRetryCount(0);
        store.setConnected(true);

        // Server automatically sends initial snapshot and stats
        // No need to request here - it avoids race conditions
      };

      ws.onmessage = (event) => {
        try {
          const message: TaskWebSocketMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (err) {
          console.error("[TaskMonitor] Failed to parse message:", err);
        }
      };

      ws.onerror = (event) => {
        // Note: onerror doesn't provide detailed info, onclose will be called after
        console.error("[TaskMonitor] WebSocket error event:", event);
        // Only set error if we haven't already
        if (!error) {
          setError("WebSocket connection error");
        }
      };

      ws.onclose = () => {
        console.log("[TaskMonitor] WebSocket disconnected");
        setIsConnected(false);
        setIsConnecting(false);
        store.setConnected(false);
        websocketRef.current = null;

        // Auto-reconnect logic
        if (autoReconnect && retryCount < maxReconnectAttempts) {
          const delay = reconnectDelay * Math.pow(2, retryCount); // Exponential backoff
          console.log(
            `[TaskMonitor] Reconnecting in ${delay}ms (attempt ${retryCount + 1}/${maxReconnectAttempts})`
          );

          setRetryCount((prev) => prev + 1);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (retryCount >= maxReconnectAttempts) {
          setError(
            "Max reconnection attempts reached. Please refresh the page."
          );
        }
      };

      websocketRef.current = ws;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      console.error("[TaskMonitor] Connection error:", errorMsg);
      setError(errorMsg);
      setIsConnecting(false);
    }
  }, [
    enabled,
    isConnected,
    isConnecting,
    url,
    autoReconnect,
    reconnectDelay,
    maxReconnectAttempts,
    retryCount,
    store,
  ]);

  const handleMessage = (message: TaskWebSocketMessage) => {
    const { type } = message;

    switch (type) {
      case "task:created":
      case "task:updated":
        if (message.task) {
          store.addTask(message.task);
        }
        break;

      case "task:completed":
      case "task:failed":
      case "task:cancelled":
        if (message.task) {
          store.updateTask(message.task.id, {
            status: message.task.status,
            finished_at: message.task.finished_at,
            finished_timestamp: message.task.finished_timestamp,
            duration: message.task.duration,
            error: message.task.error,
          });
        }
        break;

      case "tasks:snapshot":
      case "tasks:all":
      case "tasks:active":
        if (message.tasks) {
          store.setTasks(message.tasks);
        }
        break;

      case "tasks:stats":
        if (message.stats) {
          store.setStats(message.stats);
        }
        break;

      case "tasks:tree":
        // Tree data received, could be used for hierarchical view
        if (message.tree) {
          console.log("[TaskMonitor] Task tree received:", message.tree);
          // TODO: Store tree data if needed for tree view
        }
        break;

      default:
        console.warn("[TaskMonitor] Unknown message type:", type);
    }
  };

  const sendCommand = useCallback(
    (command: Record<string, any>) => {
      if (!websocketRef.current || !isConnected) {
        console.warn("[TaskMonitor] WebSocket not connected");
        return;
      }

      try {
        websocketRef.current.send(JSON.stringify(command));
      } catch (err) {
        console.error("[TaskMonitor] Failed to send command:", err);
      }
    },
    [isConnected]
  );

  // Connect on mount (if enabled)
  useEffect(() => {
    if (enabled) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (websocketRef.current) {
        websocketRef.current.close();
      }
    };
  }, [enabled, connect]);

  return {
    isConnected,
    isConnecting,
    error,
    retryCount,
    sendCommand,
  };
}
