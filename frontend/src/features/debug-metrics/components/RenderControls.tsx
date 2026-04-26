/**
 * RenderControls — FPS setting, counter reset, and metrics interval controls.
 * Mutations go through REST API (not Socket.IO).
 */

import { useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Slider } from '@/shared/ui/slider';
import api from '@/shared/api/client';

const INTERVAL_OPTIONS = [0.25, 0.5, 1, 2] as const;

export function RenderControls() {
  const [renderFps, setRenderFps] = useState(60);
  const [metricsInterval, setMetricsInterval] = useState(1);

  async function handleResetCounters() {
    try {
      await api.post('/v1/metrics/reset');
    } catch (error) {
      console.error('Failed to reset metrics:', error);
    }
  }

  async function handleFpsChange(values: number[]) {
    const fps = values[0];
    setRenderFps(fps);
    try {
      await api.put('/v1/metrics/render-fps', { fps });
    } catch (error) {
      console.error('Failed to set render FPS:', error);
    }
  }

  async function handleIntervalChange(interval: number) {
    setMetricsInterval(interval);
    try {
      await api.put('/v1/metrics/interval', { interval });
    } catch (error) {
      console.error('Failed to set metrics interval:', error);
    }
  }

  return (
    <Card className="bg-gray-900/50">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-300">Controls</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Render FPS */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400">Render FPS</span>
            <span className="text-xs font-mono text-gray-300">{renderFps}</span>
          </div>
          <Slider
            defaultValue={[60]}
            min={1}
            max={120}
            step={1}
            onValueCommit={handleFpsChange}
          />
        </div>

        {/* Metrics Interval */}
        <div>
          <span className="text-xs text-gray-400 block mb-2">Stream Interval</span>
          <div className="flex gap-2">
            {INTERVAL_OPTIONS.map((interval) => (
              <Button
                key={interval}
                variant={metricsInterval === interval ? 'default' : 'outline'}
                size="sm"
                className="text-xs"
                onClick={() => handleIntervalChange(interval)}
              >
                {interval}s
              </Button>
            ))}
          </div>
        </div>

        {/* Reset */}
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={handleResetCounters}
        >
          <RotateCcw className="w-3 h-3 mr-2" />
          Reset Counters
        </Button>
      </CardContent>
    </Card>
  );
}
