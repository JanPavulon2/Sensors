/**
 * Zones Dashboard - Thumbnail grid with detail card modal
 *
 * Features:
 * - Grid of zone thumbnails with live animation preview
 * - Click thumbnail to open detail card
 * - Full zone editing in modal
 * - Navigation arrows to prev/next zone
 * - On/off toggles
 * - Brightness control with slider
 */

import React, { useState, useMemo } from 'react';
import type { ZoneCombined } from '../../types/index';
import { ZoneThumbnail } from './ZoneThumbnail';
import { ZoneDetailCard } from './ZoneDetailCard';
import styles from './ZonesDashboard.module.css';

interface ZonesDashboardProps {
  zones: Map<string, ZoneCombined>;
  selectedZoneId?: string;
  onZoneUpdate: (zone: ZoneCombined) => void;
}

/**
 * ZonesDashboard Component
 * Grid-based zone thumbnail view with modal detail editor
 */
export const ZonesDashboard: React.FC<ZonesDashboardProps> = ({
  zones,
  selectedZoneId,
  onZoneUpdate,
}) => {
  const [detailZoneId, setDetailZoneId] = useState<string | null>(selectedZoneId || null);

  // Sort zones by order
  const sortedZones = useMemo(
    () => Array.from(zones.values()).sort((a, b) => a.order - b.order),
    [zones]
  );

  // Get detail zone
  const detailZone = useMemo(() => {
    if (!detailZoneId) return null;
    return zones.get(detailZoneId) || null;
  }, [zones, detailZoneId]);

  // Get current zone index and navigation
  const currentIndex = useMemo(() => {
    return sortedZones.findIndex((z) => z.id === detailZoneId);
  }, [sortedZones, detailZoneId]);

  const handlePrevZone = () => {
    if (currentIndex > 0) {
      setDetailZoneId(sortedZones[currentIndex - 1].id);
    }
  };

  const handleNextZone = () => {
    if (currentIndex < sortedZones.length - 1) {
      setDetailZoneId(sortedZones[currentIndex + 1].id);
    }
  };

  const totalPixels = sortedZones.reduce((sum, z) => sum + z.pixelCount, 0);

  return (
    <div className={styles.dashboard}>
      {/* Header */}
      <div className={styles.header}>
        <h2 className={styles.title}>🎨 Zones Dashboard</h2>
        <div className={styles.stats}>
          <span>{zones.size} zones</span>
          <span>{totalPixels} pixels</span>
        </div>
      </div>

      {/* Thumbnail Grid */}
      <div className={styles.grid}>
        {sortedZones.map((zone) => (
          <ZoneThumbnail
            key={zone.id}
            zone={zone}
            isSelected={detailZoneId === zone.id}
            onClick={() => setDetailZoneId(zone.id)}
          />
        ))}
      </div>

      {/* Detail Card Modal */}
      {detailZone && (
        <div className={styles.modalOverlay} onClick={() => setDetailZoneId(null)}>
          <div
            className={styles.modalContent}
            onClick={(e) => e.stopPropagation()}
          >
            <ZoneDetailCard
              zone={detailZone}
              currentIndex={currentIndex}
              totalZones={sortedZones.length}
              onUpdate={onZoneUpdate}
              onClose={() => setDetailZoneId(null)}
              onPrevZone={handlePrevZone}
              onNextZone={handleNextZone}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ZonesDashboard;
