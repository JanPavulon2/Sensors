/**
 * Log Categories Hook
 * Fetches available log categories from the backend API
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/api/client';

interface LogCategoriesResponse {
  categories: string[];
}

/**
 * Fetch available log categories from backend
 */
export const useLogCategories = () => {
  return useQuery<LogCategoriesResponse, Error>({
    queryKey: ['log-categories'],
    queryFn: async () => {
      const response = await api.get('/v1/logger/categories');
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    retry: 2,
  });
};
