/**
 * Logger Component
 * Main real-time logger display with WebSocket integration
 */

import { useLoggerWebSocket } from '@/features/logger/hooks/useLoggerWebSocket';
import { LogViewer } from './LogViewer';
import { LogFilterPanel } from './LogFilterPanel';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/ui/card';
import { Zap, AlertCircle } from 'lucide-react';

interface LoggerProps {
  /**
   * Enable/disable WebSocket connection
   */
  enabled?: boolean;
  /**
   * Custom WebSocket URL
   */
  wsUrl?: string;
  /**
   * Custom max height for log viewer
   */
  maxHeight?: string;
}

export function Logger({
  enabled = true,
  wsUrl,
  maxHeight = 'h-96',
}: LoggerProps): JSX.Element {
  const { isConnected } = useLoggerWebSocket({ enabled, url: wsUrl });

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle>Real-Time Logger</CardTitle>
            <div
              className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success' : 'bg-warning'}`}
              title={isConnected ? 'Connected' : 'Disconnected'}
            />
          </div>
          {!isConnected && (
            <div className="flex items-center gap-1 text-xs text-warning">
              <AlertCircle className="w-3 h-3" />
              <span>Reconnecting...</span>
            </div>
          )}
        </div>
        <CardDescription>
          Real-time view of backend logs with per-category level filtering
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Filter Panel */}
        <LogFilterPanel isCollapsible={true} />

        {/* Log Viewer */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            <p className="text-sm font-medium text-foreground">Logs</p>
          </div>
          <LogViewer maxHeight={maxHeight} />
        </div>
      </CardContent>
    </Card>
  );
}

export default Logger;
