/**
 * Demo Mode Hook
 * Allows toggling between real zones and example zones for showcasing functionality
 */

import { useState, useCallback } from 'react';
import { getExampleZones } from '../utils/exampleZones';
import type { ZoneCombined } from '../types/index';

interface UseDemoModeReturn {
  isDemoMode: boolean;
  zones: ZoneCombined[];
  toggleDemoMode: () => void;
  setRealZones: (zones: ZoneCombined[]) => void;
}

export function useDemoMode(realZones: ZoneCombined[]): UseDemoModeReturn {
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [currentRealZones, setCurrentRealZones] = useState(realZones);

  const toggleDemoMode = useCallback(() => {
    setIsDemoMode((prev) => !prev);
  }, []);

  const setRealZones = useCallback((zones: ZoneCombined[]) => {
    setCurrentRealZones(zones);
  }, []);

  const zones = isDemoMode ? getExampleZones() : currentRealZones;

  return {
    isDemoMode,
    zones,
    toggleDemoMode,
    setRealZones,
  };
}
