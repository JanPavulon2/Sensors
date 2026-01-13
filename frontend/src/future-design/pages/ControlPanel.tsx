/**
 * Control Panel - Live LED Control Interface
 *
 * Demonstrates the complete Phase 1 system with:
 * - Real-time LED canvas visualization
 * - Zone management
 * - Color controls
 * - Animation controls
 *
 * This is a working demo that can be extended to use actual backend data
 */

import React, { useEffect, useMemo } from 'react';
import { LEDCanvasRenderer } from '../components/LEDVisualization/LEDCanvasRenderer';
import { ColorControlPanel } from '../components/ColorControl/ColorControlPanel';
import { AnimationControlPanel } from '../components/AnimationControl/AnimationControlPanel';
import { useDesignStore, useZones, useSelectedZone, useDesignTheme } from '../store/designStore';
import type { Color, AnimationID, AnimationParameters } from '../types/index';
import styles from './ControlPanel.module.css';

/**
 * ControlPanel Component
 * Live control interface for LED management
 */
export const ControlPanel: React.FC = () => {
  const theme = useDesignTheme();
  const zones = useZones();
  const selectedZoneId = useSelectedZone();
  const selectZone = useDesignStore((state) => state.selectZone);
  // updateParameter is currently not implemented
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
          mode: 'STATIC' as const,
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
          mode: 'STATIC' as const,
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

  const selectedZone = useMemo(() => {
    return zones.get(selectedZoneId || '') || Array.from(zones.values())[0];
  }, [zones, selectedZoneId]);

  // Unified color change handler
  const handleColorChange = (color: Color) => {
    if (!selectedZone) return;
    const updatedZone = {
      ...selectedZone,
      color,
    };
    updateZone(updatedZone);
  };

  // Brightness change handler
  const handleBrightnessChange = (brightness: number) => {
    if (!selectedZone) return;
    const updatedZone = {
      ...selectedZone,
      brightness,
    };
    updateZone(updatedZone);
  };

  // Animation mode change handler
  const handleAnimationChange = (mode: AnimationID) => {
    if (!selectedZone) return;
    const updatedZone = {
      ...selectedZone,
      mode,
    };
    updateZone(updatedZone);
  };

  // Animation parameter change handler
  const handleParameterChange = (_key: keyof AnimationParameters, _value: number | string) => {
    if (!selectedZone) return;
    // TODO: Implement parameter persistence
    // updateParameter(_key as ParamID, _value);
  };

  return (
    <div className={`${styles.container} ${theme}-theme`}>
      {/* Import styles */}
      <style>{`
        @import url('../styles/design-tokens.css');
        @import url('../styles/theme-cyber.css');
        @import url('../styles/theme-nature.css');
      `}</style>

      <header className={styles.header}>
        <h1>🎮 LED Control Panel</h1>
        <p>Live visualization and control interface</p>
      </header>

      <div className={styles.layout}>
        {/* Main Canvas */}
        <section className={styles.canvasSection}>
          <h2>LED Visualization</h2>
          <LEDCanvasRenderer
            zones={zones}
            selectedZoneId={selectedZoneId || ''}
            orientation="horizontal"
            pixelSize={24}
            gapBetweenZones={12}
            onZoneSelect={(zoneId) => selectZone(zoneId)}
          />
        </section>

        {/* Control Panel */}
        <section className={styles.controlSection}>
          {/* Zone Selector */}
          <div className={styles.panel}>
            <h3>Zones</h3>
            <div className={styles.zoneList}>
              {Array.from(zones.values())
                .sort((a, b) => a.order - b.order)
                .map((zone) => (
                  <button
                    key={zone.id}
                    className={`${styles.zoneButton} ${selectedZone?.id === zone.id ? styles.active : ''}`}
                    onClick={() => selectZone(zone.id)}
                  >
                    <span className={styles.zoneName}>{zone.displayName}</span>
                    <span className={styles.zonePixels}>{zone.pixelCount}px</span>
                  </button>
                ))}
            </div>
          </div>

          {/* Color Control Panel */}
          {selectedZone && (
            <ColorControlPanel
              color={selectedZone.color}
              brightness={selectedZone.brightness || 100}
              onColorChange={handleColorChange}
              onBrightnessChange={handleBrightnessChange}
              compact
            />
          )}

          {/* Animation Control Panel */}
          {selectedZone && (
            <AnimationControlPanel
              animationMode={selectedZone.mode}
              parameters={{
                speed: 50,
                intensity: 50,
                length: 10,
                hue_offset: 0,
              }}
              enabled={selectedZone.enabled !== false}
              onAnimationChange={handleAnimationChange}
              onParameterChange={handleParameterChange}
            />
          )}

          {/* Info Panel */}
          <div className={styles.panel}>
            <h3>System Info</h3>
            <div className={styles.info}>
              <p>
                <strong>Zones:</strong> {zones.size}
              </p>
              <p>
                <strong>Total Pixels:</strong> {Array.from(zones.values()).reduce((sum, z) => sum + z.pixelCount, 0)}
              </p>
              <p>
                <strong>Selected:</strong> {selectedZone?.displayName || 'None'}
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default ControlPanel;
