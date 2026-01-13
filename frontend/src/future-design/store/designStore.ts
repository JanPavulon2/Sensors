/**
 * Zustand store for Future Design UX/UI System
 * Manages theme, zone selection, color control, animation state
 * Isolated from existing app state to avoid conflicts
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type {
  AnimationID,
  AnimationPreset,
  Color,
  ColorMode,
  DesignState,
  ParamID,
  ThemeType,
  ZoneID,
  ZoneCombined,
} from '../types/index';

// ============ Store Definition ============

interface DesignStoreState extends DesignState {
  // Actions
  setTheme: (theme: ThemeType) => void;
  selectZone: (zoneId: ZoneID | null) => void;
  selectAnimation: (animId: AnimationID | null) => void;
  setColorMode: (mode: ColorMode) => void;
  setCurrentColor: (color: Color) => void;
  updateZone: (zone: ZoneCombined) => void;
  updateParameter: (paramId: ParamID, value: any) => void;
  setAnimationPresets: (presets: AnimationPreset[]) => void;
  saveAnimationPreset: (preset: AnimationPreset) => void;
  deleteAnimationPreset: (presetId: string) => void;
  syncZones: (zones: ZoneCombined[]) => void;
  toggleGlowEffect: () => void;
  toggleColorBleeding: () => void;
}

// ============ Store Creation ============

export const useDesignStore = create<DesignStoreState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        theme: 'cyber',
        selectedZoneId: null,
        selectedAnimation: null,
        showAnimationPreview: true,
        colorMode: 'HUE',
        currentColor: { mode: 'HUE', hue: 0 },
        zones: new Map(),
        animationParameters: new Map(),
        animationPresets: [],
        showGlowEffect: true,
        enableColorBleeding: true,
        targetFPS: 60,

        // Actions
        setTheme: (theme) => {
          set({ theme });
          // Apply theme class to DOM
          document.documentElement.className = `${theme}-theme`;
          localStorage.setItem('design-theme', theme);
        },

        selectZone: (zoneId) => set({ selectedZoneId: zoneId }),

        selectAnimation: (animId) => set({ selectedAnimation: animId }),

        setColorMode: (mode) => set({ colorMode: mode }),

        setCurrentColor: (color) => set({ currentColor: color }),

        updateZone: (zone) => {
          const zones = new Map(get().zones);
          zones.set(zone.id, zone);
          set({ zones });
        },

        updateParameter: (paramId, value) => {
          const params = new Map(get().animationParameters);
          params.set(paramId, value);
          set({ animationParameters: params });
        },

        setAnimationPresets: (presets) => set({ animationPresets: presets }),

        saveAnimationPreset: (preset) => {
          const presets = [...get().animationPresets, preset];
          set({ animationPresets: presets });
          localStorage.setItem('animation-presets', JSON.stringify(presets));
        },

        deleteAnimationPreset: (presetId) => {
          const presets = get().animationPresets.filter((p) => p.id !== presetId);
          set({ animationPresets: presets });
          localStorage.setItem('animation-presets', JSON.stringify(presets));
        },

        syncZones: (zones) => {
          const zoneMap = new Map(zones.map((z) => [z.id, z]));
          set({ zones: zoneMap });
        },

        toggleGlowEffect: () => set((state) => ({ showGlowEffect: !state.showGlowEffect })),

        toggleColorBleeding: () => set((state) => ({ enableColorBleeding: !state.enableColorBleeding })),
      }),
      {
        name: 'diuna-design-store',
        partialize: (state) => ({
          theme: state.theme,
          colorMode: state.colorMode,
          showGlowEffect: state.showGlowEffect,
          enableColorBleeding: state.enableColorBleeding,
          animationPresets: state.animationPresets,
        }),
      }
    ),
    { name: 'DesignStore' }
  )
);

// ============ Selectors (for performance) ============

/**
 * Select theme only (avoids re-renders on other state changes)
 */
export const useDesignTheme = () => useDesignStore((state) => state.theme);

/**
 * Select selected zone only
 */
export const useSelectedZone = () => useDesignStore((state) => state.selectedZoneId);

/**
 * Select all zones
 */
export const useZones = () => useDesignStore((state) => state.zones);

/**
 * Select specific zone by ID
 */
export const useZoneById = (zoneId: ZoneID | null) =>
  useDesignStore((state) => (zoneId ? state.zones.get(zoneId) : null));

/**
 * Select color mode and current color
 */
export const useColorControl = () =>
  useDesignStore((state) => ({
    mode: state.colorMode,
    color: state.currentColor,
  }));

/**
 * Select animation state
 */
export const useAnimationState = () =>
  useDesignStore((state) => ({
    selectedAnimation: state.selectedAnimation,
    parameters: state.animationParameters,
  }));

/**
 * Select animation presets
 */
export const useAnimationPresets = () => useDesignStore((state) => state.animationPresets);

/**
 * Select visual effects toggles
 */
export const useVisualEffects = () =>
  useDesignStore((state) => ({
    showGlowEffect: state.showGlowEffect,
    enableColorBleeding: state.enableColorBleeding,
  }));

// ============ Computed Selectors ============

/**
 * Get list of zones sorted by order
 */
export const useSortedZones = () => {
  const zones = useDesignStore((state) => state.zones);
  const zoneArray = Array.from(zones.values());
  return zoneArray.sort((a, b) => a.order - b.order);
};

/**
 * Get zone count
 */
export const useZoneCount = () => {
  const zones = useDesignStore((state) => state.zones);
  return zones.size;
};

/**
 * Get total pixel count
 */
export const useTotalPixelCount = () => {
  const zones = useDesignStore((state) => state.zones);
  let total = 0;
  zones.forEach((zone) => {
    total += zone.pixelCount;
  });
  return total;
};

/**
 * Get enabled zone count
 */
export const useEnabledZoneCount = () => {
  const zones = useDesignStore((state) => state.zones);
  let count = 0;
  zones.forEach((zone) => {
    if (zone.enabled) count++;
  });
  return count;
};

// ============ Store Actions (convenience hooks) ============

/**
 * Hook for theme switching
 */
export const useThemeSwitch = () => {
  const setTheme = useDesignStore((state) => state.setTheme);
  const theme = useDesignTheme();

  return {
    theme,
    toggleTheme: () => setTheme(theme === 'cyber' ? 'nature' : 'cyber'),
    setTheme,
  };
};

/**
 * Hook for zone selection
 */
export const useZoneSelection = () => {
  const selectZone = useDesignStore((state) => state.selectZone);
  const selectedZoneId = useSelectedZone();
  const zones = useZones();

  return {
    selectedZoneId,
    selectZone,
    selectedZone: selectedZoneId ? zones.get(selectedZoneId) : null,
    clearSelection: () => selectZone(null),
  };
};

/**
 * Hook for color control
 */
export const useColorController = () => {
  const setColorMode = useDesignStore((state) => state.setColorMode);
  const setCurrentColor = useDesignStore((state) => state.setCurrentColor);
  const colorControl = useColorControl();

  return {
    ...colorControl,
    setMode: setColorMode,
    setColor: setCurrentColor,
  };
};

/**
 * Hook for animation control
 */
export const useAnimationController = () => {
  const selectAnimation = useDesignStore((state) => state.selectAnimation);
  const updateParameter = useDesignStore((state) => state.updateParameter);
  const animState = useAnimationState();

  return {
    ...animState,
    selectAnimation,
    updateParameter,
  };
};

/**
 * Hook for animation preset management
 */
export const useAnimationPresetManager = () => {
  const presets = useAnimationPresets();
  const savePreset = useDesignStore((state) => state.saveAnimationPreset);
  const deletePreset = useDesignStore((state) => state.deleteAnimationPreset);

  return {
    presets,
    savePreset,
    deletePreset,
  };
};

/**
 * Initialize store with theme from localStorage
 */
export const initializeDesignStore = () => {
  const savedTheme = localStorage.getItem('design-theme') as ThemeType | null;
  if (savedTheme) {
    useDesignStore.setState({ theme: savedTheme });
    document.documentElement.className = `${savedTheme}-theme`;
  } else {
    // Default to cyber theme
    useDesignStore.setState({ theme: 'cyber' });
    document.documentElement.className = 'cyber-theme';
  }
};
