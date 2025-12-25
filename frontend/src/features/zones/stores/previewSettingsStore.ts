/**
 * LED Preview Settings Store
 * Persists user preferences for LED preview customization
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type LEDShape = 'square' | 'circle' | 'pill';

export interface LEDPreviewSettings {
  shape: LEDShape;
  size: number; // 4-24px
  spacing: number; // 1-8px
  glowIntensity: number; // 0-100
  showGlow: boolean;
}

interface PreviewSettingsStore {
  settings: LEDPreviewSettings;
  setShape: (shape: LEDShape) => void;
  setSize: (size: number) => void;
  setSpacing: (spacing: number) => void;
  setGlowIntensity: (intensity: number) => void;
  setShowGlow: (show: boolean) => void;
  resetToDefaults: () => void;
}

const defaultSettings: LEDPreviewSettings = {
  shape: 'square',
  size: 12,
  spacing: 2,
  glowIntensity: 80,
  showGlow: true,
};

export const usePreviewSettingsStore = create<PreviewSettingsStore>()(
  persist(
    (set) => ({
      settings: defaultSettings,
      setShape: (shape) =>
        set((state) => ({
          settings: { ...state.settings, shape },
        })),
      setSize: (size) =>
        set((state) => ({
          settings: { ...state.settings, size: Math.max(4, Math.min(24, size)) },
        })),
      setSpacing: (spacing) =>
        set((state) => ({
          settings: { ...state.settings, spacing: Math.max(1, Math.min(8, spacing)) },
        })),
      setGlowIntensity: (glowIntensity) =>
        set((state) => ({
          settings: { ...state.settings, glowIntensity: Math.max(0, Math.min(100, glowIntensity)) },
        })),
      setShowGlow: (showGlow) =>
        set((state) => ({
          settings: { ...state.settings, showGlow },
        })),
      resetToDefaults: () => set({ settings: defaultSettings }),
    }),
    {
      name: 'led-preview-settings',
      version: 1,
    }
  )
);
