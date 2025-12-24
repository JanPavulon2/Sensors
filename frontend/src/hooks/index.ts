/**
 * Hooks Index
 * Central export point for all custom hooks
 */

// Shared hooks (moved to shared)
export { useAuth, useIsAuthenticated, useCheckBackendConnection, useHealthQuery, useSystemStatusQuery } from '@/shared/hooks';

// Zone-related hooks (to be moved to features/zones)
export * from './useZones';

// Animations
export * from './useAnimations';
