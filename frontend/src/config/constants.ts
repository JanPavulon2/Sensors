/**
 * Application Constants
 * Central configuration for API endpoints and app settings
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const WEBSOCKET_URL = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000';
const LOG_LEVEL = (import.meta.env.VITE_LOG_LEVEL || 'info') as 'debug' | 'info' | 'warn' | 'error';

export const config = {
  api: {
    baseUrl: API_BASE_URL,
    timeout: 10000,
  },
  websocket: {
    url: WEBSOCKET_URL,
    reconnectAttempts: 5,
    reconnectDelay: 1000,
  },
  logging: {
    level: LOG_LEVEL,
  },
  features: {
    analytics: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
    experimentalFeatures: import.meta.env.VITE_ENABLE_EXPERIMENTAL_FEATURES === 'true',
  },
} as const;

export default config;
