/**
 * Authentication Hooks
 * Manages auth token in localStorage and provides token operations
 */

import { useState, useEffect, useCallback } from 'react';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
}

const AUTH_TOKEN_KEY = 'auth_token';
const DEFAULT_TEST_TOKEN = 'test-user-demo-token';

/**
 * Hook for managing authentication token
 * Reads from localStorage and provides methods to set/clear token
 */
export const useAuth = () => {
  const [authState, setAuthState] = useState<AuthState>(() => ({
    token: localStorage.getItem(AUTH_TOKEN_KEY),
    isAuthenticated: !!localStorage.getItem(AUTH_TOKEN_KEY),
    loading: false,
  }));

  // Load token from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (token) {
      setAuthState({
        token,
        isAuthenticated: true,
        loading: false,
      });
    }
  }, []);

  const setToken = useCallback((token: string) => {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    setAuthState({
      token,
      isAuthenticated: true,
      loading: false,
    });
  }, []);

  const clearToken = useCallback(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    setAuthState({
      token: null,
      isAuthenticated: false,
      loading: false,
    });
  }, []);

  const setTestToken = useCallback((userId: string = 'test-user') => {
    // In development, create a test token
    // Format: {userId}-{randomString}
    const randomPart = Math.random().toString(36).substring(2, 10);
    const testToken = `${userId}-${randomPart}`;
    setToken(testToken);
  }, [setToken]);

  const useDefaultTestToken = useCallback(() => {
    setToken(DEFAULT_TEST_TOKEN);
  }, [setToken]);

  return {
    ...authState,
    setToken,
    clearToken,
    setTestToken,
    useDefaultTestToken,
  };
};

/**
 * Hook to check if user is authenticated
 * Can be used to guard routes or conditional rendering
 */
export const useIsAuthenticated = () => {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  return !!token;
};
