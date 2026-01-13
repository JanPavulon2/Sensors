/**
 * Task types and interfaces for real-time task monitoring
 *
 * These types represent the async tasks running in the backend application,
 * including their lifecycle, status, and hierarchy.
 */

export type TaskCategory =
  | "API"
  | "HARDWARE"
  | "RENDER"
  | "ANIMATION"
  | "INPUT"
  | "EVENTBUS"
  | "TRANSITION"
  | "SYSTEM"
  | "BACKGROUND"
  | "GENERAL";

export type TaskStatus = "running" | "completed" | "failed" | "cancelled";

export interface Task {
  id: number;
  category: TaskCategory | string;
  description: string;
  created_at: string;
  created_timestamp: number;
  created_by?: string;
  parent_task_id?: number;
  status: TaskStatus;
  error?: string;
  finished_at?: string;
  finished_timestamp?: number;
  duration?: number;
  children?: Task[];
  origin_stack?: string;
}

export interface TaskStats {
  total: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  avg_running_duration: number;
  avg_completed_duration: number;
  categories: Record<string, number>;
}

export interface TaskTree {
  tasks: Task[];
  total: number;
}

/**
 * WebSocket message types for task monitoring
 */
export type TaskWebSocketMessageType =
  | "task:created"
  | "task:updated"
  | "task:completed"
  | "task:failed"
  | "task:cancelled"
  | "tasks:snapshot"
  | "tasks:stats"
  | "tasks:all"
  | "tasks:active"
  | "tasks:tree";

export interface TaskWebSocketMessage {
  type: TaskWebSocketMessageType;
  task?: Task;
  tasks?: Task[];
  stats?: TaskStats;
  tree?: TaskTree;
  timestamp?: string;
}
