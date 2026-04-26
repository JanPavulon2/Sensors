/**
 * RenderMetricsPanel — Main container for render metrics visualization.
 *
 * Connects to the /metrics Socket.IO namespace on mount,
 * disconnects on unmount (auto-lifecycle).
 */

import { useEffect } from 'react';
import { Wifi, WifiOff } from 'lucide-react';
import { connectMetricsStream, disconnectMetricsStream } from '../realtime/metrics.socket';
import { useMetricsSnapshot, useMetricsConnected } from '../realtime/metrics.store';

import { FpsGauge } from './FpsGauge';
import { CounterCards } from './CounterCards';
import { PipelineTimingChart } from './PipelineTimingChart';
import { ZoneInsightsTable } from './ZoneInsightsTable';
import { AnimationStatsTable } from './AnimationStatsTable';
import { RenderControls } from './RenderControls';

export function RenderMetricsPanel() {
  const snapshot = useMetricsSnapshot();
  const connected = useMetricsConnected();

  useEffect(() => {
    connectMetricsStream();
    return () => disconnectMetricsStream();
  }, []);

  return (
    <div className="space-y-4">
      {/* Connection status */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        {connected ? (
          <>
            <Wifi className="w-3 h-3 text-green-400" />
            <span className="text-green-400">Connected to /metrics</span>
          </>
        ) : (
          <>
            <WifiOff className="w-3 h-3 text-red-400" />
            <span className="text-red-400">Disconnected</span>
          </>
        )}
      </div>

      {!snapshot ? (
        <div className="text-sm text-gray-500 py-8 text-center">
          Waiting for metrics data...
        </div>
      ) : (
        <>
          {/* Row 1: FPS + Counters */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <FpsGauge fps={snapshot.fps} />
            <div className="lg:col-span-3">
              <CounterCards counters={snapshot.counters} />
            </div>
          </div>

          {/* Row 2: Pipeline + Controls */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <PipelineTimingChart pipeline={snapshot.pipeline} />
            </div>
            <RenderControls />
          </div>

          {/* Row 3: Zone + Animation Tables */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ZoneInsightsTable zones={snapshot.zones} />
            <AnimationStatsTable animations={snapshot.animations} />
          </div>
        </>
      )}
    </div>
  );
}
