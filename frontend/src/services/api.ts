/**
 * Axios API Client Configuration
 * Handles HTTP requests to backend with interceptors for auth and error handling
 */

import axios from 'axios';
import type { AxiosError, AxiosInstance, AxiosResponse } from 'axios';
import { config } from '@/config/constants';
import { toast } from 'sonner';

const api: AxiosInstance = axios.create({
  baseURL: config.api.baseUrl,
  timeout: config.api.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor - add auth token and logging
 */
api.interceptors.request.use(
  (axiosConfig) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      axiosConfig.headers.Authorization = `Bearer ${token}`;
    }

    if (config.logging.level === 'debug') {
      console.log('[API Request]', axiosConfig.method?.toUpperCase(), axiosConfig.url);
    }

    return axiosConfig;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

/**
 * Response interceptor - handle errors and auth failures
 */
api.interceptors.response.use(
  (response: AxiosResponse) => {
    if (config.logging.level === 'debug') {
      console.log('[API Response]', response.status, response.config.url);
    }
    return response;
  },
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }

    const message = error.response?.data instanceof Object
      ? (error.response.data as Record<string, string>).message || error.message
      : error.message;

    if (config.logging.level === 'warn' || config.logging.level === 'debug') {
      console.warn('[API Error]', error.status, message);
    }

    // Show error toast for user feedback
    if (error.response?.status && error.response.status >= 500) {
      toast.error('Server error', {
        description: 'Please try again later',
      });
    }

    return Promise.reject(error);
  }
);

export { api };
export default api;
