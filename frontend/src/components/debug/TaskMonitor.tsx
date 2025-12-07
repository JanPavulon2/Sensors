/**
 * TaskMonitor Component
 *
 * Main component for real-time task monitoring
 * Displays:
 * - Connection status
 * - Task statistics
 * - Filterable task list
 * - Real-time updates via WebSocket
 */

import { useState, useMemo } from "react";
import { useTaskStore } from "@/stores/taskStore";
import { useTaskWebSocket } from "@/hooks/useTaskWebSocket";
import { TaskCard } from "./TaskCard";
import { TaskStatsDisplay } from "./TaskStats";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Activity,
  RefreshCw,
  Trash2,
  Wifi,
  WifiOff,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

type FilterTab = "all" | "running" | "completed" | "failed" | "cancelled";

export function TaskMonitor() {
  const [filterTab, setFilterTab] = useState<FilterTab>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Get store data
  const tasks = useTaskStore((s) => s.tasks);
  const stats = useTaskStore((s) => s.stats);
  const clearCompleted = useTaskStore((s) => s.clearCompleted);
  const clearFailed = useTaskStore((s) => s.clearFailed);

  // WebSocket hook
  const { isConnected, isConnecting, error, retryCount, sendCommand } =
    useTaskWebSocket({
      enabled: true,
    });

  // Filter and search tasks
  const filteredTasks = useMemo(() => {
    let filtered = Array.from(tasks.values());

    // Filter by tab
    switch (filterTab) {
      case "running":
        filtered = filtered.filter((t) => t.status === "running");
        break;
      case "completed":
        filtered = filtered.filter((t) => t.status === "completed");
        break;
      case "failed":
        filtered = filtered.filter((t) => t.status === "failed");
        break;
      case "cancelled":
        filtered = filtered.filter((t) => t.status === "cancelled");
        break;
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.description.toLowerCase().includes(query) ||
          t.category.toLowerCase().includes(query) ||
          t.id.toString().includes(query)
      );
    }

    // Sort by creation time (newest first)
    filtered.sort((a, b) => b.created_timestamp - a.created_timestamp);

    return filtered;
  }, [tasks, filterTab, searchQuery]);

  const handleRefresh = () => {
    sendCommand({ command: "get_all" });
    sendCommand({ command: "get_stats" });
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card className="p-4 bg-gray-900/50">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-bold">Task Monitor</h2>
          </div>

          {/* Connection Status */}
          <div className="flex items-center gap-3">
            {error && (
              <div className="flex items-center gap-1 text-xs text-red-400">
                <AlertCircle className="w-3 h-3" />
                {retryCount > 0 && <span>Retry {retryCount}...</span>}
              </div>
            )}

            <div className="flex items-center gap-2">
              {isConnected ? (
                <>
                  <Wifi className="w-4 h-4 text-green-400" />
                  <span className="text-xs text-green-400">Connected</span>
                </>
              ) : isConnecting ? (
                <>
                  <WifiOff className="w-4 h-4 text-yellow-400 animate-pulse" />
                  <span className="text-xs text-yellow-400">Connecting...</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-4 h-4 text-red-400" />
                  <span className="text-xs text-red-400">Disconnected</span>
                </>
              )}
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={!isConnected}
              className="h-7"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Stats */}
        <TaskStatsDisplay stats={stats} tasks={tasks} />
      </Card>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-2">
        <Input
          placeholder="Search tasks by description, category, or ID..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1"
        />
        <Button
          variant="outline"
          size="sm"
          onClick={clearCompleted}
          className="whitespace-nowrap"
        >
          <Trash2 className="w-3 h-3 mr-2" />
          Clear Completed
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={clearFailed}
          className="whitespace-nowrap"
        >
          <Trash2 className="w-3 h-3 mr-2" />
          Clear Failed
        </Button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-gray-700">
        {["all", "running", "completed", "failed", "cancelled"].map((tab) => (
          <Button
            key={tab}
            variant="ghost"
            size="sm"
            onClick={() => setFilterTab(tab as FilterTab)}
            className={cn(
              "rounded-none border-b-2 border-transparent capitalize",
              filterTab === tab && "border-b-blue-400 text-blue-400"
            )}
          >
            {tab}
            <span className="ml-2 text-xs text-gray-400">
              ({
                tab === "all"
                  ? tasks.size
                  : tab === "running"
                    ? Array.from(tasks.values()).filter((t) => t.status === "running")
                        .length
                    : tab === "completed"
                      ? Array.from(tasks.values()).filter((t) => t.status === "completed")
                          .length
                      : tab === "failed"
                        ? Array.from(tasks.values()).filter((t) => t.status === "failed")
                            .length
                        : Array.from(tasks.values()).filter((t) => t.status === "cancelled")
                            .length
              })
            </span>
          </Button>
        ))}
      </div>

      {/* Task List */}
      <div className="space-y-2 max-h-[calc(100vh-500px)] overflow-y-auto">
        {filteredTasks.length === 0 ? (
          <Card className="p-8 bg-gray-900/50 text-center">
            <p className="text-gray-400">
              {searchQuery ? "No tasks match your search" : "No tasks yet"}
            </p>
          </Card>
        ) : (
          filteredTasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
            />
          ))
        )}
      </div>

      {/* Footer Info */}
      {filteredTasks.length > 0 && (
        <div className="text-xs text-gray-400 text-center py-2">
          Showing {filteredTasks.length} of {tasks.size} tasks
        </div>
      )}
    </div>
  );
}
