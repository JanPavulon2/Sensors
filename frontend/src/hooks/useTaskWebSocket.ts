/**
 * Custom React hook for managing WebSocket connection to task monitoring endpoint
 *
 * Handles:
 * - Connection lifecycle (connect, disconnect, reconnect)
 * - Message parsing and validation
 * - Store updates via Zustand
 * - Automatic reconnection with exponential backoff
 * - Memory cleanup on unmount
 *
 * IMPORTANT IMPLEMENTATION NOTES:
 * This hook uses refs strategically to prevent infinite reconnection loops caused by stale closures.
 *
 * THE PROBLEM:
 * - WebSocket event handlers (onopen, onclose, etc.) capture variables when created
 * - If `connect()` is recreated on every state change, old handlers still reference old closures
 * - This causes: state change → connect recreates → effect re-runs → new connection → state change → LOOP
 *
 * THE SOLUTION:
 * 1. Use refs for reconnection logic values (retryCount, autoReconnect, etc.)
 *    - Refs maintain current values without triggering re-renders
 *    - Closures can read latest values from refs without being recreated
 *
 * 2. Keep connect() dependencies minimal and stable
 *    - Only depend on: enabled, url, handleMessage
 *    - Do NOT depend on state that changes during operation (retryCount, isConnected, etc.)
 *
 * 3. Use mountedRef to ensure single connection attempt per mount
 *    - Prevents multiple simultaneous connection attempts
 *    - useEffect depends only on 'enabled', not 'connect'
 *
 * 4. Access Zustand store directly via getState()
 *    - Avoids adding store methods to dependency arrays
 *    - Store methods from useTaskStore() might not be stable references
 *    - Using getState() ensures we always get fresh store instance
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
  const mountedRef = useRef(false);

  // Use refs for values that need to be accessed in closures but shouldn't trigger re-creation
  const retryCountRef = useRef(0);
  const autoReconnectRef = useRef(autoReconnect);
  const reconnectDelayRef = useRef(reconnectDelay);
  const maxReconnectAttemptsRef = useRef(maxReconnectAttempts);

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  // Update refs when props change (but don't recreate connect function)
  autoReconnectRef.current = autoReconnect;
  reconnectDelayRef.current = reconnectDelay;
  maxReconnectAttemptsRef.current = maxReconnectAttempts;

  // Define handleMessage first so it can be used in connect
  // Access store directly inside the handler to avoid dependency issues
  const handleMessage = useCallback((message: TaskWebSocketMessage) => {
    const { type } = message;
    const store = useTaskStore.getState();

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
  }, []); // No dependencies - we get fresh store state each time

  const connect = useCallback(() => {
    // Guard: Don't connect if disabled, already connected, or already connecting
    if (!enabled || websocketRef.current !== null) {
      return;
    }

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
        retryCountRef.current = 0;
        useTaskStore.getState().setConnected(true);

        // Request initial data immediately
        ws.send(JSON.stringify({ command: "get_stats" }));
        ws.send(JSON.stringify({ command: "get_all" }));
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
        setError("WebSocket connection error");
      };

      ws.onclose = () => {
        console.log("[TaskMonitor] WebSocket disconnected");
        setIsConnected(false);
        setIsConnecting(false);
        useTaskStore.getState().setConnected(false);
        websocketRef.current = null;

        // Auto-reconnect logic using refs to avoid stale closures
        const currentRetryCount = retryCountRef.current;
        const shouldReconnect = autoReconnectRef.current && currentRetryCount < maxReconnectAttemptsRef.current;

        if (shouldReconnect) {
          const delay = reconnectDelayRef.current * Math.pow(2, currentRetryCount);
          console.log(
            `[TaskMonitor] Reconnecting in ${delay}ms (attempt ${currentRetryCount + 1}/${maxReconnectAttemptsRef.current})`
          );

          // Increment retry count
          retryCountRef.current = currentRetryCount + 1;
          setRetryCount(currentRetryCount + 1);

          // Schedule reconnection
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (currentRetryCount >= maxReconnectAttemptsRef.current) {
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
    url,
    handleMessage,
  ]); // Only include stable values - NOT state that changes during reconnection

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
  // NOTE: We do NOT include 'connect' in the dependency array because:
  // - 'connect' is recreated whenever retryCount/state changes
  // - Including it would cause the effect to re-run constantly
  // - This creates an infinite loop of connection attempts
  // - Instead, we use mountedRef to ensure connect() is called only once per mount
  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Only attempt to connect once per component mount
    if (!mountedRef.current) {
      mountedRef.current = true;
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
  }, [enabled]); // Only depend on 'enabled' to prevent infinite re-runs when 'connect' is recreated

  return {
    isConnected,
    isConnecting,
    error,
    retryCount,
    sendCommand,
  };
}
