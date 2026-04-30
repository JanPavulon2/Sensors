/**
 * Debug Metrics Feature
 *
 * Real-time render pipeline metrics streaming and visualization.
 */

// Types
export type {
  RenderMetricsSnapshot,
  FpsMetrics,
  PipelineMetrics,
  CounterMetrics,
  ZoneMetricsData,
  AnimationMetricsData,
} from './types/metrics';

// Realtime
export {
  metricsSocket,
  connectMetricsStream,
  disconnectMetricsStream,
} from './realtime/metrics.socket';

export {
  useMetricsSnapshot,
  useMetricsHistory,
  useMetricsConnected,
  clearMetricsHistory,
} from './realtime/metrics.store';

// Components
export { RenderMetricsPanel } from './components';
