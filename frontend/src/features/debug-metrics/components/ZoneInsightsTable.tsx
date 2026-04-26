/**
 * ZoneInsightsTable — Per-zone frame production, change ratio, and source display.
 */

import { Card, CardHeader, CardTitle, CardContent } from '@/shared/ui/card';
import type { ZoneMetricsData } from '../types/metrics';

interface ZoneInsightsTableProps {
  zones: Record<string, ZoneMetricsData>;
}

function changeRatioColor(ratio: number): string {
  if (ratio >= 0.8) return 'text-green-400';
  if (ratio >= 0.4) return 'text-yellow-400';
  return 'text-gray-500';
}

export function ZoneInsightsTable({ zones }: ZoneInsightsTableProps) {
  const entries = Object.entries(zones);

  if (entries.length === 0) {
    return (
      <Card className="bg-gray-900/50 p-4">
        <p className="text-sm text-gray-500">No zone metrics available</p>
      </Card>
    );
  }

  return (
    <Card className="bg-gray-900/50">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-300">
          Zone Insights
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-700">
                <th className="text-left py-2 pr-3">Zone</th>
                <th className="text-right py-2 px-2">Produced</th>
                <th className="text-right py-2 px-2">Rendered</th>
                <th className="text-right py-2 px-2">Expired</th>
                <th className="text-right py-2 px-2">Change%</th>
                <th className="text-right py-2 px-2">Source</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([zoneName, zm]) => (
                <tr key={zoneName} className="border-b border-gray-800">
                  <td className="py-1.5 pr-3 font-mono text-gray-300">{zoneName}</td>
                  <td className="py-1.5 px-2 text-right font-mono text-blue-400">
                    {zm.produced.toLocaleString()}
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono text-green-400">
                    {zm.rendered.toLocaleString()}
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono text-red-400">
                    {zm.expired.toLocaleString()}
                  </td>
                  <td className={`py-1.5 px-2 text-right font-mono ${changeRatioColor(zm.change_ratio)}`}>
                    {(zm.change_ratio * 100).toFixed(1)}%
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono text-gray-500">
                    {zm.last_source ?? '—'}
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
