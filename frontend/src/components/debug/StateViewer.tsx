/**
 * State Viewer Component
 * Displays application state in real-time as a collapsible tree
 */

import { useZoneStore } from '@/stores/zoneStore';
import { useSystemStore } from '@/stores/systemStore';
import { TreeNode } from './TreeNode';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface StateViewerProps {
  compact?: boolean;
}

export function StateViewer({ compact = false }: StateViewerProps): JSX.Element {
  // Get all state from stores
  const zoneState = useZoneStore();
  const systemState = useSystemStore();

  // Build state tree
  const appState = {
    zones: {
      zones: zoneState.zones.length,
      selectedZoneId: zoneState.selectedZoneId,
      loading: zoneState.loading,
      error: zoneState.error,
      details: zoneState.zones.map((zone) => ({
        id: zone.id,
        name: zone.name,
        enabled: zone.state.is_on,
        brightness: zone.state.brightness,
        color: zone.state.color.mode,
      })),
    },
    system: {
      connectionStatus: systemState.connectionStatus,
      fps: systemState.fps,
      powerDraw: systemState.powerDraw,
      uptime: systemState.uptime,
      theme: systemState.theme,
    },
  };

  return (
    <div className={`bg-bg-elevated rounded border border-accent-primary/20 ${!compact ? '' : 'h-full'}`}>
      {!compact && (
        <Card className="bg-bg-elevated">
          <CardHeader>
            <CardTitle className="text-sm">State Tree</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="bg-bg-app rounded p-3 font-mono text-xs max-h-96 overflow-auto">
              <TreeNode label="app" children={appState} />
            </div>
            <p className="text-xs text-text-tertiary mt-3">
              Real-time view of Zustand stores. Click to expand/collapse.
            </p>
          </CardContent>
        </Card>
      )}
      {compact && (
        <div className="flex flex-col h-full">
          <div className="px-3 py-2 border-b border-accent-primary/20">
            <p className="text-xs font-medium text-text-primary">State</p>
          </div>
          <div className="flex-1 overflow-auto bg-bg-app font-mono text-xs p-2">
            <TreeNode label="app" children={appState} />
          </div>
        </div>
      )}
    </div>
  );
}

export default StateViewer;
