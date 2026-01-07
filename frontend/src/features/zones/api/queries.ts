/**
 * Zone Queries & Mutations
 *
 * Architecture:
 * 1. useZonesQuery - Initial fetch on page load (no polling)
 * 2. useZoneSocket (in hooks/) - Listens to Socket.IO events and updates cache
 * 3. Simple mutations below - Just send commands to backend (no optimistic updates)
 *    - Backend validates, updates state, emits ZoneStateChanged event
 *    - Socket.IO listener receives zone.snapshot and updates React Query cache
 *    - No need for optimistic updates - real updates come from Socket.IO
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/api/client';
import type { ZoneSnapshot } from '@/shared/types/domain/zone';

interface ZonesResponse {
  zones: ZoneSnapshot[];
  count: number;
}

/**
 * Fetch all zones from the API (initial load, no polling)
 * Real-time updates are handled by useZoneSocket hook via Socket.IO events
 */
export const useZonesQuery = () => {
  return useQuery<ZonesResponse, Error>({
    queryKey: ['zones'],
    queryFn: async () => {
      const response = await api.get('/v1/zones');
      return response.data;
    },
    // No polling - Socket.IO provides real-time updates
    refetchOnWindowFocus: true,
  });
};

/**
 * Fetch a single zone by ID
 */
export const useZoneQuery = (zoneId: string | null) => {
  return useQuery<ZoneSnapshot, Error>({
    queryKey: ['zone', zoneId],
    queryFn: async () => {
      if (!zoneId) throw new Error('Zone ID required');
      const response = await api.get(`/v1/zones/${zoneId}`);
      return response.data;
    },
    enabled: !!zoneId,
    staleTime: 2000,
  });
};

/**
 * Simple mutations - Send commands to backend
 *
 * Flow:
 * 1. Frontend sends PUT request (e.g., brightness = 100)
 * 2. Backend updates zone, saves state, emits ZoneStateChanged
 * 3. Socket.IO handler converts to zone.snapshot event
 * 4. Frontend receives via Socket.IO, updates React Query cache
 *
 * No optimistic updates needed - real updates come from Socket.IO
 */

/**
 * Update zone brightness
 */
export const useSetZoneBrightness = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { brightness: number }) =>
      api.put(`/v1/zones/${zoneId}/brightness`, data),
    onSuccess: () => {
      // Invalidate cache to force refetch if Socket.IO is slow
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};

/**
 * Update zone power state (on/off)
 */
export const useSetZonePower = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { is_on: boolean }) =>
      api.put(`/v1/zones/${zoneId}/is-on`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};

/**
 * Update zone color (hue, RGB, or preset)
 */
export const useSetZoneColor = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      color: {
        mode: 'RGB' | 'HUE' | 'PRESET';
        hue?: number;
        rgb?: [number, number, number];
        preset_name?: string;
      };
    }) => api.put(`/v1/zones/${zoneId}/color`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};

/**
 * Update zone render mode (STATIC or ANIMATION)
 */
export const useSetZoneRenderMode = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { render_mode: 'STATIC' | 'ANIMATION' }) =>
      api.put(`/v1/zones/${zoneId}/render-mode`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};

/**
 * Start zone animation (switches render_mode to ANIMATION automatically)
 */
export const useStartZoneAnimation = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { animation_id: string }) =>
      api.post(`/v1/zones/${zoneId}/animation/start`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};

/**
 * Update zone animation parameters (only when animation is running)
 */
export const useUpdateZoneAnimationParams = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { parameters: Record<string, any> }) =>
      api.put(`/v1/zones/${zoneId}/animation/parameters`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};

/**
 * Reset zone to defaults
 */
export const useResetZone = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.post(`/v1/zones/${zoneId}/reset`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};
