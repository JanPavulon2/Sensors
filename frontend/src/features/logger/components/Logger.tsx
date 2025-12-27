/**
 * Logger Component
 * Main real-time logger display with WebSocket integration
 */

import { useLoggerWebSocket } from '@/features/logger/hooks/useLoggerWebSocket';
import { LogViewer } from './LogViewer';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/ui/card';
import { AlertCircle } from 'lucide-react';

interface LoggerProps {
  /**
   * Enable/disable WebSocket connection
   */
  enabled?: boolean;
  /**
   * Custom max height for log viewer
   */
  maxHeight?: string;
}

export function Logger({
  enabled = true,
  maxHeight = 'h-96',
}: LoggerProps): JSX.Element {
  const { isConnected } = useLoggerWebSocket({ enabled });

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

      <CardContent>
        <LogViewer maxHeight={maxHeight} />
      </CardContent>
    </Card>
  );
}

export default Logger;
