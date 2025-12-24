/**
 * Log Filter Panel Component
 * UI for configuring per-category log level filters
 */

import { useMemo } from 'react';
import { useLoggerStore } from '@/features/logger/stores/loggerStore';
import { useLogFilterStore } from '@/features/logger/stores/logFilterStore';
import { useLogCategories } from '@/features/logger/hooks/useLogCategories';
import type { LogLevel } from '@/shared/types/domain/logger';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

const LOG_LEVELS: LogLevel[] = ['DEBUG', 'INFO', 'WARN', 'ERROR'];

interface LogFilterPanelProps {
  isCollapsible?: boolean;
}

export function LogFilterPanel({ isCollapsible = true }: LogFilterPanelProps): JSX.Element {
  const [isExpanded, setIsExpanded] = useState(!isCollapsible);
  const logs = useLoggerStore((state) => state.logs);
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

  if (!isCollapsible || !isExpanded) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsExpanded(true)}
        className="w-full justify-between"
      >
        Filters {isCollapsible && <ChevronDown className="w-4 h-4" />}
      </Button>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Log Filters</CardTitle>
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" onClick={handleShowAll}>
              Show All
            </Button>
            <Button size="sm" variant="ghost" onClick={handleHideAll}>
              Hide All
            </Button>
            <Button size="sm" variant="ghost" onClick={resetFilters}>
              Reset
            </Button>
            {isCollapsible && (
              <button onClick={() => setIsExpanded(false)} className="p-1">
                <ChevronUp className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
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
                {/* Category Name */}
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

                {/* Log Level Selector */}
                {!isHidden && (
                  <select
                    value={currentLevel}
                    onChange={(e) => setFilter(category, e.target.value as LogLevel)}
                    className="ml-2 px-2 py-1 text-xs rounded bg-background border border-border text-foreground"
                  >
                    {LOG_LEVELS.map((level) => (
                      <option key={level} value={level}>
                        {level}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            );
          })
        )}

        <p className="text-xs text-muted-foreground pt-2">
          Tip: Uncheck to hide a category completely, or adjust the level dropdown to filter by
          severity
        </p>
      </CardContent>
    </Card>
  );
}

export default LogFilterPanel;
