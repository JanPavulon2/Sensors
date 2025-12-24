/**
 * Animation Queries
 * React Query hooks for fetching animation data from the API
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/api/client';

export interface Animation {
  id: string;
  display_name: string;
  description: string;
  parameters: string[];
}

interface AnimationsResponse {
  animations: Animation[];
  count: number;
}

/**
 * Fetch all available animations from the API
 */
export const useAnimationsQuery = () => {
  return useQuery<AnimationsResponse, Error>({
    queryKey: ['animations'],
    queryFn: async () => {
      const response = await api.get('/v1/system/animations');
      return response.data;
    },
    refetchInterval: 60000, // Refetch every 60 seconds (animations don't change often)
    refetchOnWindowFocus: false,
  });
};
