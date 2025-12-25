/**
 * Logger Stream Store
 * Manages real-time log entries from WebSocket stream
 * This store is specifically for streaming data (not REST API data)
 */

import { create } from 'zustand';
import type { LogEntry } from '@/shared/types/domain/logger';

const MAX_LOGS = 1000; // Circular buffer size

interface LoggerStreamStoreState {
  logs: LogEntry[];
  addLog: (log: LogEntry) => void;
  clearLogs: () => void;
  setMaxLogs: (max: number) => void;
  maxLogs: number;
}

export const useLoggerStreamStore = create<LoggerStreamStoreState>((set) => ({
  logs: [],
  maxLogs: MAX_LOGS,

  addLog: (log: LogEntry) =>
    set((state) => {
      const newLogs = [...state.logs, log];
      // Keep only the last maxLogs entries (circular buffer)
      if (newLogs.length > state.maxLogs) {
        newLogs.shift();
      }
      return { logs: newLogs };
    }),

  clearLogs: () => set({ logs: [] }),

  setMaxLogs: (max: number) => set({ maxLogs: max }),
}));
