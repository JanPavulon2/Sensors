/**
 * Log Filter Panel Component
 * UI for configuring per-category log level filters
 */

import { useMemo } from 'react';
import { useLoggerStreamStore } from '@/features/logger/stores/loggerStreamStore';
import { useLogFilterStore } from '@/features/logger/stores/logFilterStore';
import { useLogCategories } from '@/features/logger/hooks/useLogCategories';
import type { LogLevel } from '@/shared/types/domain/logger';
import { Button } from '@/shared/ui/button';

const LOG_LEVELS: LogLevel[] = ['DEBUG', 'INFO', 'WARN', 'ERROR'];

export function LogFilterPanel(): JSX.Element {
  const logs = useLoggerStreamStore((state) => state.logs);
  const filters = useLogFilterStore((state) => state.filters);
  const setFilter = useLogFilterStore((state) => state.setFilter);
  const hideCategory = useLogFilterStore((state) => state.hideCategory);
  const showCategory = useLogFilterStore((state) => state.showCategory);
  const resetFilters = useLogFilterStore((state) => state.resetFilters);
  const { data: categoriesData } = useLogCategories();

  // Get unique categories from logs + API data
  const allCategories = useMemo(() => {
    const fromLogs = new Set(logs.map((log) => log.category));
    const fromApi = new Set(categoriesData?.categories || []);
    return Array.from(new Set([...fromLogs, ...fromApi])).sort();
  }, [logs, categoriesData]);

  const handleShowAll = () => {
    allCategories.forEach((category) => {
      showCategory(category, 'DEBUG');
    });
  };

  const handleHideAll = () => {
    allCategories.forEach((category) => {
      hideCategory(category);
    });
  };

  return (
    <div className="p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 pb-2 border-b border-border">
        <h4 className="text-sm font-semibold">Filter by Category</h4>
        <div className="flex gap-1">
          <Button size="sm" variant="ghost" onClick={handleShowAll} className="text-xs h-7">
            All
          </Button>
          <Button size="sm" variant="ghost" onClick={handleHideAll} className="text-xs h-7">
            None
          </Button>
          <Button size="sm" variant="ghost" onClick={resetFilters} className="text-xs h-7">
            Reset
          </Button>
        </div>
      </div>

      {/* Filter controls */}
      {allCategories.length === 0 ? (
        <p className="text-xs text-muted-foreground">No categories found</p>
      ) : (
        allCategories.map((category) => {
          const isHidden = !filters.has(category);
          const currentLevel = filters.get(category) || 'DEBUG';

          return (
            <div
              key={category}
              className="flex items-center justify-between p-2 rounded bg-muted/50 hover:bg-muted transition-colors"
            >
              <label className="flex items-center gap-2 flex-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={!isHidden}
                  onChange={(e) => {
                    if (e.target.checked) {
                      showCategory(category, 'DEBUG');
                    } else {
                      hideCategory(category);
                    }
                  }}
                  className="rounded border-border"
                />
                <span className="text-xs font-medium text-foreground">{category}</span>
              </label>

              <select
                value={currentLevel}
                onChange={(e) => setFilter(category, e.target.value as LogLevel)}
                disabled={isHidden}
                className="ml-2 px-2 py-1 text-xs rounded bg-background border border-border text-foreground disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {LOG_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </div>
          );
        })
      )}
    </div>
  );
}

export default LogFilterPanel;
