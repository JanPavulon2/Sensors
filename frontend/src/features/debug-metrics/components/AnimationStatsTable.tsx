/**
 * AnimationStatsTable — Per-animation step timing and frame counts.
 * Sorted by max step time to surface bottlenecks.
 */

import { Card, CardHeader, CardTitle, CardContent } from '@/shared/ui/card';
import type { AnimationMetricsData } from '../types/metrics';

interface AnimationStatsTableProps {
  animations: Record<string, AnimationMetricsData>;
}

function stepTimeColor(maxMs: number): string {
  if (maxMs >= 5) return 'text-red-400';
  if (maxMs >= 2) return 'text-yellow-400';
  return 'text-green-400';
}

export function AnimationStatsTable({ animations }: AnimationStatsTableProps) {
  const entries = Object.entries(animations).sort(
    ([, a], [, b]) => b.max_step_ms - a.max_step_ms,
  );

  if (entries.length === 0) {
    return (
      <Card className="bg-gray-900/50 p-4">
        <p className="text-sm text-gray-500">No animation metrics available</p>
      </Card>
    );
  }

  return (
    <Card className="bg-gray-900/50">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-300">
          Animation Stats
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-700">
                <th className="text-left py-2 pr-3">Zone : Animation</th>
                <th className="text-right py-2 px-2">Frames</th>
                <th className="text-right py-2 px-2">Avg Step</th>
                <th className="text-right py-2 px-2">Max Step</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([key, data]) => (
                <tr key={key} className="border-b border-gray-800">
                  <td className="py-1.5 pr-3 font-mono text-gray-300">{key}</td>
                  <td className="py-1.5 px-2 text-right font-mono text-blue-400">
                    {data.frames_produced.toLocaleString()}
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono text-gray-300">
                    {data.avg_step_ms.toFixed(3)} ms
                  </td>
                  <td className={`py-1.5 px-2 text-right font-mono ${stepTimeColor(data.max_step_ms)}`}>
                    {data.max_step_ms.toFixed(3)} ms
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
