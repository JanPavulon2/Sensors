/**
 * Dashboard Page
 * Main dashboard with system metrics, zone overview, and controls
 */

import { useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { useCheckBackendConnection } from '@/shared/hooks';
import { useZones } from '@/features/zones/hooks';
import { ZonesGrid, ZoneEditPanel } from '@/features/zones/components';

export function Dashboard(): JSX.Element {
  // Real-time zone updates via Socket.IO
  const zones = useZones();
  const { isConnected, isLoading: connectionLoading } = useCheckBackendConnection();

  // Note: Real-time zone updates via Socket.IO are automatically initialized
  // when the zones module is imported (see features/zones/index.ts)

  // Zone detail panel state
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);

  const zoneCount = zones.length;
  const totalPixels = zones.reduce((sum: number, zone) => sum + zone.pixel_count, 0);
  const zonesLoading = zoneCount === 0 && !isConnected;

  // Find selected zone and its index
  const selectedZone = zones.find(z => z.id === selectedZoneId);
  const selectedZoneIndex = selectedZone ? zones.indexOf(selectedZone) : 0;

  // Navigation handlers for detail panel
  const handlePrevZone = () => {
    if (selectedZoneIndex > 0) {
      setSelectedZoneId(zones[selectedZoneIndex - 1].id);
    }
  };

  const handleNextZone = () => {
    if (selectedZoneIndex < zones.length - 1) {
      setSelectedZoneId(zones[selectedZoneIndex + 1].id);
    }
  };

  const handleClosePanel = () => {
    setSelectedZoneId(null);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-text-secondary mt-2">
            {isConnected ? 'System connected and running' : 'Connecting to system...'}
          </p>
        </div>
        <Button>New Animation</Button>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid gap-4 md:grid-cols-4">
        {/* Connection Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            <div
              className={`h-3 w-3 rounded-sm ${
                isConnected ? 'bg-accent-primary' : 'bg-warning'
              }`}
            />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {connectionLoading ? 'Checking...' : isConnected ? 'Online' : 'Offline'}
            </div>
            <p className="text-xs text-text-tertiary mt-1">
              {isConnected ? 'API connected' : 'Reconnecting...'}
            </p>
          </CardContent>
        </Card>

        {/* Total Zones */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Zones</CardTitle>
            <svg
              className="h-4 w-4 text-accent-primary"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M12 2v20M2 12h20" />
            </svg>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{zonesLoading ? '--' : zoneCount}</div>
            <p className="text-xs text-text-tertiary mt-1">
              {zoneCount > 0 ? `${zoneCount} zone${zoneCount !== 1 ? 's' : ''} active` : 'No zones'}
            </p>
          </CardContent>
        </Card>

        {/* Total Pixels */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Pixels</CardTitle>
            <svg
              className="h-4 w-4 text-accent-primary"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="1" />
              <circle cx="19" cy="5" r="1" />
              <circle cx="5" cy="19" r="1" />
            </svg>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{zonesLoading ? '--' : totalPixels}</div>
            <p className="text-xs text-text-tertiary mt-1">
              Total LED count
            </p>
          </CardContent>
        </Card>

        {/* Performance */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">FPS</CardTitle>
            <svg
              className="h-4 w-4 text-accent-primary"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isConnected ? '60' : '--'}</div>
            <p className="text-xs text-text-tertiary mt-1">
              {isConnected ? 'Rendering' : 'Not available'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Zones Section */}
      {isConnected && zoneCount > 0 && (
        <div className="space-y-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">LED Zones</h2>
            <p className="text-text-secondary text-sm mt-1">
              {zoneCount} zone{zoneCount !== 1 ? 's' : ''} configured
            </p>
          </div>
          <ZonesGrid onSelectZone={setSelectedZoneId} />
        </div>
      )}

      {/* Zone Edit Panel */}
      {selectedZone && (
        <ZoneEditPanel
          zone={selectedZone}
          currentIndex={selectedZoneIndex}
          totalZones={zoneCount}
          onClose={handleClosePanel}
          onPrevZone={handlePrevZone}
          onNextZone={handleNextZone}
        />
      )}

      {/* Empty State */}
      {isConnected && zoneCount === 0 && !zonesLoading && (
        <Card className="bg-bg-elevated">
          <CardContent className="pt-6 text-center">
            <p className="text-text-secondary mb-4">No zones configured</p>
            <Button variant="outline">Check Settings</Button>
          </CardContent>
        </Card>
      )}

      {/* Documentation Card */}
      {/* <Card className="bg-bg-elevated border border-accent-primary/20">
        <CardHeader>
          <CardTitle className="text-sm">Quick Start</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-text-secondary space-y-2">
          <p>1. Configure your backend API URL in Settings</p>
          <p>2. Zones will load automatically from the backend</p>
          <p>3. Use zone controls to set colors and brightness</p>
          <p>4. Create animations and preview in real-time</p>
        </CardContent>
      </Card> */}
    </div>
  );
}

export default Dashboard;
