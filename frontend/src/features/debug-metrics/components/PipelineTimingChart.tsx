/**
 * PipelineTimingChart — Stacked horizontal bar showing build/merge/hw/emit ms
 * with avg and max values.
 */

import { Card, CardHeader, CardTitle, CardContent } from '@/shared/ui/card';
import type { PipelineMetrics } from '../types/metrics';

interface PipelineTimingChartProps {
  pipeline: PipelineMetrics;
}

interface StageRowProps {
  label: string;
  avgMs: number;
  maxMs: number;
  color: string;
  maxScale: number;
}

function StageRow({ label, avgMs, maxMs, color, maxScale }: StageRowProps) {
  const avgWidth = maxScale > 0 ? (avgMs / maxScale) * 100 : 0;
  const maxWidth = maxScale > 0 ? (maxMs / maxScale) * 100 : 0;

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-400 w-32 shrink-0 text-right">{label}</span>
      <div className="flex-1 relative h-5">
        {/* Max bar (dimmed) */}
        <div
          className={`absolute inset-y-0 left-0 rounded opacity-20 ${color}`}
          style={{ width: `${Math.min(100, maxWidth)}%` }}
        />
        {/* Avg bar (solid) */}
        <div
          className={`absolute inset-y-0 left-0 rounded ${color}`}
          style={{ width: `${Math.min(100, avgWidth)}%` }}
        />
      </div>
      <span className="text-xs font-mono text-gray-300 w-20 text-right">
        {avgMs.toFixed(2)} ms
      </span>
      <span className="text-xs font-mono text-gray-500 w-20 text-right">
        max {maxMs.toFixed(2)}
      </span>
    </div>
  );
}

export function PipelineTimingChart({ pipeline }: PipelineTimingChartProps) {
  // Use render_cycle_max as the scale reference
  const maxScale = Math.max(
    pipeline.render_cycle_max_ms,
    pipeline.build_max_ms + pipeline.merge_max_ms +
    pipeline.write_to_hardware_max_ms + pipeline.emit_max_ms,
    1,
  );

  return (
    <Card className="bg-gray-900/50">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-300">
          Pipeline Timing
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <StageRow
          label="Build"
          avgMs={pipeline.build_avg_ms}
          maxMs={pipeline.build_max_ms}
          color="bg-blue-500"
          maxScale={maxScale}
        />
        <StageRow
          label="Merge"
          avgMs={pipeline.merge_avg_ms}
          maxMs={pipeline.merge_max_ms}
          color="bg-cyan-500"
          maxScale={maxScale}
        />
        <StageRow
          label="Write to HW"
          avgMs={pipeline.write_to_hardware_avg_ms}
          maxMs={pipeline.write_to_hardware_max_ms}
          color="bg-purple-500"
          maxScale={maxScale}
        />
        <StageRow
          label="Emit"
          avgMs={pipeline.emit_avg_ms}
          maxMs={pipeline.emit_max_ms}
          color="bg-amber-500"
          maxScale={maxScale}
        />
        <div className="border-t border-gray-700 pt-2">
          <StageRow
            label="Render Cycle"
            avgMs={pipeline.render_cycle_avg_ms}
            maxMs={pipeline.render_cycle_max_ms}
            color="bg-green-500"
            maxScale={maxScale}
          />
        </div>

        {/* Sparkline for render cycle history */}
        {pipeline.render_cycle_history.length > 1 && (
          <div className="pt-2">
            <p className="text-xs text-gray-500 mb-1">Render cycle history</p>
            <Sparkline data={pipeline.render_cycle_history} color="rgb(34, 197, 94)" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** Simple SVG sparkline */
function Sparkline({ data, color, height = 32 }: { data: number[]; color: string; height?: number }) {
  if (data.length < 2) return null;

  const max = Math.max(...data, 0.001);
  const width = 300;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - (v / max) * (height - 2);
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height }}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}
