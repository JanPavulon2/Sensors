/**
 * System Store
 * Global state for system/connection status
 */

import { create } from 'zustand';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected';

interface SystemStore {
  connectionStatus: ConnectionStatus;
  fps: number;
  powerDraw: number;
  uptime: number;
  theme: 'dark' | 'light';

  // Actions
  setConnectionStatus: (status: ConnectionStatus) => void;
  setFps: (fps: number) => void;
  setPowerDraw: (power: number) => void;
  setUptime: (uptime: number) => void;
  setTheme: (theme: 'dark' | 'light') => void;
}

export const useSystemStore = create<SystemStore>((set) => ({
  connectionStatus: 'disconnected',
  fps: 0,
  powerDraw: 0,
  uptime: 0,
  theme: 'dark',

  setConnectionStatus: (status: ConnectionStatus) => set({ connectionStatus: status }),
  setFps: (fps: number) => set({ fps }),
  setPowerDraw: (power: number) => set({ powerDraw: power }),
  setUptime: (uptime: number) => set({ uptime }),
  setTheme: (theme: 'dark' | 'light') => set({ theme }),
}));

export default useSystemStore;
