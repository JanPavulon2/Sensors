/**
 * Application Constants
 * Central configuration for API endpoints and app settings
 */

// Auto-detect backend URL based on current hostname
// Supports: localhost (Pi access), IP address (remote access), or explicit env override
const getBackendUrl = () => {
  // If explicitly set via environment, use that
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // If accessing from Pi itself (localhost), use localhost
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000/api';
  }

  // If accessing from remote (by IP), use the same host
  return `http://${window.location.hostname}:8000/api`;
};

const getWebSocketUrl = () => {
  // If explicitly set via environment, use that
  if (import.meta.env.VITE_WEBSOCKET_URL) {
    return import.meta.env.VITE_WEBSOCKET_URL;
  }

  // If accessing from Pi itself (localhost), use localhost
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'ws://localhost:8000';
  }

  // If accessing from remote (by IP), use the same host
  return `ws://${window.location.hostname}:8000`;
};

const API_BASE_URL = getBackendUrl();
const WEBSOCKET_URL = getWebSocketUrl();
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
