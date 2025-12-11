/**
 * Zones Dashboard Page
 *
 * Full-page view showing all zones as animated thumbnails in a grid.
 * Click any zone to open detailed editor in modal.
 * Features live animation previews, brightness sliders, and full zone control.
 */

import React, { useEffect } from 'react';
import { ZonesDashboard } from '../components/ZonesDashboard/ZonesDashboard';
import { useDesignStore, useZones, useDesignTheme } from '../store/designStore';
import styles from './ZonesDashboardPage.module.css';

/**
 * ZonesDashboardPage Component
 * Main dashboard page for managing all zones
 */
export const ZonesDashboardPage: React.FC = () => {
  const theme = useDesignTheme();
  const zones = useZones();
  const updateZone = useDesignStore((state) => state.updateZone);

  // Initialize with demo zones if empty
  useEffect(() => {
    if (zones.size === 0) {
      // Create sample zones for demo
      const demoZones = [
        {
          id: 'floor',
          displayName: 'Floor Strip',
          pixelCount: 18,
          enabled: true,
          reversed: false,
          order: 0,
          startIndex: 0,
          endIndex: 17,
          gpio: 18,
          color: { mode: 'HUE' as const, hue: 240 },
          brightness: 150,
          mode: 'STATIC' as const,
        },
        {
          id: 'lamp',
          displayName: 'Lamp',
          pixelCount: 19,
          enabled: true,
          reversed: false,
          order: 1,
          startIndex: 18,
          endIndex: 36,
          gpio: 18,
          color: { mode: 'HUE' as const, hue: 120 },
          brightness: 120,
          mode: 'BREATHE' as const,
        },
        {
          id: 'left',
          displayName: 'Left Wall',
          pixelCount: 4,
          enabled: true,
          reversed: false,
          order: 2,
          startIndex: 37,
          endIndex: 40,
          gpio: 18,
          color: { mode: 'PRESET' as const, preset: 'red' },
          brightness: 180,
          mode: 'COLOR_CYCLE' as const,
        },
        {
          id: 'right',
          displayName: 'Right Wall',
          pixelCount: 12,
          enabled: true,
          reversed: false,
          order: 3,
          startIndex: 41,
          endIndex: 52,
          gpio: 18,
          color: { mode: 'HUE' as const, hue: 300 },
          brightness: 140,
          mode: 'SNAKE' as const,
        },
        {
          id: 'ceiling',
          displayName: 'Ceiling',
          pixelCount: 24,
          enabled: true,
          reversed: false,
          order: 4,
          startIndex: 53,
          endIndex: 76,
          gpio: 18,
          color: { mode: 'PRESET' as const, preset: 'cyan' },
          brightness: 100,
          mode: 'COLOR_FADE' as const,
        },
      ];

      demoZones.forEach((zone) => {
        const demoZone = { ...zone } as any;
        useDesignStore.setState((state) => ({
          zones: new Map(state.zones).set(zone.id, demoZone),
        }));
      });
    }
  }, [zones.size]);

  return (
    <div className={`${styles.page} ${theme}-theme`}>
      {/* Import styles */}
      <style>{`
        @import url('../styles/design-tokens.css');
        @import url('../styles/theme-cyber.css');
        @import url('../styles/theme-nature.css');
      `}</style>

      {/* Header */}
      <header className={styles.header}>
        <h1>🎛️ Zones Control Center</h1>
        <p>Click any zone to view and edit its properties</p>
      </header>

      {/* Main Content */}
      <main className={styles.content}>
        <ZonesDashboard zones={zones} onZoneUpdate={updateZone} />
      </main>
    </div>
  );
};

export default ZonesDashboardPage;
