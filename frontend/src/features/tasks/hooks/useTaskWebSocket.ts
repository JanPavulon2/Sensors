/**
 * Socket.IO hook for managing real-time task updates
 * Migrated from raw WebSocket to Socket.IO for unified communication
 *
 * Handles:
 * - Socket.IO connection lifecycle (connect, disconnect, reconnect)
 * - Task event listening (creation, updates, completion)
 * - Task command emission (get_all, get_stats, etc.)
 * - Store updates via Zustand
 * - Automatic reconnection with exponential backoff
 * - Memory cleanup on unmount
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
 * 1. Use handleTaskEvent callback with useTaskStreamStore.getState() to get fresh store state
 *    - Avoids adding store methods to dependency arrays
 *    - Using getState() ensures we always get the current store instance
 *
 * 2. Keep effect dependencies minimal and stable
 *    - Only depend on: enabled
 *    - Do NOT depend on state that changes during operation (isConnected, etc.)
 *
 * 3. Use refs for Socket.IO instance to ensure single connection
 *    - Prevents multiple simultaneous Socket.IO connections
 *    - Refs maintain current values without triggering re-renders
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { io, Socket } from "socket.io-client";
import { useTaskStreamStore } from "@/features/tasks/stores/taskStreamStore";
import { config } from "@/config/constants";
import type { Task, TaskStats } from "@/shared/types/domain/task";

interface UseTaskWebSocketOptions {
  enabled?: boolean;
}

interface UseTaskWebSocketReturn {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  retryCount: number;
  sendCommand: (command: Record<string, any>) => void;
}

export function useTaskWebSocket(
  options: UseTaskWebSocketOptions = {}
): UseTaskWebSocketReturn {
  const { enabled = true } = options;

  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  // Define handleTaskEvent callback that accesses fresh store state
  // This prevents stale closures by always calling getState() instead of capturing methods
  const handleTaskEvent = useCallback((eventType: string, data: unknown) => {
    const store = useTaskStreamStore.getState();

    try {
      switch (eventType) {
        case "task:created":
        case "task:updated": {
          const task = data as Task;
          if (task && typeof task === 'object' && 'id' in task) {
            store.addTask(task);
          } else {
            console.warn("[TaskMonitor] Invalid task data:", data);
          }
          break;
        }

        case "task:completed":
        case "task:failed":
        case "task:cancelled": {
          const task = data as Task;
          if (task && typeof task === 'object' && 'id' in task) {
            store.updateTask(task.id, {
              status: task.status,
              finished_at: task.finished_at,
              finished_timestamp: task.finished_timestamp,
              duration: task.duration,
              error: task.error,
            });
          } else {
            console.warn("[TaskMonitor] Invalid task data:", data);
          }
          break;
        }

        case "tasks:all":
        case "tasks:active": {
          // Handle both array format and wrapped format
          let tasks = data as Task[];
          if (!Array.isArray(tasks)) {
            const wrapped = data as Record<string, unknown>;
            if (Array.isArray(wrapped.tasks)) {
              tasks = wrapped.tasks as Task[];
            } else {
              console.warn("[TaskMonitor] Invalid tasks data format:", data);
              break;
            }
          }
          store.setTasks(tasks);
          break;
        }

        case "tasks:stats": {
          // Handle both direct stats and wrapped stats
          let stats = data as TaskStats;
          if (!stats || typeof stats !== 'object' || !('total' in stats)) {
            const wrapped = data as Record<string, unknown>;
            if (wrapped.stats && typeof wrapped.stats === 'object' && 'total' in wrapped.stats) {
              stats = wrapped.stats as TaskStats;
            } else {
              console.warn("[TaskMonitor] Invalid stats data format:", data);
              break;
            }
          }
          store.setStats(stats);
          break;
        }

        case "tasks:tree":
          // Tree data received, could be used for hierarchical view
          // TODO: Store tree data if needed for tree view
          break;

        default:
          console.warn("[TaskMonitor] Unknown task event type:", eventType);
      }
    } catch (error) {
      console.error("[TaskMonitor] Error handling event:", eventType, error);
    }
  }, []); // No dependencies - we get fresh store state each time

  useEffect(() => {
    if (!enabled) return;

    // Prevent duplicate connections
    if (socketRef.current?.connected) {
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      // Connect to Socket.IO server (same host/port as HTTP frontend)
      // Note: Try polling first as fallback if WebSocket has issues
      const socket = io(config.websocket.url, {
        reconnection: true,
        reconnectionDelay: 3000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: Infinity,
        transports: ["polling", "websocket"], // HTTP polling first, WebSocket fallback
      });

      // Connection established
      socket.on("connect", () => {
        console.log("✓ Task Socket.IO connected");
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
        setRetryCount(0);
        useTaskStreamStore.getState().setConnected(true);

        // Request initial data
        socket.emit("task_get_stats");
        socket.emit("task_get_all");
      });

      // Listen to task push events (real-time updates)
      socket.on("task:created", (task: unknown) => {
        handleTaskEvent("task:created", task);
      });

      socket.on("task:updated", (task: unknown) => {
        handleTaskEvent("task:updated", task);
      });

      socket.on("task:completed", (task: unknown) => {
        handleTaskEvent("task:completed", task);
      });

      socket.on("task:failed", (task: unknown) => {
        handleTaskEvent("task:failed", task);
      });

      socket.on("task:cancelled", (task: unknown) => {
        handleTaskEvent("task:cancelled", task);
      });

      // Listen to task command response events
      socket.on("tasks:all", (tasks: unknown) => {
        handleTaskEvent("tasks:all", tasks);
      });

      socket.on("tasks:active", (tasks: unknown) => {
        handleTaskEvent("tasks:active", tasks);
      });

      socket.on("tasks:stats", (stats: unknown) => {
        handleTaskEvent("tasks:stats", stats);
      });

      socket.on("tasks:tree", (tree: unknown) => {
        handleTaskEvent("tasks:tree", tree);
      });

      // Connection lost
      socket.on("disconnect", (reason) => {
        console.log(`Task Socket.IO disconnected: ${reason}`);
        setIsConnected(false);
        setIsConnecting(false);
        useTaskStreamStore.getState().setConnected(false);
      });

      // Connection error
      socket.on("connect_error", (connectError: unknown) => {
        const errorMsg = connectError instanceof Error ? connectError.message : String(connectError);
        console.error("Task Socket.IO connection error:", errorMsg);
        setError(errorMsg);
        setIsConnecting(false);
        setRetryCount((count) => count + 1);
      });

      socketRef.current = socket;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      console.error("Failed to create Task Socket.IO connection:", errorMsg);
      setError(errorMsg);
      setIsConnecting(false);
    }

    return () => {
      // Cleanup on unmount - unregister all listeners and disconnect
      if (socketRef.current) {
        socketRef.current.off("connect");
        socketRef.current.off("task:created");
        socketRef.current.off("task:updated");
        socketRef.current.off("task:completed");
        socketRef.current.off("task:failed");
        socketRef.current.off("task:cancelled");
        socketRef.current.off("tasks:all");
        socketRef.current.off("tasks:active");
        socketRef.current.off("tasks:stats");
        socketRef.current.off("tasks:tree");
        socketRef.current.off("disconnect");
        socketRef.current.off("connect_error");
        socketRef.current.disconnect();
        socketRef.current = null;
        setIsConnected(false);
      }
    };
  }, [enabled, handleTaskEvent]); // Only stable dependencies

  const sendCommand = useCallback(
    (command: Record<string, any>) => {
      if (!socketRef.current?.connected) {
        console.warn("[TaskMonitor] Task Socket.IO not connected");
        return;
      }

      try {
        // Map legacy WebSocket command format to Socket.IO events
        const { command: cmd } = command;
        switch (cmd) {
          case "get_all":
            socketRef.current.emit("task_get_all");
            break;
          case "get_active":
            socketRef.current.emit("task_get_active");
            break;
          case "get_stats":
            socketRef.current.emit("task_get_stats");
            break;
          case "get_tree":
            socketRef.current.emit("task_get_tree");
            break;
          default:
            console.warn("[TaskMonitor] Unknown command:", cmd);
        }
      } catch (err) {
        console.error("[TaskMonitor] Failed to send command:", err);
      }
    },
    []
  );

  return {
    isConnected,
    isConnecting,
    error,
    retryCount,
    sendCommand,
  };
}
