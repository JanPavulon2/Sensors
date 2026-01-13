/**
 * Log Viewer Component
 * Displays real-time log entries with filtering
 * Newest logs appear at top, auto-scroll only when user is viewing
 */

import { useEffect, useRef, useMemo, useState } from 'react';
import { useLoggerStreamStore } from '@/features/logger/stores/loggerStreamStore';
import { useLogFilterStore } from '@/features/logger/stores/logFilterStore';
import { useLoggerWebSocket } from '@/features/logger/hooks/useLoggerWebSocket';
import { shouldShowLog, LOG_LEVEL_COLORS } from '@/shared/types/domain/logger';
import { Copy, Trash2, FileText, Settings, Wifi, WifiOff } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu';
import { LogFilterPanel } from './LogFilterPanel';

interface LogViewerProps {
  maxHeight?: string;
}

export function LogViewer({ maxHeight = 'h-96' }: LogViewerProps): JSX.Element {
  const logs = useLoggerStreamStore((state) => state.logs);
  const clearLogs = useLoggerStreamStore((state) => state.clearLogs);
  const filters = useLogFilterStore((state) => state.filters);
  const { isConnected } = useLoggerWebSocket({ enabled: true });
  const containerRef = useRef<HTMLDivElement>(null);
  const viewportSentinelRef = useRef<HTMLDivElement>(null);
  const [isLoggerVisible, setIsLoggerVisible] = useState(true);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  // Calculate width for category column (accounts for truncation at 12 chars)
  const maxCategoryWidth = useMemo(() => {
    const categories = new Set(logs.map((log) => log.category));
    let maxWidth = 'UNKNOWN'.length;
    categories.forEach((cat) => {
      maxWidth = Math.max(maxWidth, cat.length);
    });
    // Since we truncate to 12 chars, width is based on truncated length
    // w-16 (~64px) = ~8 chars, w-20 (~80px) = ~10 chars, w-24 (~96px) = ~12 chars
    const truncatedMax = Math.min(maxWidth, 12);
    return truncatedMax > 10 ? 'w-24' : truncatedMax > 8 ? 'w-20' : 'w-16';
  }, [logs]);

  // Filter logs based on preferences
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => shouldShowLog(log, filters));
  }, [logs, filters]);

  // Reverse logs so newest appear at top
  const reversedLogs = useMemo(() => {
    return [...filteredLogs].reverse();
  }, [filteredLogs]);

  // Detect if logger is visible in user's viewport using Intersection Observer
  useEffect(() => {
    if (!viewportSentinelRef.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsLoggerVisible(entry.isIntersecting);
      },
      { threshold: 0.1 } // Trigger when 10% visible
    );

    observer.observe(viewportSentinelRef.current);
    return () => observer.disconnect();
  }, []);

  // Smart auto-scroll: only scroll logger container if user hasn't scrolled down
  const handleContainerScroll = () => {
    if (!containerRef.current) return;
    // If user has scrolled more than 50px from top, disable auto-scroll
    const isNearTop = containerRef.current.scrollTop < 50;
    setShouldAutoScroll(isNearTop);
  };

  // Auto-scroll logger container to top when new logs arrive (only if logger is visible and user hasn't scrolled)
  useEffect(() => {
    if (shouldAutoScroll && isLoggerVisible && containerRef.current) {
      // Scroll only the container, not the page
      containerRef.current.scrollTop = 0;
    }
  }, [reversedLogs, shouldAutoScroll, isLoggerVisible]);

  const handleCopyLog = (log: string) => {
    navigator.clipboard.writeText(log);
  };

  const handleClearLogs = () => {
    if (confirm('Clear all logs?')) {
      clearLogs();
    }
  };

  const formatTime = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return timestamp;
    }
  };

  const truncateCategory = (category: string, maxLength: number = 12): string => {
    if (category.length <= maxLength) {
      return category;
    }
    return category.slice(0, maxLength - 1) + '…';
  };

  return (
    <div className="flex flex-col h-full gap-2">
      {/* Header - Single Line Layout */}
      <div className="flex items-center justify-between">
        {/* Left: Icon + "Logs" */}
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-primary" />
          <p className="text-sm font-medium">Logs</p>
        </div>

        {/* Right: Filters Dropdown + Clear Button */}
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-1 h-7">
                <Settings className="w-3 h-3" />
                Filters
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <LogFilterPanel />
            </DropdownMenuContent>
          </DropdownMenu>
          <Button
            size="sm"
            variant="outline"
            onClick={handleClearLogs}
            disabled={logs.length === 0}
            className="h-7"
          >
            <Trash2 className="w-3 h-3 mr-1" />
            Clear
          </Button>
        </div>
      </div>

      {/* Log Display */}
      <div
        ref={containerRef}
        onScroll={handleContainerScroll}
        className={`${maxHeight} overflow-y-auto bg-background rounded border border-border p-2 font-mono text-xs`}
      >
        {/* Viewport sentinel - detect if logger is visible to user */}
        <div ref={viewportSentinelRef} className="h-0" />

        {filteredLogs.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            {logs.length === 0 ? 'No logs yet' : 'No logs match current filters'}
          </p>
        ) : (
          reversedLogs.map((log) => (
            <div
              key={log.id}
              className="flex items-start gap-1 hover:bg-muted rounded group transition-colors"
            >
              {/* Timestamp - Fixed Width Column (hh:mm:ss) */}
              <span className="text-muted-foreground whitespace-nowrap text-xs w-16 flex-shrink-0">
                {formatTime(log.timestamp)}
              </span>

              {/* Log Level - Fixed Width Column (DEBUG/ERROR) */}
              <span
                className="font-semibold whitespace-nowrap text-xs w-12 flex-shrink-0"
                style={{ color: LOG_LEVEL_COLORS[log.level] }}
              >
                {log.level.padEnd(5)}
              </span>

              {/* Category - Fixed Width Column */}
              <span
                className={`text-primary font-medium text-xs ${maxCategoryWidth} flex-shrink-0 truncate`}
                title={log.category}
              >
                [{truncateCategory(log.category)}]
              </span>

              {/* Message - Flexible */}
              <span className="text-foreground flex-1 break-words text-xs">{log.message}</span>

              {/* Copy Button */}
              <button
                onClick={() =>
                  handleCopyLog(
                    `[${log.level}] ${formatTime(log.timestamp)} [${log.category}] ${log.message}`
                  )
                }
                className="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                title="Copy log"
              >
                <Copy className="w-3 h-3 text-muted-foreground hover:text-foreground" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default LogViewer;
