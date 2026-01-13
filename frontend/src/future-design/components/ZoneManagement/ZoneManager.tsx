/**
 * Zone Manager - Multi-zone management interface
 *
 * Displays:
 * - Grid of zone cards
 * - Zone summary statistics
 * - Total pixels and zones count
 *
 * Features:
 * - Quick zone selection
 * - Bulk enable/disable
 * - Zone reordering (future)
 */

import React, { useState } from 'react';
import type { ZoneCombined } from '../../types/index';
import { ZoneCard } from './ZoneCard';
import styles from './ZoneManagement.module.css';

interface ZoneManagerProps {
  zones: Map<string, ZoneCombined>;
  selectedZoneId?: string;
  onZoneSelect: (zoneId: string) => void;
  onZoneToggle?: (zoneId: string, enabled: boolean) => void;
}

/**
 * ZoneManager Component
 * Grid-based zone management interface
 */
export const ZoneManager: React.FC<ZoneManagerProps> = ({
  zones,
  selectedZoneId,
  onZoneSelect,
  onZoneToggle,
}) => {
  const [showStats, setShowStats] = useState(true);

  const sortedZones = Array.from(zones.values()).sort((a, b) => a.order - b.order);
  const totalPixels = sortedZones.reduce((sum, zone) => sum + zone.pixelCount, 0);
  const enabledZones = sortedZones.filter((z) => z.enabled !== false).length;
  const disabledZones = sortedZones.length - enabledZones;

  return (
    <div className={styles.zoneManager}>
      {/* Header */}
      <div className={styles.managerHeader}>
        <h3>Zones ({zones.size})</h3>
        <button
          className={styles.statsToggle}
          onClick={() => setShowStats(!showStats)}
          title={showStats ? 'Hide stats' : 'Show stats'}
        >
          {showStats ? '▼' : '▶'} Stats
        </button>
      </div>

      {/* Statistics Bar */}
      {showStats && (
        <div className={styles.statsBar}>
          <div className={styles.stat}>
            <span className={styles.statLabel}>Total Zones</span>
            <span className={styles.statValue}>{zones.size}</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statLabel}>Total Pixels</span>
            <span className={styles.statValue}>{totalPixels}</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statLabel}>Enabled</span>
            <span className={styles.statValue}>{enabledZones}</span>
          </div>
          {disabledZones > 0 && (
            <div className={styles.stat}>
              <span className={styles.statLabel}>Disabled</span>
              <span className={`${styles.statValue} ${styles.warning}`}>{disabledZones}</span>
            </div>
          )}
          <div className={styles.stat}>
            <span className={styles.statLabel}>Avg Pixels</span>
            <span className={styles.statValue}>{Math.round(totalPixels / Math.max(1, zones.size))}</span>
          </div>
        </div>
      )}

      {/* Zone Cards Grid */}
      {zones.size === 0 ? (
        <div className={styles.emptyState}>
          <p>No zones configured</p>
          <p className={styles.emptyHint}>Create zones to get started</p>
        </div>
      ) : (
        <div className={styles.cardsGrid}>
          {sortedZones.map((zone) => (
            <ZoneCard
              key={zone.id}
              zone={zone}
              isSelected={selectedZoneId === zone.id}
              onSelect={onZoneSelect}
              onToggleEnabled={onZoneToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default ZoneManager;
