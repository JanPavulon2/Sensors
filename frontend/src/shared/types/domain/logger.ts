/**
 * Logger Types
 * Real-time logging system for backend events
 */

export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';

export interface LogEntry {
  id: string; // unique identifier
  timestamp: string; // ISO 8601 datetime
  level: LogLevel;
  category: string; // e.g., 'ZONE', 'COLOR', 'RENDER_ENGINE'
  message: string;
}

export interface LogFilter {
  /**
   * Per-category filtering
   * key: category name
   * value: minimum log level to show (DEBUG < INFO < WARN < ERROR)
   * If category not in map, it's considered "hidden"
   */
  categories: Map<string, LogLevel>;
}

export const LOG_LEVEL_ORDER: Record<LogLevel, number> = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
};

export const LOG_LEVEL_COLORS: Record<LogLevel, string> = {
  DEBUG: '#7a8899', // zinc 500
  INFO: '#06b6d4', // cyan
  WARN: '#f59e0b', // amber
  ERROR: '#ef4444', // red
};

/**
 * Check if log should be displayed based on filter
 */
export function shouldShowLog(log: LogEntry, filters: Map<string, LogLevel>): boolean {
  // If category not in filter map, it's hidden
  if (!filters.has(log.category)) {
    return false;
  }

  const minLevel = filters.get(log.category)!;
  return LOG_LEVEL_ORDER[log.level] >= LOG_LEVEL_ORDER[minLevel];
}
