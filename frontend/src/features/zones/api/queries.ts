/**
 * Zone Queries & Mutations
 * React Query hooks for fetching and updating zone data from the API
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/api/client';
import type { Zone } from '@/shared/types/domain/zone';

interface ZonesResponse {
  zones: Zone[];
  count: number;
}

interface ColorUpdateRequest {
  color: {
    mode: 'RGB' | 'HUE' | 'PRESET';
    hue?: number;
    rgb?: [number, number, number];
    preset?: string;
  };
}

interface BrightnessUpdateRequest {
  brightness: number;
}

interface ZonePowerToggleRequest {
  is_on: boolean;
}

/**
 * Fetch all zones from the API
 */
export const useZonesQuery = () => {
  return useQuery<ZonesResponse, Error>({
    queryKey: ['zones'],
    queryFn: async () => {
      const response = await api.get('/v1/zones');
      return response.data;
    },
    refetchInterval: 5000, // Refetch every 5 seconds
    refetchOnWindowFocus: true,
  });
};

/**
 * Fetch a single zone by ID
 */
export const useZoneQuery = (zoneId: string | null) => {
  return useQuery<Zone, Error>({
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
 * Update zone color
 */
export const useUpdateZoneColorMutation = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation<Zone, Error, ColorUpdateRequest>({
    mutationFn: async (data) => {
      const response = await api.put(`/v1/zones/${zoneId}/color`, data);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate and refetch zones to get complete color data with rgb conversion
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};

/**
 * Update zone brightness
 */
export const useUpdateZoneBrightnessMutation = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    Zone,
    Error,
    BrightnessUpdateRequest,
    { previousZones?: ZonesResponse }
  >({
    mutationFn: async (data) => {
      const response = await api.put(`/v1/zones/${zoneId}/brightness`, data);
      return response.data;
    },
    onMutate: async (newBrightness) => {
      await queryClient.cancelQueries({ queryKey: ['zones'] });

      const previousZones = queryClient.getQueryData<ZonesResponse>(['zones']);

      if (previousZones) {
        queryClient.setQueryData<ZonesResponse>(['zones'], {
          ...previousZones,
          zones: previousZones.zones.map((zone) =>
            zone.id === zoneId
              ? {
                  ...zone,
                  state: {
                    ...zone.state,
                    brightness: newBrightness.brightness,
                  },
                }
              : zone
          ),
        });
      }

      return { previousZones };
    },
    onError: (_err, _newBrightness, context) => {
      if (context?.previousZones) {
        queryClient.setQueryData(['zones'], context.previousZones);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};

/**
 * Toggle zone power on/off
 */
export const useToggleZonePowerMutation = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    Zone,
    Error,
    ZonePowerToggleRequest,
    { previousZones?: ZonesResponse }
  >({
    mutationFn: async (data) => {
      const response = await api.put(`/v1/zones/${zoneId}/is-on`, data);
      return response.data;
    },
    onMutate: async (newPower) => {
      await queryClient.cancelQueries({ queryKey: ['zones'] });

      const previousZones = queryClient.getQueryData<ZonesResponse>(['zones']);

      if (previousZones) {
        queryClient.setQueryData<ZonesResponse>(['zones'], {
          ...previousZones,
          zones: previousZones.zones.map((zone) =>
            zone.id === zoneId
              ? {
                  ...zone,
                  state: {
                    ...zone.state,
                    is_on: newPower.is_on,
                  },
                }
              : zone
          ),
        });
      }

      return { previousZones };
    },
    onError: (_err, _newPower, context) => {
      if (context?.previousZones) {
        queryClient.setQueryData(['zones'], context.previousZones);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};

/**
 * Reset zone to defaults
 */
export const useResetZoneMutation = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    Zone,
    Error,
    void,
    { previousZones?: ZonesResponse }
  >({
    mutationFn: async () => {
      const response = await api.post(`/v1/zones/${zoneId}/reset`);
      return response.data;
    },
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['zones'] });
      return { previousZones: queryClient.getQueryData<ZonesResponse>(['zones']) };
    },
    onError: (_err, _variables, context) => {
      if (context?.previousZones) {
        queryClient.setQueryData(['zones'], context.previousZones);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};

/**
 * Update zone animation - start animation or switch to static mode
 */
export const useUpdateZoneAnimationMutation = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation<Zone, Error, { animation_id: string | null }>({
    mutationFn: async (data) => {
      if (data.animation_id === null) {
        // Switch to STATIC mode (keep animation_id stored for later resumption)
        const response = await api.put(`/v1/zones/${zoneId}/render-mode`, {
          render_mode: 'STATIC',
        });
        return response.data;
      } else {
        // Start the selected animation (will switch to ANIMATION mode automatically)
        const response = await api.post(`/v1/zones/${zoneId}/animation/start`, {
          animation_id: data.animation_id,
        });
        return response.data;
      }
    },
    onSuccess: () => {
      // Invalidate and refetch zones to get complete updated data
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};

/**
 * Update zone animation parameters
 */
export const useUpdateZoneAnimationParametersMutation = (zoneId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    Zone,
    Error,
    { animation_parameters: Record<string, any> },
    { previousZones?: ZonesResponse }
  >({
    mutationFn: async (data) => {
      const response = await api.put(`/v1/zones/${zoneId}/animation-parameters`, data);
      return response.data.zone;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] });
    },
  });
};
