/**
 * Debug Page
 *
 * Centralized debugging and monitoring dashboard with tabs for:
 * - Task Monitor (real-time async task tracking)
 * - Logger (application logs)
 * - State Viewer (Zustand store inspection)
 */

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { TaskMonitor } from "@/features/tasks/components";
import { Logger } from "@/features/logger/components";
import { Activity, FileText, Database } from "lucide-react";

type DebugTab = "tasks" | "logs" | "state";

export function DebugPage(): JSX.Element {
  const [activeTab, setActiveTab] = useState<DebugTab>("tasks");

  return (
    <div className="space-y-4">
      {/* Page Header */}
      <div>
        <h1 className="text-4xl font-bold mb-2">Debug Dashboard</h1>
        <p className="text-gray-400">
          Real-time monitoring of tasks, logs, and application state
        </p>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as DebugTab)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="tasks" className="flex items-center gap-2">
            <Activity className="w-4 h-4" />
            Tasks
          </TabsTrigger>
          <TabsTrigger value="logs" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Logs
          </TabsTrigger>
          <TabsTrigger value="state" className="flex items-center gap-2">
            <Database className="w-4 h-4" />
            State
          </TabsTrigger>
        </TabsList>

        {/* Task Monitor Tab */}
        <TabsContent value="tasks" className="space-y-4">
          <TaskMonitor />
        </TabsContent>

        {/* Logger Tab */}
        <TabsContent value="logs" className="space-y-4">
          <Logger />
        </TabsContent>
      </Tabs>
    </div>
  );
}
