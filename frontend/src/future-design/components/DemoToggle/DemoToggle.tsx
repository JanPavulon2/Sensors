/**
 * Demo Toggle Component
 * Allows users to switch between real zones and example zones
 */

import React from 'react';
import { getExampleZonesStats } from '../../utils/exampleZones';
import styles from './DemoToggle.module.css';

interface DemoToggleProps {
  isDemoMode: boolean;
  onToggle: () => void;
}

export const DemoToggle: React.FC<DemoToggleProps> = ({ isDemoMode, onToggle }) => {
  const stats = getExampleZonesStats();

  return (
    <div className={styles.container}>
      <button
        className={`${styles.button} ${isDemoMode ? styles.active : ''}`}
        onClick={onToggle}
        title={isDemoMode ? 'Switch to real zones' : 'Switch to demo zones'}
      >
        <span className={styles.icon}>{isDemoMode ? '🎮' : '⚙️'}</span>
        <span className={styles.label}>{isDemoMode ? 'Demo Mode' : 'Real Zones'}</span>
      </button>

      {isDemoMode && (
        <div className={styles.info}>
          <p className={styles.infoText}>
            Showing {stats.total} example zones ({stats.strip} strip, {stats.circle} circle,{' '}
            {stats.matrix} matrix) with {stats.totalPixels} total pixels
          </p>
        </div>
      )}
    </div>
  );
};

export default DemoToggle;
