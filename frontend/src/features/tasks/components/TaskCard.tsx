/**
 * TaskCard Component
 *
 * Displays a single task with:
 * - Status indicator (color-coded circle)
 * - Task metadata (ID, category, description, timestamps)
 * - Duration and error information
 * - Expandable details modal
 */

import { useState } from "react";
import type { Task, TaskStatus } from "@/shared/types/domain/task";
import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  ChevronDown,
  Copy,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface TaskCardProps {
  task: Task;
}

const getStatusColor = (status: TaskStatus): string => {
  switch (status) {
    case "running":
      return "text-blue-400";
    case "completed":
      return "text-green-400";
    case "failed":
      return "text-red-400";
    case "cancelled":
      return "text-gray-400";
    default:
      return "text-gray-400";
  }
};

const getStatusBgColor = (status: TaskStatus): string => {
  switch (status) {
    case "running":
      return "bg-blue-900/20";
    case "completed":
      return "bg-green-900/20";
    case "failed":
      return "bg-red-900/20";
    case "cancelled":
      return "bg-gray-900/20";
    default:
      return "bg-gray-900/20";
  }
};

const getStatusIcon = (status: TaskStatus) => {
  switch (status) {
    case "running":
      return <Clock className={cn("w-4 h-4", getStatusColor(status), "animate-spin")} />;
    case "completed":
      return <CheckCircle className={cn("w-4 h-4", getStatusColor(status))} />;
    case "failed":
      return <XCircle className={cn("w-4 h-4", getStatusColor(status))} />;
    case "cancelled":
      return <AlertCircle className={cn("w-4 h-4", getStatusColor(status))} />;
    default:
      return <Clock className={cn("w-4 h-4", getStatusColor(status))} />;
  }
};

const formatDuration = (seconds: number | undefined): string => {
  if (!seconds) return "N/A";
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}m ${secs.toFixed(0)}s`;
};

const formatTimestamp = (isoString: string | undefined): string => {
  if (!isoString) return "N/A";
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString();
  } catch {
    return isoString;
  }
};

export function TaskCard({ task }: TaskCardProps) {
  const [showModal, setShowModal] = useState(false);

  const handleCopyId = () => {
    navigator.clipboard.writeText(`Task ${task.id}`);
  };

  return (
    <>
      <Card
        className={cn(
          "p-3 transition-all duration-200",
          getStatusBgColor(task.status),
          "border-l-4",
          task.status === "running"
            ? "border-l-blue-400"
            : task.status === "completed"
              ? "border-l-green-400"
              : task.status === "failed"
                ? "border-l-red-400"
                : "border-l-gray-400"
        )}
      >
        {/* Task Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-start gap-3 flex-1">
            {/* Status Icon */}
            <div className="mt-1">{getStatusIcon(task.status)}</div>

            {/* Task Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono bg-gray-800 px-2 py-1 rounded">
                  #{task.id}
                </span>
                <span className="text-xs bg-gray-700 px-2 py-1 rounded font-semibold">
                  {task.category}
                </span>
                <span
                  className={cn(
                    "text-xs font-semibold capitalize",
                    getStatusColor(task.status)
                  )}
                >
                  {task.status}
                </span>
              </div>

              <p className="text-sm text-gray-200 truncate">{task.description}</p>

              {/* Quick Info */}
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                <span>Started: {formatTimestamp(task.created_at)}</span>
                {task.duration !== undefined && (
                  <span>Duration: {formatDuration(task.duration)}</span>
                )}
              </div>

              {/* Error Message (if failed) */}
              {task.error && (
                <div className="mt-2 p-2 bg-red-900/30 border border-red-700/50 rounded text-xs text-red-300 font-mono truncate">
                  {task.error}
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-1 flex-shrink-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopyId}
              className="h-7 w-7 p-0"
              title="Copy task ID"
            >
              <Copy className="w-3 h-3" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowModal(true)}
              className="h-7 w-7 p-0"
              title="View details"
            >
              <ChevronDown className="w-3 h-3" />
            </Button>
          </div>
        </div>
      </Card>

      {/* Details Modal */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="w-full max-w-2xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {getStatusIcon(task.status)}
              Task #{task.id}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-400">Description:</span>
                <p className="font-mono text-gray-200">{task.description}</p>
              </div>
              <div>
                <span className="text-gray-400">Category:</span>
                <p className="font-mono text-gray-200">{task.category}</p>
              </div>
              <div>
                <span className="text-gray-400">Status:</span>
                <p className={cn("font-mono capitalize", getStatusColor(task.status))}>
                  {task.status}
                </p>
              </div>
              <div>
                <span className="text-gray-400">Duration:</span>
                <p className="font-mono text-gray-200">
                  {formatDuration(task.duration)}
                </p>
              </div>
              <div>
                <span className="text-gray-400">Created:</span>
                <p className="font-mono text-gray-200">
                  {formatTimestamp(task.created_at)}
                </p>
              </div>
              {task.finished_at && (
                <div>
                  <span className="text-gray-400">Finished:</span>
                  <p className="font-mono text-gray-200">
                    {formatTimestamp(task.finished_at)}
                  </p>
                </div>
              )}
            </div>

            {task.error && (
              <div className="p-3 bg-red-900/20 border border-red-700/50 rounded">
                <span className="text-gray-400 block mb-1">Error:</span>
                <p className="font-mono text-red-300">{task.error}</p>
              </div>
            )}

            {task.origin_stack && (
              <div className="p-3 bg-gray-900/50 border border-gray-700/30 rounded">
                <span className="text-gray-400 block mb-2">Stack Trace:</span>
                <pre className="text-xs text-gray-400 overflow-auto max-h-48">
                  {task.origin_stack}
                </pre>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
