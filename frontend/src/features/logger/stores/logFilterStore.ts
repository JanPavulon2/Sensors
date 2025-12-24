/**
 * Logger Filter Store
 * Manages per-category log level filters
 * Store in localStorage for persistence
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { LogLevel } from '@/types/logger';

interface LogFilterStoreState {
  filters: Map<string, LogLevel>;
  setFilter: (category: string, level: LogLevel) => void;
  removeFilter: (category: string) => void;
  addCategory: (category: string, level: LogLevel) => void;
  hideCategory: (category: string) => void;
  showCategory: (category: string, level: LogLevel) => void;
  getFilter: (category: string) => LogLevel | undefined;
  isHidden: (category: string) => boolean;
  resetFilters: () => void;
}

// Default filters: show all categories at DEBUG level
const DEFAULT_FILTERS: Record<string, LogLevel> = {
  ZONE: 'DEBUG',
  COLOR: 'DEBUG',
  RENDER_ENGINE: 'DEBUG',
  ANIMATION: 'DEBUG',
  CONTROLLER: 'DEBUG',
};

export const useLogFilterStore = create<LogFilterStoreState>()(
  persist(
    (set, get) => ({
      filters: new Map(Object.entries(DEFAULT_FILTERS)),

      setFilter: (category: string, level: LogLevel) =>
        set((state) => {
          const newFilters = new Map(state.filters);
          newFilters.set(category, level);
          return { filters: newFilters };
        }),

      removeFilter: (category: string) =>
        set((state) => {
          const newFilters = new Map(state.filters);
          newFilters.delete(category);
          return { filters: newFilters };
        }),

      addCategory: (category: string, level: LogLevel) =>
        set((state) => {
          const newFilters = new Map(state.filters);
          newFilters.set(category, level);
          return { filters: newFilters };
        }),

      hideCategory: (category: string) => {
        get().removeFilter(category);
      },

      showCategory: (category: string, level: LogLevel = 'DEBUG') => {
        get().addCategory(category, level);
      },

      getFilter: (category: string) => {
        return get().filters.get(category);
      },

      isHidden: (category: string) => {
        return !get().filters.has(category);
      },

      resetFilters: () =>
        set({ filters: new Map(Object.entries(DEFAULT_FILTERS)) }),
    }),
    {
      name: 'diuna-log-filters',
      storage: {
        getItem: (name: string) => {
          const item = localStorage.getItem(name);
          if (!item) return null;
          try {
            const parsed = JSON.parse(item);
            return {
              ...parsed,
              state: {
                ...parsed.state,
                filters: new Map(parsed.state.filters || []),
              },
            };
          } catch {
            return null;
          }
        },
        setItem: (name: string, value: any) => {
          const toStore = {
            ...value,
            state: {
              ...value.state,
              filters: Array.from(value.state.filters.entries()),
            },
          };
          localStorage.setItem(name, JSON.stringify(toStore));
        },
        removeItem: (name: string) => localStorage.removeItem(name),
      },
    }
  )
);
