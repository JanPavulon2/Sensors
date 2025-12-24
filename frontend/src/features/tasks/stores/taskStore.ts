/**
 * Zustand store for managing task state and history
 *
 * Provides:
 * - Real-time task updates via WebSocket
 * - Task filtering and searching
 * - Statistics and metrics
 * - Circular buffer to prevent memory leaks
 */

import { create } from "zustand";
import type { Task, TaskStatus, TaskStats, TaskCategory } from "@/shared/types/domain/task";

interface TaskStoreState {
  // Core state
  tasks: Map<number, Task>;
  stats: TaskStats | null;
  isConnected: boolean;

  // Computed/filtered views
  activeTasks: () => Task[];
  completedTasks: () => Task[];
  failedTasks: () => Task[];
  cancelledTasks: () => Task[];
  tasksByCategory: (category: TaskCategory | string) => Task[];
  tasksByStatus: (status: TaskStatus) => Task[];

  // Actions
  addTask: (task: Task) => void;
  updateTask: (id: number, update: Partial<Task>) => void;
  removeTask: (id: number) => void;
  setTasks: (tasks: Task[]) => void;
  setStats: (stats: TaskStats) => void;
  setConnected: (connected: boolean) => void;
  clearCompleted: () => void;
  clearFailed: () => void;
  clear: () => void;
}

const MAX_TASKS = 500; // Circular buffer limit

export const useTaskStore = create<TaskStoreState>((set, get) => ({
  // Initial state
  tasks: new Map(),
  stats: null,
  isConnected: false,

  // Computed getters
  activeTasks: () => {
    const tasks = get().tasks;
    return Array.from(tasks.values()).filter((t) => t.status === "running");
  },

  completedTasks: () => {
    const tasks = get().tasks;
    return Array.from(tasks.values()).filter((t) => t.status === "completed");
  },

  failedTasks: () => {
    const tasks = get().tasks;
    return Array.from(tasks.values()).filter((t) => t.status === "failed");
  },

  cancelledTasks: () => {
    const tasks = get().tasks;
    return Array.from(tasks.values()).filter((t) => t.status === "cancelled");
  },

  tasksByCategory: (category) => {
    const tasks = get().tasks;
    return Array.from(tasks.values()).filter(
      (t) => t.category === category || t.category === String(category)
    );
  },

  tasksByStatus: (status) => {
    const tasks = get().tasks;
    return Array.from(tasks.values()).filter((t) => t.status === status);
  },

  // Action: Add or update a task
  addTask: (task: Task) => {
    set((state) => {
      const newTasks = new Map(state.tasks);
      newTasks.set(task.id, task);

      // Enforce circular buffer limit
      if (newTasks.size > MAX_TASKS) {
        // Remove oldest completed/cancelled tasks first
        const sortedByTime = Array.from(newTasks.values()).sort(
          (a, b) => a.created_timestamp - b.created_timestamp
        );

        // Remove non-running tasks until we're under the limit
        for (const task of sortedByTime) {
          if (task.status !== "running" && newTasks.size > MAX_TASKS) {
            newTasks.delete(task.id);
          }
        }

        // If still over, remove oldest running tasks
        if (newTasks.size > MAX_TASKS) {
          newTasks.delete(sortedByTime[0].id);
        }
      }

      return { tasks: newTasks };
    });
  },

  // Action: Update a task
  updateTask: (id: number, update: Partial<Task>) => {
    set((state) => {
      const task = state.tasks.get(id);
      if (!task) return state;

      const newTasks = new Map(state.tasks);
      newTasks.set(id, { ...task, ...update });
      return { tasks: newTasks };
    });
  },

  // Action: Remove a task
  removeTask: (id: number) => {
    set((state) => {
      const newTasks = new Map(state.tasks);
      newTasks.delete(id);
      return { tasks: newTasks };
    });
  },

  // Action: Replace all tasks (from snapshot)
  setTasks: (tasks: Task[]) => {
    const taskMap = new Map(tasks.map((t) => [t.id, t]));
    set({ tasks: taskMap });
  },

  // Action: Update statistics
  setStats: (stats: TaskStats) => {
    set({ stats });
  },

  // Action: Update connection status
  setConnected: (connected: boolean) => {
    set({ isConnected: connected });
  },

  // Action: Clear completed tasks
  clearCompleted: () => {
    set((state) => {
      const newTasks = new Map(state.tasks);
      for (const [id, task] of newTasks) {
        if (task.status === "completed") {
          newTasks.delete(id);
        }
      }
      return { tasks: newTasks };
    });
  },

  // Action: Clear failed tasks
  clearFailed: () => {
    set((state) => {
      const newTasks = new Map(state.tasks);
      for (const [id, task] of newTasks) {
        if (task.status === "failed") {
          newTasks.delete(id);
        }
      }
      return { tasks: newTasks };
    });
  },

  // Action: Clear all tasks
  clear: () => {
    set({ tasks: new Map() });
  },
}));
