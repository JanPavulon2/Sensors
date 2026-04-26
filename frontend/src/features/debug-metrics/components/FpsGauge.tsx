/**
 * FpsGauge — Real-time FPS display with color-coded status.
 */

import { Activity } from 'lucide-react';
import { Card } from '@/shared/ui/card';
import type { FpsMetrics } from '../types/metrics';

interface FpsGaugeProps {
  fps: FpsMetrics;
  targetFps?: number;
}

function getFpsColor(actual: number, target: number): string {
  const ratio = actual / target;
  if (ratio >= 0.95) return 'text-green-400';
  if (ratio >= 0.8) return 'text-yellow-400';
  return 'text-red-400';
}

export function FpsGauge({ fps, targetFps = 60 }: FpsGaugeProps) {
  const color = getFpsColor(fps.actual, targetFps);

  return (
    <Card className="p-4 bg-gray-900/50 flex items-center gap-4">
      <Activity className={`w-8 h-8 ${color}`} />
      <div>
        <p className="text-xs text-gray-400">Actual FPS</p>
        <p className={`text-3xl font-bold font-mono ${color}`}>
          {fps.actual.toFixed(1)}
        </p>
      </div>
      <div className="ml-auto text-right">
        <p className="text-xs text-gray-400">Target</p>
        <p className="text-lg font-mono text-gray-500">{targetFps}</p>
      </div>
    </Card>
  );
}
