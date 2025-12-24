/**
 * TaskStats Component
 *
 * Displays real-time task statistics:
 * - Total, running, completed, failed, cancelled counts
 * - Average durations
 * - Category breakdown
 */

import type { Task, TaskStats } from "@/shared/types/domain/task";
import { Card } from "@/shared/ui/card";
import { Activity, AlertCircle, CheckCircle, Clock, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface TaskStatsDisplayProps {
  stats: TaskStats | null;
  tasks: Map<number, Task>;
}

export function TaskStatsDisplay({ stats }: TaskStatsDisplayProps) {
  if (!stats) {
    return (
      <Card className="p-4 bg-gray-900/50">
        <p className="text-sm text-gray-400">Loading statistics...</p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {/* Main Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <StatCard
          icon={Activity}
          label="Total"
          value={stats.total}
          color="text-blue-400"
        />
        <StatCard
          icon={Clock}
          label="Running"
          value={stats.running}
          color="text-yellow-400"
        />
        <StatCard
          icon={CheckCircle}
          label="Completed"
          value={stats.completed}
          color="text-green-400"
        />
        <StatCard
          icon={AlertCircle}
          label="Failed"
          value={stats.failed}
          color="text-red-400"
        />
        <StatCard
          icon={Zap}
          label="Cancelled"
          value={stats.cancelled}
          color="text-gray-400"
        />
      </div>

      {/* Durations */}
      <div className="grid grid-cols-2 gap-3">
        <Card className="p-3 bg-gray-900/50">
          <p className="text-xs text-gray-400 mb-1">Avg Running Duration</p>
          <p className="text-lg font-mono font-bold text-yellow-400">
            {formatDuration(stats.avg_running_duration)}
          </p>
        </Card>
        <Card className="p-3 bg-gray-900/50">
          <p className="text-xs text-gray-400 mb-1">Avg Completed Duration</p>
          <p className="text-lg font-mono font-bold text-green-400">
            {formatDuration(stats.avg_completed_duration)}
          </p>
        </Card>
      </div>

      {/* Category Breakdown */}
      {Object.keys(stats.categories).length > 0 && (
        <Card className="p-3 bg-gray-900/50">
          <p className="text-xs text-gray-400 mb-2 font-semibold">Tasks by Category</p>
          <div className="space-y-2">
            {Object.entries(stats.categories)
              .sort(([, a], [, b]) => b - a)
              .map(([category, count]) => (
                <div key={category} className="flex items-center justify-between text-xs">
                  <span className="text-gray-300 font-semibold">{category}</span>
                  <div className="flex items-center gap-2">
                    <div className="bg-gray-700 rounded h-1.5 w-16">
                      <div
                        className="bg-blue-400 h-1.5 rounded"
                        style={{
                          width: `${Math.min((count / stats.total) * 100, 100)}%`,
                        }}
                      />
                    </div>
                    <span className="text-gray-400 font-mono w-8 text-right">
                      {count}
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </Card>
      )}
    </div>
  );
}

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  color: string;
}

function StatCard({ icon: Icon, label, value, color }: StatCardProps) {
  return (
    <Card className="p-3 bg-gray-900/50 flex flex-col items-center justify-center">
      <Icon className={cn("w-5 h-5 mb-1", color)} />
      <p className="text-xs text-gray-400 text-center">{label}</p>
      <p className={cn("text-xl font-bold font-mono", color)}>{value}</p>
    </Card>
  );
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds === 0) return "0s";
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}m ${secs.toFixed(0)}s`;
}
