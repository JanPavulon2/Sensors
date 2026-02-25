/**
 * CounterCards — Global frame counter metrics displayed as a card grid.
 */

import { Layers, SkipForward, Timer, Send } from 'lucide-react';
import { Card } from '@/shared/ui/card';
import type { CounterMetrics } from '../types/metrics';

interface CounterCardsProps {
  counters: CounterMetrics;
}

interface StatCardProps {
  icon: React.ElementType;
  label: string;
  value: number;
  color: string;
}

function StatCard({ icon: Icon, label, value, color }: StatCardProps) {
  return (
    <Card className="p-3 bg-gray-900/50 flex flex-col items-center justify-center">
      <Icon className={`w-5 h-5 mb-1 ${color}`} />
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`text-xl font-bold font-mono ${color}`}>
        {value.toLocaleString()}
      </p>
    </Card>
  );
}

export function CounterCards({ counters }: CounterCardsProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
      <StatCard
        icon={Layers}
        label="Rendered"
        value={counters.frames_rendered}
        color="text-green-400"
      />
      <StatCard
        icon={SkipForward}
        label="DMA Skipped"
        value={counters.dma_skipped}
        color="text-yellow-400"
      />
      <StatCard
        icon={Timer}
        label="Expired"
        value={counters.frames_expired}
        color="text-red-400"
      />
      <StatCard
        icon={Send}
        label="Submitted"
        value={counters.frames_submitted}
        color="text-blue-400"
      />
      <Card className="p-3 bg-gray-900/50 flex flex-col items-center justify-center">
        <p className="text-xs text-gray-400">Redundant</p>
        <p className="text-xl font-bold font-mono text-yellow-400">
          {(counters.redundant_ratio * 100).toFixed(1)}%
        </p>
        <div className="bg-gray-700 rounded h-1.5 w-16 mt-1">
          <div
            className="bg-yellow-400 h-1.5 rounded"
            style={{ width: `${Math.min(100, counters.redundant_ratio * 100)}%` }}
          />
        </div>
      </Card>
    </div>
  );
}
