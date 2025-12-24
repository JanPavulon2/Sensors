/**
 * Log Viewer Component
 * Displays real-time log entries with filtering
 */

import { useEffect, useRef, useMemo } from 'react';
import { useLoggerStore } from '@/features/logger/stores/loggerStore';
import { useLogFilterStore } from '@/features/logger/stores/logFilterStore';
import { shouldShowLog, LOG_LEVEL_COLORS } from '@/types/logger';
import { Copy, Trash2 } from 'lucide-react';
import { Button } from '@/shared/ui/button';

interface LogViewerProps {
  maxHeight?: string;
}

export function LogViewer({ maxHeight = 'h-96' }: LogViewerProps): JSX.Element {
  const logs = useLoggerStore((state) => state.logs);
  const clearLogs = useLoggerStore((state) => state.clearLogs);
  const filters = useLogFilterStore((state) => state.filters);
  const endOfLogsRef = useRef<HTMLDivElement>(null);

  // Filter logs based on preferences
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => shouldShowLog(log, filters));
  }, [logs, filters]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    endOfLogsRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [filteredLogs]);

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

  return (
    <div className="flex flex-col h-full gap-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Showing {filteredLogs.length} of {logs.length} logs
        </p>
        <Button size="sm" variant="ghost" onClick={handleClearLogs} disabled={logs.length === 0}>
          <Trash2 className="w-3 h-3 mr-1" />
          Clear
        </Button>
      </div>

      {/* Log Display */}
      <div
        className={`${maxHeight} overflow-y-auto bg-background rounded border border-border p-2 font-mono text-xs space-y-1`}
      >
        {filteredLogs.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            {logs.length === 0 ? 'No logs yet' : 'No logs match current filters'}
          </p>
        ) : (
          filteredLogs.map((log) => (
            <div
              key={log.id}
              className="flex items-start gap-2 p-2 hover:bg-muted rounded group transition-colors"
            >
              {/* Log Level - Colored */}
              <span
                className="font-semibold whitespace-nowrap min-w-fit"
                style={{ color: LOG_LEVEL_COLORS[log.level] }}
              >
                {log.level.padEnd(5)}
              </span>

              {/* Timestamp */}
              <span className="text-muted-foreground whitespace-nowrap min-w-fit">
                {formatTime(log.timestamp)}
              </span>

              {/* Category */}
              <span className="text-primary font-medium min-w-fit">[{log.category}]</span>

              {/* Message */}
              <span className="text-foreground flex-1 break-words">{log.message}</span>

              {/* Copy Button */}
              <button
                onClick={() =>
                  handleCopyLog(
                    `[${log.level}] ${formatTime(log.timestamp)} [${log.category}] ${log.message}`
                  )
                }
                className="opacity-0 group-hover:opacity-100 transition-opacity"
                title="Copy log"
              >
                <Copy className="w-3 h-3 text-muted-foreground hover:text-foreground" />
              </button>
            </div>
          ))
        )}
        <div ref={endOfLogsRef} />
      </div>

      {/* Stats */}
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Buffer: {logs.length} / 1000</span>
        <span>Visible: {filteredLogs.length}</span>
      </div>
    </div>
  );
}

export default LogViewer;
