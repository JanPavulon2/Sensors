/**
 * System Queries
 * React Query hooks for fetching system status and health
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/api/client';
import type { SystemStatus } from '@/shared/types/api/responses';

interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

/**
 * Fetch system health status (no auth required)
 */
export const useHealthQuery = () => {
  return useQuery<HealthResponse, Error>({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await api.get('/health');
      return response.data;
    },
    refetchInterval: 5000, // Check health every 5 seconds
    refetchOnWindowFocus: true,
  });
};

/**
 * Fetch system status (connection, FPS, etc.)
 * This is a placeholder for future implementation
 * Backend endpoint: GET /api/v1/system/status
 */
export const useSystemStatusQuery = (enabled = true) => {
  return useQuery<SystemStatus, Error>({
    queryKey: ['systemStatus'],
    queryFn: async () => {
      const response = await api.get('/v1/system/status');
      return response.data;
    },
    enabled: enabled,
    refetchInterval: 1000, // Refetch every second for real-time updates
    refetchOnWindowFocus: true,
    retry: false,
  });
};

/**
 * Check if backend is reachable (without auth)
 */
export const useCheckBackendConnection = () => {
  const { data, isLoading, error, refetch } = useHealthQuery();

  const isConnected = !!data && data.status === 'healthy';

  return {
    isConnected,
    isLoading,
    error,
    refetch,
  };
};
